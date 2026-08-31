"""
=========================================================================
LRT PIPELINE REAL - 65 CASOS ETIQUETADOS
Pipeline de Leads con IA - TFI UTN FRM
=========================================================================

Mide el tiempo real de pipeline completo (webhook -> ETL -> IA clasificar
-> [IA generar email si no es spam] -> PATCH final a Supabase), no el
fast-ack de Flask (~2.1s, que es lo que mide tests/test_65_casos_limpio.py
como lrt_flask_segundos).

Metodo: cronometro propio (Opcion 2). Se descarto la Opcion 1
(updated_at - timestamp_ingesta) porque en una prueba real se detecto
que, para los casos de spam, timestamp_ingesta salia DESPUES de
updated_at (diferencias negativas de hasta -0.6s) -algo fisicamente
imposible que indica que la referencia $('ETL').item.json.timestamp_ingesta
dentro del nodo PATCH no siempre resuelve al valor que se espera segun
la rama del workflow-. El cronometro propio no depende de como n8n arma
sus timestamps internos: se mide con el MISMO reloj el instante en que
se manda el lead y el instante en que Supabase muestra la clasificacion
ya escrita (que es el ultimo campo que escribe el PATCH final, tanto
para spam como para no-spam).

USO:
  python tests/test_65_casos_lrt_pipeline.py

SALIDA:
  tests/resultados_v3/lrt_pipeline_65_casos.csv
  tests/resultados_v3/lrt_pipeline_65_casos.txt
=========================================================================
"""
import os
import sys
import csv
import statistics
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from test_100_leads import generar_100_casos, get_session_with_csrf  # noqa: E402

load_dotenv()

BASE_URL = os.getenv("FLASK_URL", "http://localhost:5000")
API_URL = f"{BASE_URL}/api/leads"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SLEEP_ENTRE_CASOS = float(os.getenv("SLEEP_ENTRE_CASOS", "8"))
POLL_INTERVALO = float(os.getenv("POLL_INTERVALO", "0.5"))
POLL_TIMEOUT = float(os.getenv("POLL_TIMEOUT", "30"))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "resultados_v3")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "lrt_pipeline_65_casos.csv")
OUTPUT_TXT = os.path.join(OUTPUT_DIR, "lrt_pipeline_65_casos.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_ANON_KEY en .env")


def casos_65_etiquetados():
    casos = generar_100_casos()
    return [c for c in casos if c.get("esperado", {}).get("ia_clasificacion")]


def email_run(email_original):
    local, dominio = email_original.split("@", 1)
    return f"{local}+lrtpipe3@{dominio}"


HEURISTICA_PREFIJO = "Clasificacion heuristica"


def esperar_clasificacion_con_cronometro(email, t0, timeout=POLL_TIMEOUT, intervalo=POLL_INTERVALO):
    """Poll a Supabase hasta ver la clasificacion REAL de la IA (no la
    heuristica de respaldo que 'Persistir Early' ya escribe al toque,
    antes de llamar a OpenAI -detectable porque ia_resumen arranca con
    'Clasificacion heuristica'-). Devuelve (lrt_segundos, ia_clasificacion)
    medido con el reloj local desde t0."""
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {
        "select": "ia_clasificacion,ia_resumen",
        "email": f"eq.{email}",
        "order": "created_at.desc",
        "limit": "1",
    }
    deadline = t0 + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/leads", headers=headers,
                              params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data:
                    resumen = data[0].get("ia_resumen") or ""
                    clasif = data[0].get("ia_clasificacion")
                    if clasif and not resumen.startswith(HEURISTICA_PREFIJO):
                        lrt = round(time.time() - t0, 3)
                        return lrt, clasif
        except requests.exceptions.RequestException:
            pass
        time.sleep(intervalo)
    return None, None


def main():
    casos = casos_65_etiquetados()
    print(f"Casos etiquetados: {len(casos)} (se esperan 65)")

    print(f"\n{'=' * 72}\nCORRIDA CON CRONOMETRO - {len(casos)} casos\n{'=' * 72}")
    filas = []
    for i, caso in enumerate(casos):
        session, csrf = get_session_with_csrf()
        email = email_run(caso["email"])
        payload = {
            "nombre": caso["nombre"], "apellido": caso["apellido"],
            "email": email, "telefono": caso["telefono"],
            "mensaje": caso["mensaje"], "fuente": "lrt_pipeline_65_v2",
            "_csrf_token": csrf,
        }

        t0 = time.time()
        try:
            session.post(API_URL, data=payload, timeout=8,
                         headers={"Accept": "application/json"})
        except requests.exceptions.RequestException:
            pass

        lrt, obtenido = esperar_clasificacion_con_cronometro(email, t0)

        fila = {
            "caso_id": caso["id"],
            "categoria": caso["categoria"],
            "esperado": caso["esperado"]["ia_clasificacion"],
            "obtenido": obtenido,
            "lrt_pipeline_segundos": lrt,
        }
        filas.append(fila)

        icono = "OK " if lrt is not None else "ERR"
        lrt_str = f"{lrt}s" if lrt is not None else "TIMEOUT"
        pct = (i + 1) / len(casos) * 100
        print(f"  [{pct:5.1f}%] {icono} {caso['id']:10s} LRT Pipeline = {lrt_str}")

        if i < len(casos) - 1:
            time.sleep(SLEEP_ENTRE_CASOS)

    validos = [f["lrt_pipeline_segundos"] for f in filas if f["lrt_pipeline_segundos"] is not None]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "caso_id", "categoria", "esperado", "obtenido", "lrt_pipeline_segundos"
        ])
        writer.writeheader()
        for fila in filas:
            writer.writerow({k: fila.get(k, "") for k in writer.fieldnames})

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write("LRT PIPELINE REAL - 65 CASOS ETIQUETADOS (metodo: cronometro propio)\n")
        f.write("LRT Pipeline = tiempo desde el envio del lead hasta que Supabase\n")
        f.write("muestra ia_clasificacion ya escrita (ultimo campo del PATCH final\n")
        f.write("de 'Actualizar IA en Supabase', que corre despues de clasificar y\n")
        f.write("-si no es spam- de generar el email). Medido con el mismo reloj de\n")
        f.write("principio a fin (no depende de timestamps internos de n8n).\n")
        f.write(f"Fecha: {ahora}\n")
        f.write("=" * 72 + "\n\n")
        if validos:
            f.write(f"n = {len(validos)}/{len(filas)}\n")
            f.write(f"Media:    {statistics.mean(validos):.3f} s\n")
            f.write(f"Mediana:  {statistics.median(validos):.3f} s\n")
            if len(validos) > 1:
                f.write(f"Desvio:   {statistics.stdev(validos):.3f} s\n")
            f.write(f"Minimo:   {min(validos):.3f} s\n")
            f.write(f"Maximo:   {max(validos):.3f} s\n\n")
            bajo_8 = sum(1 for v in validos if v <= 8)
            bajo_5 = sum(1 for v in validos if v <= 5)
            f.write(f"Casos <= 8s: {bajo_8}/{len(validos)} ({bajo_8/len(validos)*100:.1f}%)\n")
            f.write(f"Casos <= 5s: {bajo_5}/{len(validos)} ({bajo_5/len(validos)*100:.1f}%)\n\n")
        f.write("DETALLE CASO POR CASO:\n")
        f.write(f"{'Caso':<12s}{'Categoria':<10s}{'Esperado':<20s}{'Obtenido':<20s}"
                f"{'LRT Pipeline (s)':<18s}\n")
        f.write("-" * 80 + "\n")
        for fila in filas:
            lrt_str = f"{fila['lrt_pipeline_segundos']}" if fila["lrt_pipeline_segundos"] is not None else "SIN DATO"
            f.write(f"{fila['caso_id']:<12s}{fila['categoria']:<10s}{fila['esperado']:<20s}"
                    f"{str(fila.get('obtenido')):<20s}{lrt_str:<18s}\n")
        f.write(f"\nNota. Elaboracion propia, corrida del {ahora}. "
                "Metodo: cronometro cliente (envio -> polling cada "
                f"{POLL_INTERVALO}s hasta ver ia_clasificacion en Supabase). "
                "Ver tests/test_65_casos_lrt_pipeline.py.\n")

    print(f"\nExportado a:\n  {OUTPUT_CSV}\n  {OUTPUT_TXT}")
    if validos:
        print(f"\nMedia LRT Pipeline: {statistics.mean(validos):.3f}s | n={len(validos)}/{len(filas)}")


if __name__ == "__main__":
    main()
