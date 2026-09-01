"""
============================================================
SISTEMA INTELIGENTE DE GESTIÓN DE LEADS
Dashboard de Ventas - Streamlit
TFI - Tecnicatura Superior en Programación - UTN FRM

Conecta a Supabase PostgreSQL y muestra:
- Leads nuevos con clasificación de IA
- Filtros por estado, prioridad, clasificación, búsqueda
- Métricas en tiempo real
- Detalle de cada lead (mensaje original + respuesta IA)

UI: usa exclusivamente componentes nativos de Streamlit
(st.metric, st.container(border=True), st.badge) para que
el modo oscuro/claro (⋮ Menú > Settings > Theme) se aplique
de forma automática y consistente en toda la app.
============================================================
"""
import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

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
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "Faltan SUPABASE_URL y/o SUPABASE_ANON_KEY. "
            "Definilas en el entorno antes de iniciar el dashboard."
        )
    client = create_client(url, key)
    _auth_dashboard(client)
    return client


def _auth_dashboard(client: Client) -> None:
    email = os.getenv("SUPABASE_AUTH_EMAIL")
    password = os.getenv("SUPABASE_AUTH_PASSWORD")
    if not email or not password:
        return
    try:
        client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        raise RuntimeError(f"No se pudo autenticar en Supabase: {e}") from e

supabase = init_supabase()

# ============================================
# ESTILOS CSS (basados en variables de tema de Streamlit
# -> se adaptan solas a modo claro/oscuro, no hay colores fijos)
# ============================================
st.markdown("""
<style>
    .block-container { padding-top: 3.2rem; }

    .app-title {
        font-size: 1.9rem;
        font-weight: 800;
        line-height: 1.4;
        margin-bottom: 0;
        letter-spacing: -0.02em;
    }
    .app-subtitle {
        font-size: 0.92rem;
        color: var(--text-color);
        opacity: 0.6;
        margin-top: -6px;
    }

    /* Tarjetas nativas (st.container(border=True)) con hover sutil */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }

    section[data-testid="stSidebar"] .stCaption {
        opacity: 0.65;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER
# ============================================
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.markdown('<p class="app-title">📊 Dashboard de Leads</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Pipeline Inteligente — n8n + IA + Supabase</p>',
        unsafe_allow_html=True
    )
with col_refresh:
    st.caption(f"⏱️ Última carga: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ============================================
# SIDEBAR - FILTROS
# ============================================
CLASIFICACIONES_OPC = ["compra_inmediata", "solicita_info", "soporte", "spam"]
ESTADOS_OPC = ["nuevo", "contactado", "en_negociacion", "ganado", "perdido", "spam"]
FUENTES_OPC = ["landing_page", "meta_ads", "wordpress", "test_100_v3"]

with st.sidebar:
    st.markdown("### 🔍 Filtros")

    busqueda = st.text_input(
        "Buscar por nombre o email",
        key="f_busqueda",
        placeholder="Ej: Juan Pérez o juan@mail.com"
    )

    st.markdown("**Rango de fechas**")
    col_a, col_b = st.columns(2)
    with col_a:
        fecha_desde = st.date_input(
            "Desde", datetime.now() - timedelta(days=7), key="f_fecha_desde"
        )
    with col_b:
        fecha_hasta = st.date_input("Hasta", datetime.now(), key="f_fecha_hasta")

    clasificaciones = st.multiselect(
        "Clasificación IA",
        CLASIFICACIONES_OPC,
        default=["compra_inmediata", "solicita_info", "soporte"],
        key="f_clasificaciones"
    )

    estados = st.multiselect(
        "Estado",
        ESTADOS_OPC,
        default=["nuevo", "contactado", "en_negociacion"],
        key="f_estados"
    )

    prioridad_min = st.slider(
        "Prioridad mínima (IA)", 0, 100, 30, key="f_prioridad_min"
    )

    fuentes = st.multiselect(
        "Fuente", FUENTES_OPC, default=FUENTES_OPC, key="f_fuentes"
    )

    st.button(
        "↺ Restablecer filtros",
        use_container_width=True,
        on_click=lambda: [
            st.session_state.pop(k, None)
            for k in (
                "f_busqueda", "f_fecha_desde", "f_fecha_hasta",
                "f_clasificaciones", "f_estados", "f_prioridad_min", "f_fuentes"
            )
        ]
    )

    st.divider()
    st.caption("🌓 Podés cambiar el tema claro/oscuro desde el menú ⋮ → Settings → Theme")
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

with st.spinner("Cargando leads..."):
    leads = cargar_leads(fecha_desde, fecha_hasta)

# Aplicar filtros en memoria
busqueda_norm = (busqueda or "").strip().lower()

def _coincide_busqueda(lead: dict) -> bool:
    if not busqueda_norm:
        return True
    texto = f"{lead.get('nombre', '')} {lead.get('apellido', '')} {lead.get('email', '')}".lower()
    return busqueda_norm in texto

leads_filtrados = [
    l for l in leads
    if l.get("ia_clasificacion") in clasificaciones
    and l.get("estado") in estados
    and (l.get("ia_prioridad") or 0) >= prioridad_min
    and l.get("fuente") in fuentes
    and _coincide_busqueda(l)
]

# ============================================
# MÉTRICAS (KPI CARDS) — st.metric nativo, theme-aware
# ============================================
total = len(leads)
compras = sum(1 for l in leads if l.get("ia_clasificacion") == "compra_inmediata")
info = sum(1 for l in leads if l.get("ia_clasificacion") == "solicita_info")
spam = sum(1 for l in leads if l.get("ia_clasificacion") == "spam")
prioridad_promedio = sum(l.get("ia_prioridad") or 0 for l in leads) / max(total, 1)

def _pct(n: int) -> str:
    return f"{(n / total * 100):.0f}% del total" if total else "sin datos"

kpi_cols = st.columns(5)
kpi_data = [
    ("📥", "Total Leads", total, None),
    ("🔥", "Compra Inmediata", compras, _pct(compras)),
    ("ℹ️", "Solicita Info", info, _pct(info)),
    ("🚫", "Spam Detectado", spam, _pct(spam)),
    ("⭐", "Prioridad Promedio", f"{prioridad_promedio:.0f}/100", None),
]
for col, (icon, label, value, delta) in zip(kpi_cols, kpi_data):
    with col:
        with st.container(border=True):
            st.metric(f"{icon} {label}", value, delta=delta, delta_color="off")

st.divider()

# ============================================
# TABLA DE LEADS
# ============================================
st.markdown(f"### 📋 Leads ({len(leads_filtrados)} de {total} resultados)")

CLASIFICACION_META = {
    "compra_inmediata": ("🔥", "Compra inmediata", "red"),
    "solicita_info": ("ℹ️", "Solicita info", "blue"),
    "soporte": ("🛠️", "Soporte", "orange"),
    "spam": ("🚫", "Spam", "gray"),
}
ESTADO_COLOR = {
    "nuevo": "blue",
    "contactado": "violet",
    "en_negociacion": "orange",
    "ganado": "green",
    "perdido": "gray",
    "spam": "gray",
}

if not leads_filtrados:
    st.info(
        "No hay leads que coincidan con los filtros. "
        "Probá ajustando los criterios del panel lateral o usá **↺ Restablecer filtros**."
    )
else:
    for lead in leads_filtrados:
        prioridad = lead.get("ia_prioridad") or 0
        clasificacion = lead.get("ia_clasificacion") or "sin_clasificar"
        estado = lead.get("estado") or "nuevo"
        icon, label, color = CLASIFICACION_META.get(clasificacion, ("❔", "Sin clasificar", "gray"))

        if prioridad >= 70:
            prio_icon, prio_label, prio_color = "🔺", "Alta", "red"
        elif prioridad >= 40:
            prio_icon, prio_label, prio_color = "▪️", "Media", "orange"
        else:
            prio_icon, prio_label, prio_color = "🔻", "Baja", "green"

        nombre_completo = f"{lead.get('nombre', '')} {lead.get('apellido', '')}".strip() or "Sin nombre"

        with st.container(border=True):
            col_info, col_badges, col_action = st.columns([3, 2.2, 1])

            with col_info:
                st.markdown(f"**{nombre_completo}**")
                st.caption(f"📧 {lead.get('email', 'Sin email')}")
                resumen = (lead.get("ia_resumen") or "Sin resumen")[:120]
                st.caption(resumen)

            with col_badges:
                st.markdown(f":{color}[{icon} **{label}**]")
                st.markdown(f":{prio_color}[{prio_icon} Prioridad {prio_label} · {prioridad}/100]")
                st.markdown(
                    f":{ESTADO_COLOR.get(estado, 'gray')}[● {estado.replace('_', ' ').title()}]"
                )

            with col_action:
                st.caption(f"Fuente: {lead.get('fuente', 'N/A')}")

            with st.expander("🔍 Ver detalle", expanded=False):
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
                    st.markdown(f"**Confianza IA:** {(lead.get('ia_confianza') or 0):.0%}")
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

# ============================================
# FOOTER
# ============================================
st.divider()
st.caption(
    "Pipeline de Leads con IA · Flask + n8n + GPT-4o-mini + Supabase + Streamlit · "
    "TFI Tecnicatura Superior en Programación · UTN FRM · 2026"
)
