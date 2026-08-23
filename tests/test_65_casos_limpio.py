"""
=========================================================================
CORRIDA LIMPIA - 65 CASOS ETIQUETADOS (reemplaza el Anexo F cuestionado)
Pipeline de Leads con IA - TFI UTN FRM
=========================================================================

Por que existe este script:
  Se detecto que la Tabla F.1 publicada en el TFI (63/65 = 96,9%) no
  coincide con NINGUNA fuente de datos reproducible del repositorio
  (ni con tests/resultados_v3/anexo_f_100_casos_real.csv, ni con la
  tabla de Aug-14, ni con la simulacion de test_100_leads.py). No se
  encontro el origen real de esos numeros. Ver
  tests/resultados_v3/explicacion_datos_limpios.txt para el detalle
  completo de la investigacion.

  Esta corrida reemplaza esos numeros por una medicion real, unica,
  trazable: se corre el pipeline real (Flask -> n8n -> GPT-4o-mini
  pineado a gpt-4o-mini-2024-07-18 -> Supabase) sobre los mismos 65
  casos con clasificacion esperada, y se lee la clasificacion real
  desde Supabase (no se simula nada).

USO:
  python tests/test_65_casos_limpio.py

SALIDA:
  tests/resultados_v3/anexo_f_65_casos_limpio.csv
  tests/resultados_v3/anexo_f_65_casos_limpio.txt
=========================================================================
"""
import os
import sys
import csv
import json
import math
import time
from datetime import datetime, timezone
from collections import defaultdict

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
ESPERA_PROCESAMIENTO = float(os.getenv("ESPERA_PROCESAMIENTO", "25"))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "resultados_v3")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "anexo_f_65_casos_limpio.csv")
OUTPUT_TXT = os.path.join(OUTPUT_DIR, "anexo_f_65_casos_limpio.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_ANON_KEY en .env")

CLASES = ["compra_inmediata", "solicita_info", "soporte", "spam"]
CLASES_LABEL = {
    "compra_inmediata": "Compra inmediata",
    "solicita_info": "Solicita informacion",
    "soporte": "Soporte tecnico",
    "spam": "Spam",
}


def casos_65_etiquetados():
    casos = generar_100_casos()
    return [c for c in casos if c.get("esperado", {}).get("ia_clasificacion")]


def email_limpio(email_original):
    local, dominio = email_original.split("@", 1)
    return f"{local}+limpio@{dominio}"


def consultar_clasificacion(email, intentos=12, espera=5):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {
        "select": "ia_clasificacion,ia_prioridad,estado,created_at",
        "email": f"eq.{email}",
        "order": "created_at.desc",
        "limit": "1",
    }
    for _ in range(intentos):
        try:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/leads", headers=headers,
                              params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data and data[0].get("ia_clasificacion"):
                    return data[0]["ia_clasificacion"], data[0].get("ia_prioridad")
        except requests.exceptions.RequestException:
            pass
        time.sleep(espera)
    return None, None


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return None, None
    phat = k / n
    denom = 1 + z ** 2 / n
    center = phat + z ** 2 / (2 * n)
    adj = z * math.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2))
    lo = (center - adj) / denom
    hi = (center + adj) / denom
    return round(lo * 100, 1), round(hi * 100, 1)


def main():
    casos = casos_65_etiquetados()
    print(f"Casos etiquetados: {len(casos)} (se esperan 65)")

    print(f"\n{'=' * 72}\nCORRIDA LIMPIA - {len(casos)} casos\n{'=' * 72}")
    filas = []
    for i, caso in enumerate(casos):
        session, csrf = get_session_with_csrf()
        email_run = email_limpio(caso["email"])
        payload = {
            "nombre": caso["nombre"], "apellido": caso["apellido"],
            "email": email_run, "telefono": caso["telefono"],
            "mensaje": caso["mensaje"], "fuente": "anexo_f_limpio",
            "_csrf_token": csrf,
        }
        t0 = time.time()
        try:
            session.post(API_URL, data=payload, timeout=8,
                         headers={"Accept": "application/json"})
        except requests.exceptions.RequestException:
            pass
        lrt_flask = round(time.time() - t0, 3)

        filas.append({
            "caso_id": caso["id"],
            "categoria": caso["categoria"],
            "email_run": email_run,
            "esperado": caso["esperado"]["ia_clasificacion"],
            "lrt_flask_segundos": lrt_flask,
        })

        pct = (i + 1) / len(casos) * 100
        print(f"  [{pct:5.1f}%] enviado {caso['id']:10s}", end="\r")
        if i < len(casos) - 1:
            time.sleep(SLEEP_ENTRE_CASOS)

    print(f"\nEnvio completo. Esperando {ESPERA_PROCESAMIENTO}s antes de leer Supabase...")
    time.sleep(ESPERA_PROCESAMIENTO)

    print("Consultando clasificacion real en Supabase...")
    matriz = defaultdict(lambda: defaultdict(int))
    conteo_real = defaultdict(int)
    aciertos_totales = 0
    for fila in filas:
        obtenida, prioridad = consultar_clasificacion(fila["email_run"])
        fila["obtenido"] = obtenida
        fila["ia_prioridad"] = prioridad
        fila["resultado"] = "Acierto" if obtenida == fila["esperado"] else "Error"
        icono = "OK " if fila["resultado"] == "Acierto" else "ERR"
        print(f"  {icono} {fila['caso_id']:10s} esperado={fila['esperado']:20s} obtenido={obtenida}")
        if obtenida:
            matriz[fila["esperado"]][obtenida] += 1
            conteo_real[fila["esperado"]] += 1
            if obtenida == fila["esperado"]:
                aciertos_totales += 1

    total_evaluados = sum(conteo_real.values())
    exactitud_global = aciertos_totales / max(total_evaluados, 1) * 100
    ci_lo, ci_hi = wilson_ci(aciertos_totales, total_evaluados)

    print(f"\n{'=' * 72}\nRESULTADOS\n{'=' * 72}")
    print(f"Exactitud global: {aciertos_totales}/{total_evaluados} = {exactitud_global:.1f}% "
          f"IC95% Wilson [{ci_lo}%, {ci_hi}%]")

    metricas_clase = {}
    for clase in CLASES:
        vp = matriz[clase][clase]
        n = conteo_real.get(clase, 0)
        pct = vp / n * 100 if n else None
        lo, hi = wilson_ci(vp, n) if n else (None, None)
        metricas_clase[clase] = {"n": n, "aciertos": vp, "pct": pct, "ci_lo": lo, "ci_hi": hi}
        if n:
            print(f"  {CLASES_LABEL[clase]:<25s} {vp}/{n} = {pct:.1f}% IC95% [{lo}%, {hi}%]")

    # Exportar CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "caso_id", "categoria", "esperado", "obtenido", "resultado",
            "ia_prioridad", "lrt_flask_segundos"
        ])
        writer.writeheader()
        for fila in filas:
            writer.writerow({k: fila.get(k, "") for k in writer.fieldnames})

    # Exportar TXT (matriz + metricas, listo para transcribir)
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write("ANEXO F (LIMPIO) - CORRIDA REAL SOBRE 65 CASOS ETIQUETADOS\n")
        f.write("Reemplaza la Tabla F.1 original (96,9%), que no se pudo trazar a\n")
        f.write("ninguna fuente reproducible del repositorio.\n")
        f.write(f"Fecha: {ahora}\n")
        f.write("Pipeline: Flask -> n8n -> OpenAI (gpt-4o-mini-2024-07-18, "
                "response_format json_schema) -> Supabase\n")
        f.write("=" * 72 + "\n\n")
        f.write(f"EXACTITUD GLOBAL: {aciertos_totales}/{total_evaluados} = "
                f"{exactitud_global:.1f}%  (IC95% Wilson [{ci_lo}%, {ci_hi}%])\n\n")
        f.write("EXACTITUD POR CLASE:\n")
        for clase in CLASES:
            m = metricas_clase[clase]
            if m["n"]:
                f.write(f"  {CLASES_LABEL[clase]:<25s} {m['aciertos']}/{m['n']} = "
                        f"{m['pct']:.1f}%  IC95% [{m['ci_lo']}%, {m['ci_hi']}%]\n")
        f.write("\nMATRIZ DE CONFUSION (filas=esperado, columnas=obtenido):\n")
        f.write(" " * 20 + "".join(f"{CLASES_LABEL[c]:>22}" for c in CLASES) + "\n")
        f.write("-" * 108 + "\n")
        for real in CLASES:
            fila_vals = [matriz[real][pred] for pred in CLASES]
            f.write(f"{CLASES_LABEL[real]:<20s}" + "".join(f"{v:>22}" for v in fila_vals)
                    + f"  (n={conteo_real.get(real, 0)})\n")
        f.write("-" * 108 + "\n\n")
        f.write("DETALLE CASO POR CASO:\n")
        f.write(f"{'Caso':<12s}{'Esperado':<20s}{'Obtenido':<20s}{'Resultado':<10s}"
                f"{'Prior.':<8s}{'LRT Flask (s)':<15s}\n")
        f.write("-" * 85 + "\n")
        for fila in filas:
            f.write(f"{fila['caso_id']:<12s}{fila['esperado']:<20s}"
                    f"{str(fila.get('obtenido')):<20s}{fila['resultado']:<10s}"
                    f"{str(fila.get('ia_prioridad', '')):<8s}"
                    f"{fila['lrt_flask_segundos']:<15}\n")
        f.write("\nNota. LRT Flask = tiempo de fast-ack de Flask (no incluye el "
                "procesamiento asincronico en n8n). Elaboracion propia, "
                f"corrida del {ahora}.\n")

    print(f"\nExportado a:\n  {OUTPUT_CSV}\n  {OUTPUT_TXT}")
    return filas, exactitud_global


if __name__ == "__main__":
    main()
