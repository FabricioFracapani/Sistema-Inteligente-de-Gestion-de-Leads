"""
======================================================================
SEED DIRECTO A SUPABASE - 100 casos de prueba
Inserta los leads generados por test_100_leads.py directamente en la
tabla `leads`, simulando los resultados esperados de la IA (clasificacion,
prioridad, confianza, resumen) para poblar el dashboard sin depender
del pipeline n8n + OpenAI.

USO:
    python tests/seed_test_leads_supabase.py
======================================================================
"""
import os
import sys
import json
import random
from datetime import datetime, timezone

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

from supabase import create_client  # noqa: E402
from test_100_leads import generar_100_casos  # noqa: E402

load_dotenv()
random.seed(2026)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Faltan SUPABASE_URL y/o SUPABASE_ANON_KEY. Definilas en .env antes de correr este script."
    )

PRIORIDAD_BASE = {
    "compra_inmediata": 85,
    "solicita_info": 45,
    "soporte": 25,
    "spam": 5,
    "duplicado": 50,
    "caracteres_especiales": 50,
    "mensaje_borde": 50,
    "adversarial": 40,
    "multilingue": 50,
    "email_invalido": 0,
    "telefono_invalido": 0,
}

RESUMEN_BY_TIPO = {
    "compra_inmediata": "Intención clara de contratar: pide avanzar hoy con la implementación.",
    "solicita_info": "Solicita información, cotización o demo sin urgencia explícita.",
    "soporte": "Consulta técnica o problema reportado con el servicio.",
    "spam": "Mensaje genérico/sospechoso, sin relación con el negocio.",
    "duplicado": "Entrada repetida de una consulta ya registrada.",
    "caracteres_especiales": "Mensaje con caracteres especiales o latinos.",
    "mensaje_borde": "Mensaje en el límite de longitud o contenido atípico.",
    "adversarial": "Caso adversario (inyección de prompt o rol confuso).",
    "multilingue": "Mensaje en idioma extranjero o mezcla de lenguas.",
    "email_invalido": "Email con formato inválido: rechazado en validación.",
    "telefono_invalido": "Teléfono con formato insuficiente: rechazado en validación.",
}


def clasificacion_esperada(caso):
    """Devuelve la clasificación IA esperada para el caso de prueba."""
    tipo = caso.get("tipo")
    if tipo == "spam":
        return "spam"
    if tipo in ("compra_inmediata", "solicita_info", "soporte"):
        return tipo
    # Categorías sin clasificación 100% definida: asignar la más plausible
    if caso.get("esperado", {}).get("ia_clasificacion"):
        return caso["esperado"]["ia_clasificacion"]
    if tipo == "email_invalido":
        return None
    return random.choice(["solicita_info", "soporte"])


def build_lead(caso):
    """Construye la fila para la tabla leads."""
    tipo = caso.get("tipo")
    es_invalido = tipo in ("email_invalido", "telefono_invalido")
    clasif = clasificacion_esperada(caso)

    prioridad = 0
    confianza = round(random.uniform(0.70, 0.99), 3)
    if clasif is not None:
        base = PRIORIDAD_BASE.get(clasif, 50)
        prioridad = max(1, min(100, base + random.randint(-10, 10)))

    if es_invalido:
        estado = "rechazado"
    elif clasif == "spam":
        estado = "spam"
    else:
        estado = "nuevo"

    return {
        "nombre": caso.get("nombre"),
        "apellido": caso.get("apellido"),
        "email": caso.get("email"),
        "telefono": caso.get("telefono") or None,
        "mensaje": caso.get("mensaje"),
        "fuente": "test_100_v3",
        "ia_clasificacion": clasif,
        "ia_prioridad": prioridad if clasif is not None else None,
        "ia_confianza": confianza if clasif is not None else None,
        "ia_resumen": RESUMEN_BY_TIPO.get(tipo, "Sin resumen IA disponible.") if clasif is not None else None,
        "estado": estado,
        "timestamp_ingesta": datetime.now(timezone.utc).isoformat(),
    }


def main():
    if not SUPABASE_KEY:
        print("Falta SUPABASE_ANON_KEY en el entorno.")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    casos = generar_100_casos()
    filas = [build_lead(c) for c in casos]

    # Insertar en lotes y recolectar errores
    ok = 0
    errores = 0
    for i in range(0, len(filas), 25):
        lote = filas[i:i + 25]
        try:
            response = client.table("leads").insert(lote).execute()
            ok += len(response.data)
            print(f"  Insertados {len(response.data)} (total {ok})")
        except Exception as e:
            errores += len(lote)
            print(f"  ERROR en lote {i}: {e}")

    print(f"\nResultado: {ok} insertados, {errores} con error, de {len(filas)} totales.")

    # Verificación
    try:
        count = client.table("leads").select("id_lead", count="exact").execute()
        print(f"Total en tabla leads: {count.count}")
    except Exception as e:
        print(f"No se pudo verificar count: {e}")


if __name__ == "__main__":
    main()