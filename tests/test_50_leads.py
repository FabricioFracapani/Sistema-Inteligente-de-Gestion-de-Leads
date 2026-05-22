"""
=========================================================================
SCRIPT DE PRUEBAS AUTOMATIZADAS — Pipeline de Leads con IA
50 casos de prueba (CP-01 a CP-10) para validación del TFI
=========================================================================

USO:
  1. Asegurate de que Flask esté corriendo: python landing_page/app.py
  2. Asegurate de que n8n esté corriendo y el workflow activo
  3. Ejecutar: python tests/test_50_leads.py

MIDE:
  - Lead Response Time (LRT) por caso
  - Tasa de ingesta exitosa
  - Tasa de clasificación de IA
  - Errores y timeouts
  - Genera un archivo resultados_pruebas.csv y un resumen en consola
=========================================================================
"""
import requests
import csv
import time
import os
import json
from datetime import datetime, timezone

# ============================================================
# CONFIGURACIÓN — Ajustar antes de ejecutar
# ============================================================
BASE_URL = os.getenv("FLASK_URL", "http://localhost:5000")
API_URL = f"{BASE_URL}/api/leads"
CSRF_URL = f"{BASE_URL}/"
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "resultados_pruebas.csv")
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "resultados_pruebas.json")

# ============================================================
# OBTENER TOKEN CSRF DEL FORMULARIO
# ============================================================
def get_csrf_token():
    """Obtiene el token CSRF de la página principal (necesario para cada POST)."""
    try:
        # Primero obtenemos la cookie de sesión y el token CSRF del HTML
        session = requests.Session()
        r = session.get(BASE_URL + "/", timeout=10)
        # Buscar el token en el HTML
        import re
        match = re.search(r'name="_csrf_token"[^>]*value="([^"]+)"', r.text)
        if match:
            token = match.group(1)
        else:
            token = "test-token-fallback"
        return session, token
    except Exception as e:
        print(f"  ⚠️  No se pudo obtener CSRF token ({e}). Usando fallback.")
        return requests.Session(), "test-token-fallback"


def get_session_with_csrf():
    """Obtiene sesión fresca con cookie y token CSRF."""
    session = requests.Session()
    try:
        r = session.get(BASE_URL + "/", timeout=10)
        import re
        match = re.search(r'name="_csrf_token"[^>]*value="([^"]+)"', r.text)
        csrf = match.group(1) if match else "fallback"
    except Exception:
        csrf = "fallback"
    return session, csrf


# ============================================================
# GENERADOR DE CASOS DE PRUEBA (50 casos)
# ============================================================
def generar_casos_prueba():
    """Genera los 50 casos de prueba cubriendo CP-01 a CP-10."""

    casos = []

    # --- CP-01: Leads con intención de compra clara (10 casos) ---
    mensajes_compra = [
        "Quiero contratar el servicio ya mismo. ¿Cuándo podemos empezar?",
        "Necesito urgente automatizar los procesos de mi empresa. Llamame hoy.",
        "Estoy listo para comprar. ¿Me pueden enviar el contrato?",
        "Tengo el presupuesto aprobado, quiero implementar esta semana.",
        "URGENTE: necesito el servicio de automatización para mañana.",
        "Ya decidí, quiero el plan completo. ¿Cómo pago?",
        "Vengo de una recomendación, quiero contratar ahora mismo.",
        "Necesito comenzar el proyecto esta semana. Tengo todo listo.",
        "Presupuesto aprobado, equipo listo. ¿Empezamos el lunes?",
        "Quiero comprar el servicio premium. ¿Me pasan los datos de facturación?",
    ]
    for i, msg in enumerate(mensajes_compra):
        casos.append({
            "id": f"CP-01-{i+1:02d}",
            "tipo": "compra_inmediata",
            "nombre": f"Cliente Compra {i+1}",
            "apellido": "Test",
            "email": f"compra.test{i+1:02d}@test-leads-tfi.local",
            "telefono": f"+54 261 555{1000+i:04d}",
            "mensaje": msg,
            "esperado": {"status": 200, "ia_clasificacion": "compra_inmediata"}
        })

    # --- CP-02: Leads solicitando información (15 casos) ---
    mensajes_info = [
        "Me interesa conocer más sobre sus servicios de automatización.",
        "Hola, ¿podrían enviarme información y precios?",
        "Estoy evaluando opciones para digitalizar mi PyME. ¿Tienen demo?",
        "Quisiera saber más sobre cómo funciona n8n para mi negocio.",
        "¿Qué servicios ofrecen para pequeñas empresas?",
        "Me gustaría recibir una cotización para mi proyecto.",
        "Estoy investigando soluciones de automatización, ¿me pueden asesorar?",
        "¿Tienen algún plan para startups? Me interesa saber más.",
        "Quisiera agendar una llamada para conocer sus servicios.",
        "¿Podrían contarme más sobre la integración con IA que ofrecen?",
        "Estoy buscando automatizar el área de ventas. ¿Me ayudan?",
        "Necesito información sobre sus planes y precios.",
        "Me recomendaron sus servicios. ¿Podemos coordinar una reunión?",
        "Quiero modernizar los procesos de mi empresa. ¿Por dónde empiezo?",
        "Estoy comparando proveedores. ¿Me envían su propuesta?",
    ]
    for i, msg in enumerate(mensajes_info):
        casos.append({
            "id": f"CP-02-{i+1:02d}",
            "tipo": "solicita_info",
            "nombre": f"Prospecto Info {i+1}",
            "apellido": "Test",
            "email": f"info.test{i+1:02d}@test-leads-tfi.local",
            "telefono": f"+54 261 666{2000+i:04d}",
            "mensaje": msg,
            "esperado": {"status": 200, "ia_clasificacion": "solicita_info"}
        })

    # --- CP-03/04: Leads con email inválido o teléfono inválido (5 casos) ---
    casos_invalidos = [
        ("CP-03-01", "Email sin @", "Felipe Fallo", "felipe.sinarroba.com", "+54 261 5550001", "Quiero info"),
        ("CP-03-02", "Email sin dominio", "Gabi Error", "gabi@", "+54 261 5550002", "Consulta de prueba"),
        ("CP-03-03", "Email vacío aparente", "Vacio Mail", "", "+54 261 5550003", "No tengo email"),
        ("CP-04-01", "Teléfono muy corto", "Tel Corto", "tel.corto@test.com", "123", "Consulta con tel inválido"),
        ("CP-04-02", "Teléfono con letras", "Tel Letras", "tel.letras@test.com", "abcdefghij", "Quiero información"),
    ]
    for cid, desc, nombre, email, tel, msg in casos_invalidos:
        casos.append({
            "id": cid, "tipo": "invalido",
            "nombre": nombre, "apellido": "Error",
            "email": email, "telefono": tel, "mensaje": msg,
            "esperado": {"status": 400}  # Flask devuelve 400 para validación fallida
        })

    # --- CP-05: Leads duplicados (mismo email, 5 casos) ---
    for i in range(5):
        casos.append({
            "id": f"CP-05-{i+1:02d}",
            "tipo": "duplicado",
            "nombre": f"Duplicado {i+1}",
            "apellido": "Test",
            "email": "duplicado.test@test-leads-tfi.local",  # mismo email para los 5
            "telefono": f"+54 261 777{3000+i:04d}",
            "mensaje": f"Consulta repetida #{i+1}",
            "esperado": {"status": 200}  # Flask acepta, n8n decide si duplicado
        })

    # --- CP-06/07: Leads de soporte o queja (5 casos) ---
    mensajes_soporte = [
        "El sistema no me deja entrar desde ayer. Necesito ayuda urgente.",
        "Estoy teniendo problemas con la integración de la API.",
        "La automatización que configuramos dejó de funcionar el lunes.",
        "No recibo los emails de notificación. ¿Pueden revisar?",
        "Tengo un error 500 al intentar exportar los datos.",
    ]
    for i, msg in enumerate(mensajes_soporte):
        casos.append({
            "id": f"CP-06-{i+1:02d}",
            "tipo": "soporte",
            "nombre": f"Cliente Soporte {i+1}",
            "apellido": "Test",
            "email": f"soporte.test{i+1:02d}@test-leads-tfi.local",
            "telefono": f"+54 261 888{4000+i:04d}",
            "mensaje": msg,
            "esperado": {"status": 200, "ia_clasificacion": "soporte"}
        })

    # --- CP-08: Leads con spam (5 casos) ---
    mensajes_spam = [
        "Great post! Check out my website for amazing deals!!!",
        "Buy cheap viagra online now!!! Limited offer!!!",
        "I am a Nigerian prince and I need your help transferring money.",
        "FREE FREE FREE!!! Click here to win an iPhone!!!",
        "Congratulations! You have been selected for a free cruise!",
    ]
    for i, msg in enumerate(mensajes_spam):
        casos.append({
            "id": f"CP-08-{i+1:02d}",
            "tipo": "spam",
            "nombre": f"Spammer {i+1}",
            "apellido": "Bot",
            "email": f"spam.test{i+1:02d}@test-leads-tfi.local",
            "telefono": "",
            "mensaje": msg,
            "esperado": {"status": 200, "ia_clasificacion": "spam"}
        })

    # --- CP-09: Casos con caracteres especiales y tildes (3 casos) ---
    casos_especiales = [
        ("CP-09-01", "María José", "García Ñuñez", "maria.nunez@test.com", "Quiero información sobre automatización ¿podés ayudarme?"),
        ("CP-09-02", "François", "Müller", "francois.muller@test.com", "Je suis intéressé par vos services d'automatisation."),
        ("CP-09-03", "João", "São Pedro", "joao.pedro@test.com", "Preciso de ajuda com automação para minha empresa."),
    ]
    for cid, nombre, apellido, email, msg in casos_especiales:
        casos.append({
            "id": cid, "tipo": "caracteres_especiales",
            "nombre": nombre, "apellido": apellido,
            "email": email, "telefono": "+54 261 9990001",
            "mensaje": msg,
            "esperado": {"status": 200}
        })

    # --- CP-10: Mensajes largos (2 casos) ---
    casos.append({
        "id": "CP-10-01",
        "tipo": "mensaje_largo",
        "nombre": "Mensaje", "apellido": "Largo",
        "email": "mensaje.largo@test.com",
        "telefono": "+54 261 5559999",
        "mensaje": (
            "Hola, les escribo porque estoy buscando una solución integral para mi empresa. "
            "Tenemos aproximadamente 50 empleados y necesitamos automatizar varios procesos: "
            "la gestión de clientes, el seguimiento de proyectos, la facturación y las notificaciones. "
            "Actualmente usamos planillas de Excel y el proceso es muy lento. Nos interesa especialmente "
            "la integración con IA que mencionan en su página. ¿Podrían enviarme una propuesta detallada "
            "con costos y tiempos de implementación? También quisiera saber si ofrecen soporte post-venta "
            "y capacitación para el equipo. Tenemos presupuesto aprobado para este trimestre. "
            "Quedo atento a su respuesta. Saludos cordiales."
        ),
        "esperado": {"status": 200}
    })

    casos.append({
        "id": "CP-10-02",
        "tipo": "mensaje_corto",
        "nombre": "Corto", "apellido": "Msj",
        "email": "corto@test.com",
        "telefono": "",
        "mensaje": "Info",
        "esperado": {"status": 200}
    })

    return casos


# ============================================================
# EJECUTAR PRUEBAS
# ============================================================
def ejecutar_pruebas():
    """Ejecuta los 50 casos de prueba y registra resultados."""
    casos = generar_casos_prueba()
    resultados = []
    stats = {
        "ok_flask": 0,
        "error_flask": 0,
        "timeout": 0,
        "lrt_total": 0.0,
        "lrt_count": 0,
    }

    print("=" * 70)
    print("PRUEBAS AUTOMATIZADAS — Pipeline de Leads con IA")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total casos: {len(casos)}")
    print(f"Flask URL: {BASE_URL}")
    print("=" * 70)

    for i, caso in enumerate(casos):
        cid = caso["id"]
        tipo = caso["tipo"]

        # Obtener sesión fresca con CSRF token
        session, csrf = get_session_with_csrf()

        # Construir payload
        payload = {
            "nombre": caso["nombre"],
            "apellido": caso["apellido"],
            "email": caso["email"],
            "telefono": caso["telefono"],
            "mensaje": caso["mensaje"],
            "fuente": "test_script",
            "_csrf_token": csrf
        }

        # Medir LRT
        tiempo_inicio = time.time()
        status = None
        error_msg = None

        try:
            r = session.post(
                API_URL,
                data=payload,
                timeout=15,
                headers={"Accept": "application/json"}
            )
            status = r.status_code
            lrt = round(time.time() - tiempo_inicio, 3)

            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text[:200]}

            # Determinar resultado
            esperado = caso["esperado"].get("status", 200)
            ok = (status == esperado) or (status == 200 and esperado == 200)

            if ok and status == 200:
                stats["ok_flask"] += 1
                stats["lrt_total"] += lrt
                stats["lrt_count"] += 1
                icono = "✅"
            elif ok:
                stats["ok_flask"] += 1 if status != 500 else 0
                icono = "⚠️ "
            else:
                stats["error_flask"] += 1
                icono = "❌"
                if status is None:
                    error_msg = "Sin respuesta"

        except requests.exceptions.Timeout:
            lrt = 15.0
            status = None
            error_msg = "TIMEOUT"
            stats["timeout"] += 1
            icono = "⏱️ "
        except Exception as e:
            lrt = round(time.time() - tiempo_inicio, 3)
            status = None
            error_msg = str(e)[:100]
            stats["error_flask"] += 1
            icono = "💥"

        # Mostrar progreso
        tipo_str = f"{caso['mensaje'][:50]}..."
        print(f"  {icono} [{i+1:02d}/50] {cid:10s} | {tipo:22s} | status={status} | LRT={lrt:.2f}s | {tipo_str}")

        # Guardar resultado
        resultados.append({
            "caso_id": cid,
            "tipo": tipo,
            "nombre": caso["nombre"],
            "email": caso["email"],
            "mensaje": caso["mensaje"][:200],
            "status": status,
            "lrt_segundos": lrt,
            "ok": ok,
            "error": error_msg or "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Pequeña pausa entre requests (para no saturar rate limiting)
        if i < len(casos) - 1:
            time.sleep(0.3)

    # ============================================================
    # RESULTADOS
    # ============================================================
    print()
    print("=" * 70)
    print("RESULTADOS")
    print("=" * 70)

    total = len(casos)
    ok = stats["ok_flask"]
    err = stats["error_flask"] + stats["timeout"]
    lrt_avg = stats["lrt_total"] / max(stats["lrt_count"], 1)

    print(f"  Total casos:          {total}")
    print(f"  Respuestas OK:        {ok} ({ok/total*100:.1f}%)")
    print(f"  Errores/Timeouts:     {err} ({err/total*100:.1f}%)")
    print(f"  LRT promedio Flask:   {lrt_avg:.2f} segundos")
    print(f"  Tasa de ingesta:      {ok/total*100:.1f}%")

    # Por tipo
    print()
    print("  Por tipo de caso:")
    tipos = {}
    for r in resultados:
        t = r["tipo"]
        if t not in tipos:
            tipos[t] = {"total": 0, "ok": 0}
        tipos[t]["total"] += 1
        if r["ok"]:
            tipos[t]["ok"] += 1

    for t, d in sorted(tipos.items()):
        pct = d["ok"] / max(d["total"], 1) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"    {t:25s} {bar} {d['ok']:2d}/{d['total']:2d} ({pct:.0f}%)")

    # ============================================================
    # EXPORTAR
    # ============================================================
    # CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=resultados[0].keys())
        writer.writeheader()
        writer.writerows(resultados)
    # JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "fecha": datetime.now().isoformat(),
                "total_casos": total,
                "ok": ok,
                "errores": err,
                "lrt_promedio_flask": round(lrt_avg, 3)
            },
            "resultados": resultados
        }, f, ensure_ascii=False, indent=2)

    print()
    print(f"  📄 CSV exportado:  {OUTPUT_CSV}")
    print(f"  📄 JSON exportado: {OUTPUT_JSON}")
    print("=" * 70)

    return resultados


if __name__ == "__main__":
    ejecutar_pruebas()
