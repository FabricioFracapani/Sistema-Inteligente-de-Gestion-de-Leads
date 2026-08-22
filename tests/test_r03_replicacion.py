"""
=========================================================================
R-03 - REPLICACION (M-05)
Pipeline de Leads con IA - TFI UTN FRM
=========================================================================

Corre el pipeline real (Flask -> n8n -> GPT-4o-mini -> Supabase) 3 veces
sobre los mismos 65 casos etiquetados (los que tienen "ia_clasificacion"
esperada en generar_100_casos(): CP-01 compra_inmediata, CP-02
solicita_info, CP-06/07 soporte, CP-08 spam).

Por corrida se reenvian los 65 casos con el mismo contenido pero un email
con sufijo +r{N} (plus-addressing) para poder distinguir cada corrida en
la tabla `leads` de Supabase sin chocar con la logica de duplicados.

Requisitos antes de correr:
  - Flask corriendo en FLASK_URL (por defecto http://localhost:5000)
  - n8n corriendo con el workflow activo y las credenciales de OpenAI /
    Supabase configuradas
  - SUPABASE_URL y SUPABASE_ANON_KEY en .env (RLS permite SELECT a anon)

USO:
  python tests/test_r03_replicacion.py
=========================================================================
"""
import os
import sys
import csv
import json
import time
from datetime import datetime, timezone
from statistics import mean, stdev

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
ESPERA_PROCESAMIENTO = float(os.getenv("ESPERA_PROCESAMIENTO_R03", "25"))
N_RUNS = 3

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "resultados_v3")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "r03_replicacion.csv")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "r03_replicacion.json")
OUTPUT_SUMMARY = os.path.join(OUTPUT_DIR, "r03_replicacion_resumen.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_ANON_KEY en .env")


def casos_65_etiquetados():
    casos = generar_100_casos()
    return [c for c in casos if c.get("esperado", {}).get("ia_clasificacion")]


def email_para_corrida(email_original, run_idx):
    local, dominio = email_original.split("@", 1)
    return f"{local}+r{run_idx}@{dominio}"


def consultar_clasificacion(email, intentos=12, espera=5):
    """Consulta Supabase (anon key, RLS permite SELECT) hasta ver ia_clasificacion."""
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {
        "select": "ia_clasificacion,estado,created_at",
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
                    return data[0]["ia_clasificacion"]
        except requests.exceptions.RequestException:
            pass
        time.sleep(espera)
    return None


def ejecutar_corrida(run_idx, casos):
    print(f"\n{'=' * 72}")
    print(f"  CORRIDA {run_idx}/{N_RUNS} - {len(casos)} casos etiquetados")
    print(f"{'=' * 72}")

    envios = {}
    for i, caso in enumerate(casos):
        session, csrf = get_session_with_csrf()
        email_run = email_para_corrida(caso["email"], run_idx)
        payload = {
            "nombre": caso["nombre"],
            "apellido": caso["apellido"],
            "email": email_run,
            "telefono": caso["telefono"],
            "mensaje": caso["mensaje"],
            "fuente": f"r03_run{run_idx}",
            "_csrf_token": csrf,
        }
        try:
            session.post(API_URL, data=payload, timeout=5,
                          headers={"Accept": "application/json"})
        except requests.exceptions.RequestException:
            pass  # n8n ya recibio el webhook y sigue procesando en background

        envios[caso["id"]] = {
            "categoria": caso["categoria"],
            "email_run": email_run,
            "esperado": caso["esperado"]["ia_clasificacion"],
        }

        pct = (i + 1) / len(casos) * 100
        bar = "=" * int(pct / 2) + " " * (50 - int(pct / 2))
        print(f"  [{bar}] {pct:5.1f}% | enviado {caso['id']:10s} -> {email_run}", end="\r")

        if i < len(casos) - 1:
            time.sleep(SLEEP_ENTRE_CASOS)

    print(f"\n  Envio completo. Esperando {ESPERA_PROCESAMIENTO}s antes de leer Supabase...")
    time.sleep(ESPERA_PROCESAMIENTO)

    print("  Consultando clasificacion real en Supabase...")
    for cid, info in envios.items():
        clasif = consultar_clasificacion(info["email_run"])
        info["obtenido"] = clasif
        info["coincide"] = (clasif == info["esperado"])
        icono = "OK " if info["coincide"] else "ERR"
        print(f"    {icono} {cid:10s} esperado={info['esperado']:20s} obtenido={clasif}")

    aciertos = sum(1 for v in envios.values() if v["coincide"])
    exactitud = aciertos / len(envios) * 100
    print(f"\n  Exactitud corrida {run_idx}: {aciertos}/{len(envios)} ({exactitud:.1f}%)")
    return envios, exactitud


def main():
    casos = casos_65_etiquetados()
    print(f"Casos etiquetados encontrados: {len(casos)} (se esperan 65)")

    corridas = []
    exactitudes = []
    for run_idx in range(1, N_RUNS + 1):
        envios, exactitud = ejecutar_corrida(run_idx, casos)
        corridas.append(envios)
        exactitudes.append(exactitud)

    # ------------------------------------------------------------
    # Consolidar por caso: estabilidad entre las 3 corridas
    # ------------------------------------------------------------
    filas = []
    estables = 0
    for caso in casos:
        cid = caso["id"]
        obtenidos = [corridas[r][cid]["obtenido"] for r in range(N_RUNS)]
        esperado = caso["esperado"]["ia_clasificacion"]
        estable = len(set(obtenidos)) == 1 and obtenidos[0] is not None
        if estable:
            estables += 1
        fila = {
            "caso_id": cid,
            "categoria": caso["categoria"],
            "esperado": esperado,
        }
        for r in range(N_RUNS):
            fila[f"corrida_{r + 1}"] = obtenidos[r]
            fila[f"coincide_{r + 1}"] = corridas[r][cid]["coincide"]
        fila["estable_3_corridas"] = estable
        filas.append(fila)

    pct_estable = estables / len(casos) * 100
    media = mean(exactitudes)
    desvio = stdev(exactitudes) if len(exactitudes) > 1 else 0.0

    print(f"\n{'=' * 72}")
    print("  RESULTADOS R-03 - REPLICACION (M-05)")
    print(f"{'=' * 72}")
    for i, ex in enumerate(exactitudes, start=1):
        print(f"  Exactitud corrida {i}:  {ex:.1f}%")
    print(f"  Media +/- desvio:      {media:.1f}% +/- {desvio:.1f}%")
    print(f"  Estables en las 3:     {estables}/{len(casos)} ({pct_estable:.1f}%)")
    print(f"{'=' * 72}")

    # ------------------------------------------------------------
    # Exportar
    # ------------------------------------------------------------
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)

    metadata = {
        "fecha_ejecucion": datetime.now(timezone.utc).isoformat(),
        "requisito": "R-03",
        "metodo": "M-05",
        "n_casos": len(casos),
        "n_corridas": N_RUNS,
        "exactitud_por_corrida_pct": [round(e, 1) for e in exactitudes],
        "exactitud_media_pct": round(media, 1),
        "exactitud_desvio_pct": round(desvio, 1),
        "casos_estables": estables,
        "pct_estables": round(pct_estable, 1),
        "nota_metodologica": (
            "3 corridas del pipeline real (Flask -> n8n -> GPT-4o-mini -> Supabase) "
            "sobre los mismos 65 casos con clasificacion esperada (CP-01, CP-02, "
            "CP-06/07, CP-08). Cada corrida usa un email con sufijo +rN para "
            "distinguir las filas en Supabase. Exactitud = coincidencias con la "
            "clasificacion esperada / 65. Estabilidad = % de casos con la misma "
            "clasificacion obtenida en las 3 corridas (independiente de si acierta)."
        ),
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "casos": filas}, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write("R-03 - REPLICACION (M-05)\n")
        f.write("TFI - Sistema Inteligente de Gestion de Leads\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 72 + "\n\n")
        f.write(f"Casos etiquetados: {len(casos)}\n")
        f.write(f"Corridas: {N_RUNS}\n\n")
        for i, ex in enumerate(exactitudes, start=1):
            f.write(f"Exactitud corrida {i}: {ex:.1f}%\n")
        f.write(f"\nExactitud media +/- desvio entre corridas: {media:.1f}% +/- {desvio:.1f}%\n")
        f.write(f"Casos con clasificacion estable en las 3 corridas: {estables}/{len(casos)} ({pct_estable:.1f}%)\n")

    print(f"\nArchivos exportados a: {OUTPUT_DIR}/")
    print("  r03_replicacion.csv")
    print("  r03_replicacion.json")
    print("  r03_replicacion_resumen.txt")

    return filas, metadata


if __name__ == "__main__":
    main()
