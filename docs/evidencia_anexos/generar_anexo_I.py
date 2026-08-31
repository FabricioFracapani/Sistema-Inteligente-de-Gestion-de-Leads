"""
======================================================================
REGENERADOR DEL ANEXO I - a partir del dashboard real (dashboard.py)
El Anexo I anterior (texto pegado en el .docx) estaba escrito a mano y
desactualizado: por ejemplo, listaba solo 3 fuentes de lead
(landing_page, meta_ads, wordpress) cuando dashboard.py ya filtra por
una cuarta ("test_100_v3"). Ademas quedo fechado 2026-08-05, antes de
la corrida real de pruebas (2026-08-18) que se supone documenta -un
problema de forma (M-14): evidencia fechada antes del hecho que prueba.

Este script lee dashboard/dashboard.py y dashboard/requirements.txt con
expresiones regulares (no ejecuta Streamlit) para extraer KPIs, filtros,
cache y limite de consulta reales, y estampa su propia fecha de
generacion (UTC) en cada corrida.

USO:
    python docs/evidencia_anexos/generar_anexo_I.py

SALIDA:
    docs/evidencia_anexos/Anexo_I_Dashboard_Streamlit.txt
======================================================================
"""
import os
import re
import subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DASHBOARD_PATH = os.path.join(ROOT, "dashboard", "dashboard.py")
REQUIREMENTS_PATH = os.path.join(ROOT, "dashboard", "requirements.txt")
OUT_PATH = os.path.join(ROOT, "docs", "evidencia_anexos", "Anexo_I_Dashboard_Streamlit.txt")
REPO_URL = "https://github.com/Martinlepez031/Sistema-Inteligente-de-Gestion-de-Leads"


def get_commit_hash():
    try:
        h = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return h
    except Exception:
        return None


def leer(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extraer_version(requirements, paquete):
    m = re.search(rf"^{paquete}==([\w\.]+)", requirements, re.MULTILINE)
    return m.group(1) if m else "desconocida"


def extraer_metric_labels(src):
    # KPI cards: <div class="metric-label">TEXTO</div>
    return re.findall(r'<div class="metric-label">([^<]+)</div>', src)


def extraer_lista(src, variable):
    # busca "variable = st.multiselect(\n    "Label",\n    [ "a", "b", ... ]"
    m = re.search(
        rf'{re.escape(variable)}\s*=\s*st\.multiselect\(\s*"([^"]+)"\s*,\s*\[([^\]]+)\]',
        src,
    )
    if not m:
        return None, []
    label = m.group(1)
    opciones = re.findall(r'"([^"]+)"', m.group(2))
    return label, opciones


def extraer_slider(src, variable):
    m = re.search(
        rf'{re.escape(variable)}\s*=\s*st\.slider\(\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)',
        src,
    )
    if not m:
        return None
    label, lo, hi, default = m.groups()
    return label, int(lo), int(hi), int(default)


def extraer_cache_ttl(src):
    m = re.search(r"@st\.cache_data\(ttl=(\d+)\)", src)
    return int(m.group(1)) if m else None


def extraer_limit(src):
    m = re.search(r"\.limit\((\d+)\)", src)
    return int(m.group(1)) if m else None


def extraer_color_map(src):
    m = re.search(r"color_map\s*=\s*\{([^}]+)\}", src)
    if not m:
        return {}
    pares = re.findall(r'"([^"]+)":\s*"([^"]+)"', m.group(1))
    return dict(pares)


def main():
    src = leer(DASHBOARD_PATH)
    requirements = leer(REQUIREMENTS_PATH)

    streamlit_version = extraer_version(requirements, "streamlit")
    supabase_version = extraer_version(requirements, "supabase")

    kpis = extraer_metric_labels(src)
    _, fechas_default_dias = "Rango de fechas (desde/hasta)", 7  # st.date_input, no es lista

    label_clasif, opciones_clasif = extraer_lista(src, "clasificaciones")
    label_estado, opciones_estado = extraer_lista(src, "estados")
    label_fuente, opciones_fuente = extraer_lista(src, "fuentes")
    slider = extraer_slider(src, "prioridad_min")
    ttl = extraer_cache_ttl(src)
    limite = extraer_limit(src)
    color_map = extraer_color_map(src)

    colores_es = {
        "compra": "Rojo",
        "info": "Azul",
        "soporte": "Naranja",
        "spam": "Gris",
    }

    lineas = []
    lineas.append("=" * 72)
    lineas.append("ANEXO I — EVIDENCIA DEL DASHBOARD DE VENTAS (Streamlit)")
    lineas.append("=" * 72)
    lineas.append("")
    lineas.append("CARACTERISTICAS DEL DASHBOARD:")
    lineas.append("-" * 50)
    lineas.append(f"  - Framework: Streamlit {streamlit_version} (pinneado en dashboard/requirements.txt)")
    lineas.append(f"  - Conexion: Supabase PostgreSQL via supabase-py {supabase_version}")
    lineas.append("  - Puerto: 8501 (localhost)")
    lineas.append("")
    lineas.append(f"KPIs EN TIEMPO REAL ({len(kpis)} metricas, extraidas de dashboard.py):")
    lineas.append("-" * 50)
    for i, label in enumerate(kpis, 1):
        lineas.append(f"  {i}. {label}")
    lineas.append("")
    lineas.append("FILTROS DISPONIBLES (extraidos de dashboard.py):")
    lineas.append("-" * 50)
    lineas.append(f"  1. Rango de fechas (desde/hasta, default: ultimos {fechas_default_dias} dias)")
    lineas.append(f"  2. {label_clasif} (multiselect: {', '.join(opciones_clasif)})")
    lineas.append(f"  3. {label_estado} (multiselect: {', '.join(opciones_estado)})")
    if slider:
        slabel, slo, shi, sdef = slider
        lineas.append(f"  4. {slabel} (slider: {slo}-{shi}, default: {sdef})")
    lineas.append(f"  5. {label_fuente} (multiselect: {', '.join(opciones_fuente)})")
    lineas.append("")
    lineas.append("VISTA DETALLADA DE LEAD:")
    lineas.append("-" * 50)
    lineas.append("  - Nombre completo, email, fuente, estado")
    lineas.append("  - Clasificacion IA, prioridad, resumen generado por IA")
    lineas.append("  - Mensaje original del lead (truncado a 120 caracteres en la tarjeta)")
    lineas.append("  - Boton 'Ver' para inspeccionar el lead seleccionado")
    lineas.append("")
    lineas.append("CODIGO DE COLORES POR CLASIFICACION (color_map real del codigo):")
    lineas.append("-" * 50)
    for clave, valor in color_map.items():
        lineas.append(f"  - {clave}: {colores_es.get(valor, valor)}")
    lineas.append("")
    lineas.append("RENDIMIENTO:")
    lineas.append("-" * 50)
    if ttl is not None:
        lineas.append(f"  - Cache de datos: {ttl} segundos (@st.cache_data(ttl={ttl}))")
    if limite is not None:
        lineas.append(f"  - Limite de consulta: {limite} leads (.limit({limite}) en la query a Supabase)")
    lineas.append("  - Diseno responsive con CSS personalizado (gradientes en las tarjetas KPI)")
    lineas.append("")
    lineas.append("NOTA: Para obtener una captura de pantalla del dashboard:")
    lineas.append("  1. Ejecutar: cd dashboard && streamlit run dashboard.py")
    lineas.append("  2. Abrir http://localhost:8501 en el navegador")
    lineas.append("  3. Tomar captura de pantalla completa")

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    commit_hash = get_commit_hash()
    lineas.append("")
    lineas.append(f"Documento generado: {ahora}")
    lineas.append("Fuente: dashboard/dashboard.py")
    if commit_hash:
        lineas.append(f"Commit HEAD al generar (M-13): {commit_hash}")
        lineas.append(f"Enlace: {REPO_URL}/tree/{commit_hash}")

    contenido = "\n".join(lineas) + "\n"
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"OK -> {OUT_PATH}")
    print(f"KPIs: {len(kpis)} | Generado: {ahora}")


if __name__ == "__main__":
    main()
