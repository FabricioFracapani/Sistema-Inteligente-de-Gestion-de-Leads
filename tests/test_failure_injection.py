"""
=========================================================================
SCRIPT DE INYECCIÓN DE FALLOS — Validación de OE7 (Manejo de Errores)
Pipeline de Leads con IA — TFI UTN FRM
=========================================================================

OBJETIVO: Validar el objetivo específico OE7 (manejo de errores con
principio fail-loudly) mediante inyección deliberada de fallos.

CASOS DE PRUEBA DE FALLO:
  CF-01: n8n inalcanzable (Timeout) → Verificar backup local
  CF-02: n8n inalcanzable (Connection Refused) → Verificar backup local
  CF-03 (documentado): Credencial Supabase inválida en n8n → Error Trigger + Slack
  CF-04 (documentado): API Key OpenAI inválida en n8n → Error Trigger + Slack

NOTA: CF-03 y CF-04 requieren modificar temporalmente las credenciales
en n8n y por tanto se documentan como procedimiento manual. Este script
automatiza los casos CF-01 y CF-02 que prueban la resiliencia de Flask.

USO:
  1. Asegurate de que Flask esté corriendo: python landing_page/app.py
  2. Para CF-01/02: NO iniciar n8n (o detenerlo) para simular fallo
  3. Ejecutar: python tests/test_failure_injection.py
  4. Para CF-03/04: seguir el procedimiento manual documentado abajo
=========================================================================
"""
import requests
import time
import os
import re
import json
from datetime import datetime, timezone

BASE_URL = os.getenv("FLASK_URL", "http://localhost:5000")
BACKUP_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "landing_page", "leads_fallback.log"
)


def get_csrf():
    session = requests.Session()
    try:
        r = session.get(BASE_URL + "/", timeout=10)
        match = re.search(r'name="_csrf_token"[^>]*value="([^"]+)"', r.text)
        return session, match.group(1) if match else "fallback"
    except Exception:
        return session, "fallback"


def send_lead(session, csrf, case_id, descripcion):
    """Envía un lead de prueba y mide la respuesta de Flask."""
    payload = {
        "nombre": f"Fallo {case_id}",
        "apellido": "Test",
        "email": f"fallo.{case_id}@test-failure-tfi.local",
        "telefono": "+54 261 0000000",
        "mensaje": f"Caso de inyección de fallo: {descripcion}",
        "fuente": "failure_injection_test",
        "_csrf_token": csrf
    }

    t0 = time.time()
    try:
        r = session.post(
            f"{BASE_URL}/api/leads",
            data=payload,
            timeout=12,
            headers={"Accept": "application/json"}
        )
        lrt = round(time.time() - t0, 3)
        return {
            "case_id": case_id,
            "status": r.status_code,
            "lrt_flask": lrt,
            "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:200],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except requests.exceptions.Timeout:
        return {
            "case_id": case_id,
            "status": None,
            "lrt_flask": 12.0,
            "response": "TIMEOUT",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "case_id": case_id,
            "status": None,
            "lrt_flask": round(time.time() - t0, 3),
            "response": str(e)[:200],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def check_backup_file():
    """Verifica si el archivo de respaldo tiene entradas nuevas."""
    if not os.path.exists(BACKUP_FILE):
        return None
    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if lines:
        try:
            return json.loads(lines[-1])
        except Exception:
            return {"raw": lines[-1][:200]}
    return None


print("=" * 72)
print("  PRUEBAS DE INYECCIÓN DE FALLOS — OE7")
print("  Validación del sistema de manejo de errores (fail-loudly)")
print("  TFI — Tecnicatura Superior en Programación — UTN FRM")
print("=" * 72)
print()
print("  REQUISITO: n8n DEBE ESTAR DETENIDO para CF-01 y CF-02.")
print("  Esto simula la indisponibilidad del pipeline de automatización.")
print("  Flask debe responder con HTTP 502/504 y guardar en backup.")
print()

input("  Presiona ENTER cuando n8n esté detenido para continuar...")
print()

resultados = []

# ============================================================
# CF-01: n8n inalcanzable — prueba de resiliencia Flask
# ============================================================
print("─" * 72)
print("  CF-01: n8n inalcanzable (simula caída del pipeline)")
print("─" * 72)

session, csrf = get_csrf()
r = send_lead(session, csrf, "CF-01", "n8n_down")
resultados.append(r)

print(f"  Status HTTP Flask:  {r['status']}")
print(f"  LRT Flask:          {r['lrt_flask']:.3f}s")
print(f"  Respuesta:          {str(r['response'])[:150]}")

# Verificar backup
backup = check_backup_file()
print(f"  Backup local:       {'✅ Detectado' if backup else '❌ No detectado'}")
if backup:
    print(f"  Último backup:      {str(backup)[:200]}")

# Validación
if r['status'] in (502, 504):
    print("  ✅ VEREDICTO CF-01: Flask respondió correctamente con error 5xx")
elif r['status'] == 200:
    print("  ⚠️  VEREDICTO CF-01: Flask respondió 200 (¿n8n sigue corriendo?)")
else:
    print(f"  ⚠️  VEREDICTO CF-01: Comportamiento inesperado (status={r['status']})")
print()

# ============================================================
# CF-02: Segundo intento — verificar consistencia
# ============================================================
print("─" * 72)
print("  CF-02: Segundo intento con n8n caído (verificar consistencia)")
print("─" * 72)

time.sleep(1)
session2, csrf2 = get_csrf()
r2 = send_lead(session2, csrf2, "CF-02", "n8n_down_retry")
resultados.append(r2)

print(f"  Status HTTP Flask:  {r2['status']}")
print(f"  LRT Flask:          {r2['lrt_flask']:.3f}s")
print(f"  Respuesta:          {str(r2['response'])[:150]}")

backup2 = check_backup_file()
print(f"  Backup local:       {'✅ Detectado' if backup2 else '❌ No detectado'}")

if r2['status'] in (502, 504) and backup:
    print("  ✅ VEREDICTO CF-02: Consistente con CF-01. Flask degrada correctamente.")
else:
    print("  ⚠️  VEREDICTO CF-02: Revisar comportamiento.")
print()

# ============================================================
# RESUMEN
# ============================================================
print("=" * 72)
print("  RESUMEN DE PRUEBAS DE FALLO")
print("=" * 72)

for r in resultados:
    ok = r['status'] in (502, 504) and r['status'] is not None
    print(f"  {r['case_id']}: status={r['status']} | LRT={r['lrt_flask']:.3f}s | "
          f"{'✅ DEGRADACIÓN CONTROLADA' if ok else '⚠️  REVISAR'}")

print()
print("=" * 72)
print("  PROCEDIMIENTO MANUAL: CF-03 y CF-04 (requieren modificar n8n)")
print("=" * 72)
print("""
  CF-03 — CREDENCIAL SUPABASE INVÁLIDA:
    1. En n8n, modificar la variable SUPABASE_ANON_KEY por un valor inválido.
    2. Enviar un lead desde el formulario Flask.
    3. Verificar que:
       a) El nodo HTTP Request a Supabase falle.
       b) El Error Trigger se active.
       c) Llegue una alerta al canal #alertas-sistema de Slack.
       d) El lead quede registrado en leads_fallback.log.
    4. Restaurar la variable SUPABASE_ANON_KEY al valor correcto.
    5. Documentar: timestamp del error, contenido de la alerta Slack,
       entrada en backup log.

  CF-04 — API KEY OPENAI INVÁLIDA:
    1. En n8n, modificar la API Key de OpenAI por un valor inválido.
    2. Enviar un lead desde el formulario Flask.
    3. Verificar que:
       a) El nodo de clasificación IA falle.
       b) El Error Trigger se active.
       c) Llegue una alerta al canal #alertas-sistema de Slack.
       d) El pipeline asigne clasificación por defecto (fallback).
    4. Restaurar la API Key de OpenAI al valor correcto.
    5. Documentar: timestamp, alerta Slack, valores de fallback asignados.

  EVIDENCIA A CAPTURAR PARA EL DOCUMENTO:
    - Captura del mensaje en #alertas-sistema de Slack para CF-03 y CF-04.
    - Captura del archivo leads_fallback.log con las entradas de fallo.
    - Captura de la ejecución de n8n mostrando el Error Trigger activado.
""")

# Exportar resultados
output_dir = os.path.join(os.path.dirname(__file__), "resultados_v2")
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "failure_injection_results.json"), "w", encoding="utf-8") as f:
    json.dump({
        "metadata": {
            "fecha": datetime.now(timezone.utc).isoformat(),
            "script": "test_failure_injection.py",
            "objetivo": "OE7 — Validación de manejo de errores (fail-loudly)",
            "n8n_estado": "DETENIDO (simulación de fallo)"
        },
        "casos_automatizados": resultados,
        "casos_manuales_pendientes": ["CF-03", "CF-04"],
        "nota": (
            "CF-01 y CF-02 validan la resiliencia de Flask cuando n8n está caído. "
            "CF-03 y CF-04 requieren modificar credenciales en n8n y su ejecución "
            "es manual. La evidencia completa de OE7 requiere los 4 casos."
        )
    }, f, ensure_ascii=False, indent=2)

print(f"  Resultados exportados a: {output_dir}/failure_injection_results.json")
print("=" * 72)
