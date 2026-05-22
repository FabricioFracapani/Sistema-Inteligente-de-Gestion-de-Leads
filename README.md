# ⚡ Sistema Inteligente de Gestión de Leads

<div align="center">

**Integración de Orquestación Low-Code, IA Generativa y Desarrollo Web Seguro con Python**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![n8n](https://img.shields.io/badge/n8n-1.x-EA4B71?logo=n8n&logoColor=white)](https://n8n.io)
[![OpenAI](https://img.shields.io/badge/GPT--4o--mini-412991?logo=openai&logoColor=white)](https://platform.openai.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/Licencia-MIT-green)](LICENSE)
[![Costo](https://img.shields.io/badge/Costo-$0-success)]()
[![Seguridad](https://img.shields.io/badge/Seguridad-OWASP%20%2B%20RLS-blue)]()

</div>

---

## 📋 ¿Qué problema resuelve?

Las PyMEs pierden entre el **35% y 50% de sus oportunidades de venta** por no responder a tiempo a los clientes potenciales que llegan por formularios web. Responder en menos de 5 minutos genera **6 a 10 veces más probabilidades de conversión** que hacerlo 30 minutos después (Harvard Business Review, 2011).

Este sistema automatiza todo el ciclo de vida del lead: **captura → clasificación con IA → respuesta personalizada → persistencia → notificación**, reduciendo el tiempo de respuesta de 4-8 horas a **3.2 segundos**.

---

## 🧠 Arquitectura

```
   Usuario              Flask               n8n + IA               PostgreSQL          Streamlit
      │                   │                    │                       │                   │
      │  Completa form    │                    │                       │                   │
      │──────────────────>│                    │                       │                   │
      │                   │  POST /api/leads   │                       │                   │
      │                   │───────────────────>│                       │                   │
      │                   │                    │  Normaliza + Valida   │                   │
      │                   │                    │──────┐                │                   │
      │                   │                    │      │ (ETL)          │                   │
      │                   │                    │<─────┘                │                   │
      │                   │                    │                       │                   │
      │                   │                    │───> GPT-4o-mini ────>│                   │
      │                   │                    │     "Clasificá"       │                   │
      │                   │                    │<──── clasificación ───│                   │
      │                   │                    │                       │                   │
      │                   │                    │───> GPT-4o-mini ────>│                   │
      │                   │                    │     "Generá email"    │                   │
      │                   │                    │<─── email HTML ──────>│                   │
      │                   │                    │                       │                   │
      │                   │                    │  INSERT (REST API)    │                   │
      │                   │                    │──────────────────────>│                   │
      │                   │                    │                       │  SELECT * FROM    │
      │                   │                    │                       │<──────────────────│
      │                   │                    │                       │─── leads ────────>│
      │   HTTP 200 +      │                    │                       │                   │
      │<──────────────────│  Gmail + Slack     │                       │                   │
      │   email IA        │<───────────────────│                       │                   │
```

---

## 🚀 Stack Tecnológico

| Componente | Tecnología | Rol | Costo |
|---|---|---|---|
| Landing Page | Flask 3.x + CSS puro | Formulario seguro + SEO | $0 |
| Orquestador | n8n 1.x (Docker) | Pipeline de automatización | $0 |
| IA | GPT-4o-mini (OpenAI) | Clasificación + email personalizado | ~$0.0001/lead |
| Base de Datos | Supabase PostgreSQL | Persistencia + Row Level Security | $0 |
| Dashboard | Streamlit | KPIs + filtros + detalle de leads | $0 |
| Email | Gmail API | Envío automático | $0 |
| Notificaciones | Slack API | Alertas al equipo | $0 |
| **TOTAL** | | | **$0** |

---

## 🔒 Seguridad por Diseño

13 medidas en 3 capas, siguiendo OWASP Top 10:

| Capa | Medidas |
|---|---|
| **Aplicación** | CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, CORS, Rate Limiting, CSRF Token, Input Sanitization, Honeypot anti-spam |
| **Datos** | Row Level Security (3 roles, 11 políticas), SHA-256 de PII, IP anonimizada, API Keys con expiración |
| **Integración** | Credential Store AES-256, variables de entorno (sin texto plano), HTTPS/TLS en tránsito |

---

## 📊 Resultados

50 casos de prueba controlados (CP-01 a CP-10):

| Métrica | Valor |
|---|---|
| Lead Response Time (promedio) | 3.2 segundos |
| Casos bajo 5 segundos | 96% |
| Precisión IA (estricta) | 84.4% |
| Recall de spam | 100% |
| Tasa de ingesta exitosa | 95.6% |
| Eventos perdidos sin registro | 0 |

---

## 📁 Estructura del Proyecto

```
automatizacion_inteligente/
├── landing_page/            # Flask + HTML + CSS
│   ├── app.py               # Servidor: rutas, seguridad, validación
│   ├── templates/
│   │   ├── index.html       # Landing page con SEO + OG + JSON-LD
│   │   └── gracias.html     # Página post-envío con timeline
│   ├── static/
│   │   └── style.css        # Design system completo (11 KB)
│   └── requirements.txt
├── n8n_workflow/
│   └── pipeline_leads_ia.json  # Workflow n8n con 14 nodos (importable)
├── database/
│   └── schema.sql           # PostgreSQL + RLS + roles + triggers
├── dashboard/
│   ├── dashboard.py         # Streamlit con KPIs y filtros
│   └── requirements.txt
├── tests/
│   └── test_50_leads.py     # 50 casos de prueba automatizados
├── docs/
│   └── LEVANTAR_PROYECTO.md # Instrucciones paso a paso
├── TFI - Sistema Inteligente de Gestion de Leads.docx  # Documento académico
├── TFI_NotebookLM.md        # Fuente para NotebookLM (video + slides)
└── plan_proyecto.docx       # Planificación del proyecto
```

---

## ⚡ Levantar el proyecto

### Requisitos
- Python 3.10+
- Docker Desktop
- Cuentas gratuitas: [Supabase](https://supabase.com), [OpenAI](https://platform.openai.com), [Slack](https://api.slack.com)

### 1. Base de Datos (5 min)

```bash
# Crear proyecto en supabase.com → copiar Project ID + Anon Key
# SQL Editor → pegar y ejecutar database/schema.sql
```

### 2. n8n + IA (5 min)

```bash
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
# Abrir http://localhost:5678 → crear cuenta
# Importar n8n_workflow/pipeline_leads_ia.json
# Configurar credenciales: OpenAI, Gmail, Slack
```

### 3. Landing Page (2 min)

```bash
cd landing_page
python -m venv venv && source venv/bin/activate  # Linux/Mac
python -m venv venv && .\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
python app.py  # → http://localhost:5000
```

### 4. Dashboard (2 min)

```bash
cd dashboard
pip install -r requirements.txt
export SUPABASE_URL="https://TU_ID.supabase.co" SUPABASE_ANON_KEY="tu-key"
streamlit run dashboard.py  # → http://localhost:8501
```

### 5. Pruebas

```bash
cd tests
pip install requests
python test_50_leads.py
```

---

## 🎓 Sobre este proyecto

Trabajo Final Integrador de la **Tecnicatura Superior en Programación** — Universidad Tecnológica Nacional, Facultad Regional Mendoza.

**Autores:** Fabricio Fracapani & Martín Lepez — 2026

**Lo que construimos:** 4 componentes de software funcionales (Flask, n8n workflow, schema SQL, dashboard Streamlit) que integran desarrollo web, automatización low-code, inteligencia artificial generativa, bases de datos con seguridad a nivel de fila, y visualización de datos — todo con un stack 100% gratuito.
