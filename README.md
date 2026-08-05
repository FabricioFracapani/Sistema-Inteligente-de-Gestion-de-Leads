# Sistema Inteligente de Gestion de Leads

<div align="center">

**Integracion de Orquestacion Low-Code, IA Generativa y Desarrollo Web Seguro con Python**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![n8n](https://img.shields.io/badge/n8n-1.x-EA4B71?logo=n8n&logoColor=white)](https://n8n.io)
[![OpenAI](https://img.shields.io/badge/GPT--4o--mini-412991?logo=openai&logoColor=white)](https://platform.openai.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/Licencia-MIT-green)](LICENSE)
[![Costo](https://img.shields.io/badge/Costo-~US$0.0004/lead-informational)]()
[![Seguridad](https://img.shields.io/badge/Seguridad-OWASP%20%2B%20RLS-blue)]()

</div>

---

## Que problema resuelve?

Las PyMEs pierden entre el 35% y 50% de sus oportunidades de venta por no responder
a tiempo a los clientes potenciales. Segun Oldroyd (2007, MIT/InsideSales.com),
responder dentro de los primeros 5 minutos multiplica por 21 las probabilidades
de calificar al lead respecto de hacerlo a los 30 minutos.

Este sistema automatiza el ciclo de vida del lead: **captura -> clasificacion con IA
-> respuesta personalizada -> persistencia -> notificacion**. El tiempo de respuesta
HTTP de Flask es de ~3,2 segundos; el pipeline completo de n8n se completa en ~4,2 s.

---

## Arquitectura

```
   Usuario              Flask               n8n + IA               PostgreSQL          Streamlit
      |                   |                    |                       |                   |
      |  Completa form    |                    |                       |                   |
      |------------------>|                    |                       |                   |
      |                   |  POST /api/leads   |                       |                   |
      |                   |------------------->|                       |                   |
      |                   |                    |  Normaliza + Valida   |                   |
      |                   |                    |------.                |                   |
      |                   |                    |      | (ETL)          |                   |
      |                   |                    |<-----'                |                   |
      |                   |                    |                       |                   |
      |                   |                    |---> GPT-4o-mini ---->|                   |
      |                   |                    |     "Clasifica"       |                   |
      |                   |                    |<---- clasificacion ---|                   |
      |                   |                    |                       |                   |
      |                   |                    |---> GPT-4o-mini ---->|                   |
      |                   |                    |     "Genera email"    |                   |
      |                   |                    |<--- email HTML -------|                   |
      |                   |                    |                       |                   |
      |                   |                    |  INSERT (REST API)    |                   |
      |                   |                    |---------------------->|                   |
      |                   |                    |                       |  SELECT * FROM    |
      |                   |                    |                       |<------------------|
      |                   |                    |                       |--- leads -------->|
      |                   |   HTTP 200 +      |                       |                   |
      |<------------------|  Gmail + Slack     |                       |                   |
      |   email IA        |<-------------------|                       |                   |
```

---

## Stack Tecnologico

| Componente | Tecnologia | Rol | Costo |
|---|---|---|---|
| Landing Page | Flask 3.x + CSS puro | Formulario seguro + SEO | $0 |
| Orquestador | n8n 1.x (Docker) | Pipeline de automatizacion | $0 |
| IA | GPT-4o-mini (OpenAI) | Clasificacion + email personalizado | ~US$0.0004/lead |
| Base de Datos | Supabase PostgreSQL | Persistencia + Row Level Security | $0 (plan gratuito) |
| Dashboard | Streamlit | KPIs + filtros + detalle de leads | $0 |
| Email | Gmail API | Envio automatico | $0 |
| Notificaciones | Slack API | Alertas al equipo | $0 |
| **TOTAL** | | **Costo marginal** | **~US$0.0004/lead** |

> **Nota sobre el costo:** El stack de infraestructura opera sin costo en sus planes
> gratuitos. El unico componente con costo es la API de OpenAI, con un costo marginal
> de ~US$0.0004 por lead procesado (~US$0.04 para las 100 pruebas de validacion).

---

## Seguridad por Diseno

13 medidas en 3 capas, siguiendo OWASP Top 10 (2021):

| Capa | Medidas |
|---|---|
| **Aplicacion** | Content-Security-Policy, HSTS, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy, CORS, Rate Limiting (60 req/min), CSRF Token, Input Sanitization, Honeypot anti-spam |
| **Datos** | Row Level Security (3 roles, 11 politicas), SHA-256 de PII como campo auxiliar de busqueda, IP anonimizada (mascara /16), API Keys con expiracion |
| **Integracion** | Credential Store AES-256, variables de entorno (sin texto plano), HTTPS/TLS en transito |

---

## Resultados

100 casos de prueba controlados distribuidos en 12 categorias (CP-01 a CP-12):

| Metrica | Valor | Universo |
|---|---|---|
| LRT Flask promedio (fast ack HTTP) | 3,2 s | 90 casos validos |
| LRT Pipeline promedio (n8n completo) | 4,2 s | 90 casos validos |
| Casos con LRT Flask < 8s | 100% (90/90) | 90 casos validos |
| Tasa de persistencia exitosa | 100% | 90 casos validos |
| Exactitud de clasificacion IA (global) | 87,7% (57/65) | 65 casos con clase definida |
| Exactitud - compra_inmediata | 85,0% (17/20) | n = 20 |
| Exactitud - solicita_info | 88,0% (22/25) | n = 25 |
| Exactitud - soporte | 80,0% (8/10) | n = 10 |
| Recall - spam | 100% (10/10) | n = 10 |
| Eventos perdidos sin registro de error | 0 | 100 casos + 4 fallos |

> **Nota metodologica:** LRT Flask (~3,2 s) mide el tiempo de respuesta HTTP del
> servidor (fast acknowledgement). LRT Pipeline (~4,2 s) mide el tiempo total del
> workflow n8n. Son dos metricas diferentes que corresponden a dos momentos distintos
> del procesamiento. La diferencia (~1 s) corresponde al procesamiento asincronico
> del pipeline despues de que Flask envia la respuesta HTTP 200.

---

## Estructura del Proyecto

```
Sistema-Inteligente-de-Gestion-de-Leads/
|-- landing_page/            # Flask + HTML + CSS
|   |-- app.py               # Servidor: rutas, seguridad, validacion
|   |-- templates/
|   |   |-- index.html       # Landing page con SEO + OG + JSON-LD
|   |   |-- gracias.html     # Pagina post-envio con timeline
|   |-- static/
|   |   |-- style.css        # Design system completo
|   |-- requirements.txt
|-- n8n_workflow/
|   |-- pipeline_leads_ia.json  # Workflow n8n con 14 nodos (importable)
|-- database/
|   |-- schema.sql           # PostgreSQL + RLS + roles + triggers + indices
|-- dashboard/
|   |-- dashboard.py         # Streamlit con KPIs y filtros
|   |-- requirements.txt
|-- tests/
|   |-- test_50_leads.py         # Suite original de 50 casos
|   |-- test_50_leads_v2.py      # Suite v2 con metricas corregidas
|   |-- test_100_leads.py        # Suite 100 casos CP-01 a CP-12
|   |-- test_failure_injection.py # Pruebas de inyeccion de fallos (OE7)
|   |-- analyze_results.py       # Analisis post-ejecucion + matriz de confusion
|   |-- generate_100_results.py  # Generador de resultados simulados
|   |-- resultados_v3/           # Resultados de los 100 casos
|-- docs/
|   |-- LEVANTAR_PROYECTO.md     # Instrucciones paso a paso
|   |-- evidencia_anexos/        # Contenido de Anexos G, H, I, J
|   |-- diagrams/                # Diagramas de arquitectura
|   |   |-- figura1_arquitectura_componentes.mmd
|   |   |-- figura2_secuencia_flujo_respuesta.mmd
|   |   |-- figura3_entidad_relacion.mmd
|   |   |-- render_diagrams.py   # Script para renderizar a PNG
|   |   |-- output/              # Diagramas renderizados (PNG)
|-- TFI - Sistema Inteligente de Gestion de Leads.docx  # Documento academico
|-- TFI_NotebookLM.md        # Fuente para NotebookLM (video + slides)
|-- plan_proyecto.docx       # Planificacion del proyecto
|-- README.md
```

---

## Levantar el proyecto

### Requisitos
- Python 3.10+
- Docker Desktop
- Cuentas gratuitas: [Supabase](https://supabase.com), [OpenAI](https://platform.openai.com), [Slack](https://api.slack.com)

### 1. Base de Datos

```bash
# Crear proyecto en supabase.com -> copiar Project ID + Anon Key
# SQL Editor -> pegar y ejecutar database/schema.sql
```

### 2. n8n + IA

```bash
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
# Abrir http://localhost:5678 -> crear cuenta
# Importar n8n_workflow/pipeline_leads_ia.json
# Configurar credenciales: OpenAI, Gmail, Slack
```

### 3. Landing Page

```bash
cd landing_page
python -m venv venv && source venv/bin/activate  # Linux/Mac
python -m venv venv && .\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
python app.py  # -> http://localhost:5000
```

### 4. Dashboard

```bash
cd dashboard
pip install -r requirements.txt
$env:SUPABASE_URL="https://TU_ID.supabase.co"
$env:SUPABASE_ANON_KEY="tu-key"
streamlit run dashboard.py  # -> http://localhost:8501
```

### 5. Pruebas

```bash
cd tests
pip install requests
python test_100_leads.py        # Suite 100 casos (requiere Flask + n8n)
python test_failure_injection.py # Pruebas de fallo para OE7
python generate_100_results.py   # Resultados simulados si n8n no esta corriendo
python analyze_results.py        # Matriz de confusion (post-pipeline)
```

---

## Sobre este proyecto

Trabajo Final Integrador de la **Tecnicatura Superior en Programacion** -
Universidad Tecnologica Nacional, Facultad Regional Mendoza.

**Autores:** Fabricio Fracapani & Martin Lepez - 2026

**Repositorio:** https://github.com/FabricioFracapani/Sistema-Inteligente-de-Gestion-de-Leads

**Lo que construimos:** 4 componentes de software funcionales (Flask, n8n workflow,
schema SQL, dashboard Streamlit) que integran desarrollo web, automatizacion low-code,
inteligencia artificial generativa, bases de datos con seguridad a nivel de fila, y
visualizacion de datos - con un stack de costo marginal insignificante (~US$0.0004/lead).
