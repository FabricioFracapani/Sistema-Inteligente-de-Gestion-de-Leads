"""
============================================================
SISTEMA INTELIGENTE DE GESTIÓN DE LEADS
Dashboard de Ventas - Streamlit
TFI - Tecnicatura Superior en Programación - UTN FRM

Conecta a Supabase PostgreSQL y muestra:
- Leads nuevos con clasificación de IA
- Filtros por estado, prioridad, clasificación
- Métricas en tiempo real
- Detalle de cada lead (mensaje original + respuesta IA)
============================================================
"""
import streamlit as st
import os
from datetime import datetime, timedelta
from supabase import create_client, Client

# ============================================
# CONFIGURACIÓN
# ============================================
st.set_page_config(
    page_title="Dashboard de Leads | TFI UTN",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conexión a Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "https://TU_PROJECT_ID.supabase.co")
    key = os.getenv("SUPABASE_ANON_KEY", "TU_ANON_KEY")
    return create_client(url, key)

supabase = init_supabase()

# ============================================
# ESTILOS CSS
# ============================================
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1B3A5C;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 0.9rem;
        color: #888;
        margin-top: -10px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1B3A5C 0%, #2E86C1 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.85;
    }
    .lead-card {
        border-left: 4px solid #2E86C1;
        padding: 10px 15px;
        margin: 8px 0;
        border-radius: 6px;
        background: #f8f9fa;
    }
    .lead-card.compra { border-left-color: #e74c3c; }
    .lead-card.info { border-left-color: #2E86C1; }
    .lead-card.soporte { border-left-color: #f39c12; }
    .lead-card.spam { border-left-color: #95a5a6; }
    .priority-high { color: #e74c3c; font-weight: bold; }
    .priority-medium { color: #f39c12; font-weight: bold; }
    .priority-low { color: #27ae60; }
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER
# ============================================
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<p class="main-header">📊 Dashboard de Leads</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Pipeline Inteligente — n8n + IA + Supabase</p>', unsafe_allow_html=True)
with col2:
    st.metric("⏱️ Actualizado", datetime.now().strftime("%H:%M:%S"))

st.divider()

# ============================================
# SIDEBAR - FILTROS
# ============================================
with st.sidebar:
    st.markdown("### 🔍 Filtros")

    # Rango de fechas
    col_a, col_b = st.columns(2)
    with col_a:
        fecha_desde = st.date_input("Desde", datetime.now() - timedelta(days=7))
    with col_b:
        fecha_hasta = st.date_input("Hasta", datetime.now())

    # Clasificación IA
    clasificaciones = st.multiselect(
        "Clasificación IA",
        ["compra_inmediata", "solicita_info", "soporte", "spam"],
        default=["compra_inmediata", "solicita_info", "soporte"]
    )

    # Estado
    estados = st.multiselect(
        "Estado",
        ["nuevo", "contactado", "en_negociacion", "ganado", "perdido", "spam"],
        default=["nuevo", "contactado", "en_negociacion"]
    )

    # Prioridad mínima
    prioridad_min = st.slider("Prioridad mínima (IA)", 0, 100, 30)

    # Fuente
    fuentes = st.multiselect(
        "Fuente",
        ["landing_page", "meta_ads", "wordpress"],
        default=["landing_page", "meta_ads", "wordpress"]
    )

    st.divider()
    st.caption("TFI — UTN FRM — 2026")
    st.caption("Fracapani · Lepez")

# ============================================
# CARGAR DATOS DESDE SUPABASE
# ============================================
@st.cache_data(ttl=30)  # Cache por 30 segundos
def cargar_leads(fecha_desde, fecha_hasta):
    try:
        response = (
            supabase.table("leads")
            .select("*")
            .gte("timestamp_ingesta", fecha_desde.isoformat())
            .lte("timestamp_ingesta", (fecha_hasta + timedelta(days=1)).isoformat())
            .order("timestamp_ingesta", desc=True)
            .limit(200)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error conectando a Supabase: {e}")
        return []

leads = cargar_leads(fecha_desde, fecha_hasta)

# Aplicar filtros en memoria
leads_filtrados = [
    l for l in leads
    if l.get("ia_clasificacion") in clasificaciones
    and l.get("estado") in estados
    and (l.get("ia_prioridad") or 0) >= prioridad_min
    and l.get("fuente") in fuentes
]

# ============================================
# MÉTRICAS (KPI CARDS)
# ============================================
total = len(leads)
compras = sum(1 for l in leads if l.get("ia_clasificacion") == "compra_inmediata")
info = sum(1 for l in leads if l.get("ia_clasificacion") == "solicita_info")
spam = sum(1 for l in leads if l.get("ia_clasificacion") == "spam")
prioridad_promedio = sum(l.get("ia_prioridad") or 0 for l in leads) / max(total, 1)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1B3A5C 0%, #2E86C1 100%);">
            <div class="metric-value">{total}</div>
            <div class="metric-label">Total Leads</div>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%);">
            <div class="metric-value">{compras}</div>
            <div class="metric-label">🔥 Compra Inmediata</div>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #2471a3 0%, #2e86c1 100%);">
            <div class="metric-value">{info}</div>
            <div class="metric-label">ℹ️ Solicita Info</div>
        </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #7d8c8d 0%, #95a5a6 100%);">
            <div class="metric-value">{spam}</div>
            <div class="metric-label">🚫 Spam Detectado</div>
        </div>
    """, unsafe_allow_html=True)
with col5:
    st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);">
            <div class="metric-value">{prioridad_promedio:.0f}</div>
            <div class="metric-label">⭐ Prioridad Promedio</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ============================================
# TABLA DE LEADS
# ============================================
st.markdown(f"### 📋 Leads ({len(leads_filtrados)} resultados)")

if not leads_filtrados:
    st.info("No hay leads que coincidan con los filtros. Probá ajustando los criterios del sidebar.")
else:
    # Construir tabla
    for lead in leads_filtrados:
        prioridad = lead.get("ia_prioridad") or 0
        clasificacion = lead.get("ia_clasificacion") or "sin_clasificar"

        # Color según clasificación
        color_map = {
            "compra_inmediata": "compra",
            "solicita_info": "info",
            "soporte": "soporte",
            "spam": "spam"
        }

        emoji_map = {
            "compra_inmediata": "🔥",
            "solicita_info": "ℹ️",
            "soporte": "🛠️",
            "spam": "🚫"
        }

        prioridad_class = "priority-high" if prioridad >= 70 else "priority-medium" if prioridad >= 40 else "priority-low"

        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                nombre_completo = f"{lead.get('nombre', '')} {lead.get('apellido', '')}".strip()
                st.markdown(f"""
                    <div class="lead-card {color_map.get(clasificacion, 'info')}">
                        <strong>{emoji_map.get(clasificacion, '')} {nombre_completo}</strong>
                        <span class="{prioridad_class}"> · {prioridad}/100</span><br>
                        <small>📧 {lead.get('email', '')} · {lead.get('ia_resumen', 'Sin resumen')[:120]}</small>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.caption(f"Fuente: {lead.get('fuente', 'N/A')}")
                st.caption(f"Estado: {lead.get('estado', 'nuevo')}")

            with col3:
                if st.button("🔍 Ver", key=f"btn_{lead.get('id_lead')}", use_container_width=True):
                    st.session_state["lead_seleccionado"] = lead

# ============================================
# DETALLE DEL LEAD SELECCIONADO
# ============================================
if "lead_seleccionado" in st.session_state and st.session_state["lead_seleccionado"]:
    lead = st.session_state["lead_seleccionado"]

    st.divider()
    st.markdown("### 🔍 Detalle del Lead")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Nombre:** {lead.get('nombre', '')} {lead.get('apellido', '')}")
        st.markdown(f"**Email:** {lead.get('email', '')}")
        st.markdown(f"**Teléfono:** {lead.get('telefono', 'No proporcionado')}")
        st.markdown(f"**Fuente:** {lead.get('fuente', 'N/A')}")
        st.markdown(f"**Fecha:** {lead.get('timestamp_ingesta', '')}")

    with col2:
        st.markdown(f"**Clasificación IA:** {lead.get('ia_clasificacion', 'N/A')}")
        st.markdown(f"**Prioridad IA:** {lead.get('ia_prioridad', 0)}/100")
        st.markdown(f"**Confianza IA:** {lead.get('ia_confianza', 0):.0%}")
        st.markdown(f"**Estado:** {lead.get('estado', 'nuevo')}")
        st.markdown(f"**ID:** `{lead.get('id_lead', '')}`")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 💬 Mensaje Original")
        st.info(lead.get("mensaje", "Sin mensaje"))
    with col_b:
        st.markdown("#### 🤖 Resumen (IA)")
        st.success(lead.get("ia_resumen", "Sin clasificar"))

    if lead.get("ia_respuesta"):
        st.markdown("#### 📧 Email Generado por IA")
        with st.expander("Ver email completo", expanded=False):
            st.html(lead["ia_respuesta"])

    if st.button("❌ Cerrar detalle"):
        del st.session_state["lead_seleccionado"]
        st.rerun()

# ============================================
# FOOTER
# ============================================
st.divider()
st.caption(
    "Pipeline de Leads con IA · Flask + n8n + GPT-4o-mini + Supabase + Streamlit · "
    "TFI Tecnicatura Superior en Programación · UTN FRM · 2026"
)
