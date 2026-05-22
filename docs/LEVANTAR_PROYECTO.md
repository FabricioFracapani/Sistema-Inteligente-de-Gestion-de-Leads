# Sistema Inteligente de Gestion de Leads
## Instrucciones para levantar el proyecto

> TFI — Tecnicatura Superior en Programacion — UTN FRM
> Autores: Fracapani, Fabricio — Lepez, Martin

---

## Requisitos previos

- Python 3.10+
- Docker Desktop
- Cuenta gratuita en [supabase.com](https://supabase.com)
- Cuenta gratuita en [platform.openai.com](https://platform.openai.com) (cargar $5 de credito)
- Cuenta gratuita en [api.slack.com](https://api.slack.com) (opcional para notificaciones)
- Proyecto en Google Cloud Console con Gmail API habilitada (para envio de emails)

---

## 1. Base de Datos — Supabase (PostgreSQL)

```bash
# 1. Crear cuenta en https://supabase.com
# 2. New Project > completar datos > Create Project
# 3. Esperar 2 minutos a que la DB esté lista
# 4. Copiar Project URL y Anon Key (Settings > API)

# 5. Ir a SQL Editor y ejecutar TODO el contenido de:
#    proyecto_nuevo/database/schema.sql

# 6. Verificar en Table Editor que existan las 4 tablas:
#    leads, lead_events, ia_config, api_keys

# 7. Verificar RLS (Authentication > Policies):
#    Las 4 tablas deben mostrar "RLS enabled"
```

**Credenciales para despues:**
- `SUPABASE_PROJECT_ID` = el ID de tu proyecto (ej: `abcdefghijklm`)
- `SUPABASE_ANON_KEY` = la key publica (ej: `eyJhbGciOi...`)

---

## 2. n8n — Orquestador Low-Code

```bash
# Descargar e iniciar n8n via Docker
docker run -d --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  n8nio/n8n

# Abrir http://localhost:5678
# Crear cuenta (email + password, es solo local)
```

### 2.1 Configurar variables de entorno en n8n

Settings > Environment Variables > Add:
```
SUPABASE_PROJECT_ID = tu-project-id
SUPABASE_ANON_KEY    = tu-anon-key
```

### 2.2 Configurar credenciales en n8n

```
Credentials > Add:
  - OpenAI: API Key de platform.openai.com
  - Google OAuth2: para Gmail (necesita proyecto en Google Cloud Console)
  - Slack API: Bot Token o Incoming Webhook URL
```

### 2.3 Importar el workflow

```
Workflows > Add Workflow > Import from File
Seleccionar: proyecto_nuevo/n8n_workflow/pipeline_leads_ia.json
Activar el workflow (toggle Active ON)
```

---

## 3. Landing Page — Flask

```bash
cd proyecto_nuevo/landing_page

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activar (Mac/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python app.py

# Abrir http://localhost:5000
```

### 3.1 Variables de entorno opcionales

```bash
# Windows PowerShell
$env:FLASK_SECRET_KEY = "clave-secreta-de-32-caracteres"
$env:N8N_WEBHOOK_URL = "http://localhost:5678/webhook/leads"
$env:CORS_ORIGINS = "http://localhost:5000,http://localhost:8501"

# Mac/Linux
export FLASK_SECRET_KEY="clave-secreta-de-32-caracteres"
export N8N_WEBHOOK_URL="http://localhost:5678/webhook/leads"
export CORS_ORIGINS="http://localhost:5000,http://localhost:8501"
```

---

## 4. Dashboard — Streamlit

```bash
cd proyecto_nuevo/dashboard

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
# Windows PowerShell
$env:SUPABASE_URL = "https://TU_PROJECT_ID.supabase.co"
$env:SUPABASE_ANON_KEY = "tu-anon-key"

# Mac/Linux
export SUPABASE_URL="https://TU_PROJECT_ID.supabase.co"
export SUPABASE_ANON_KEY="tu-anon-key"

# Iniciar dashboard
streamlit run dashboard.py

# Abrir http://localhost:8501
```

---

## 5. Pruebas Automatizadas

```bash
cd proyecto_nuevo/tests

# Requiere: requests (incluida en requirements de Flask)
pip install requests

# Asegurate de que Flask esté corriendo (paso 3)
# y que n8n esté corriendo (paso 2)

# Ejecutar las 50 pruebas
python test_50_leads.py
```

**Salida esperada:**
- Barra de progreso con 50 casos
- Resumen con tasa de ingesta y LRT promedio
- Archivos `resultados_pruebas.csv` y `resultados_pruebas.json` generados

---

## 6. Verificar que todo funciona

### 6.1 Probar 1 lead end-to-end

1. Abrir `http://localhost:5000` (Flask)
2. Completar formulario con datos reales (usar tu email)
3. Click en "Solicitar Informacion"
4. Verificar en **n8n > Executions** que se ejecuto sin errores
5. Verificar en **Supabase > Table Editor > leads** que aparece el registro
6. Verificar en tu **bandeja de Gmail** que llego el email generado por IA
7. Verificar en **Slack** que llego la notificacion (si configuraste)

### 6.2 Health Checks

```
http://localhost:5000/health          → {"status": "ok", "security_headers": true}
http://localhost:5000/robots.txt      → User-agent: * \n Allow: /
http://localhost:5000/sitemap.xml     → XML con URLs del sitio
http://localhost:5678/healthz         → n8n health check
http://localhost:8501                 → Dashboard Streamlit (si esta corriendo)
```

---

## 7. Despliegue en Produccion (Render.com — Gratuito)

### Landing Page (Flask)
```
1. Subir landing_page/ a GitHub
2. Render.com > New Web Service > Conectar repo
3. Build Command: pip install -r requirements.txt
4. Start Command: gunicorn app:app
5. Environment Variables: FLASK_SECRET_KEY, N8N_WEBHOOK_URL, CORS_ORIGINS
```

### Dashboard (Streamlit)
```
1. Subir dashboard/ a GitHub
2. Render.com > New Web Service > Conectar repo
3. Build Command: pip install -r requirements.txt
4. Start Command: streamlit run dashboard.py --server.port $PORT
5. Environment Variables: SUPABASE_URL, SUPABASE_ANON_KEY
```

---

## 8. Estructura completa del proyecto

```
proyecto_nuevo/
├── plan_proyecto.docx           # Documento de planificacion (42 KB)
├── docs/
│   └── LEVANTAR_PROYECTO.md     # Este archivo
├── database/
│   └── schema.sql               # Schema PostgreSQL con RLS, roles, triggers
├── landing_page/
│   ├── app.py                   # Flask + seguridad + SEO
│   ├── requirements.txt         # Flask, requests, flask-cors, gunicorn
│   ├── templates/
│   │   ├── index.html           # Landing page con SEO + OG + JSON-LD
│   │   └── gracias.html         # Pagina post-envio
│   └── static/
│       └── style.css            # Estilos responsive
├── n8n_workflow/
│   └── pipeline_leads_ia.json   # Workflow n8n con IA (importable)
├── dashboard/
│   ├── dashboard.py             # Streamlit dashboard con KPIs
│   └── requirements.txt         # streamlit, supabase
└── tests/
    ├── test_50_leads.py         # 50 casos de prueba automatizados
    ├── resultados_pruebas.csv   # Generado al ejecutar tests
    └── resultados_pruebas.json  # Generado al ejecutar tests
```

---

## 9. Stack tecnologico resumen

| Componente   | Tecnologia      | Puerto | Costo    |
|-------------|-----------------|--------|----------|
| Landing     | Flask + Bootstrap| 5000  | $0       |
| Orquestador | n8n (Docker)    | 5678   | $0       |
| IA          | GPT-4o-mini     | API    | ~$0.0001/lead |
| Base datos  | Supabase PG     | Cloud  | $0       |
| Dashboard   | Streamlit       | 8501   | $0       |
| Email       | Gmail API       | API    | $0       |
| Notif.      | Slack API       | API    | $0       |

**Costo total estimado para 50 leads de prueba: $0.005**

---

## 10. Solucion de problemas comunes

| Problema | Causa probable | Solucion |
|----------|---------------|----------|
| Flask no inicia | Puerto 5000 en uso | `$env:PORT=5001` y probar de nuevo |
| n8n no recibe webhook | Docker no esta corriendo | `docker start n8n` |
| n8n error "Supabase not found" | Variables de entorno no configuradas | Revisar paso 2.1 |
| OpenAI error 429 | Sin credito en la cuenta | Cargar $5 en platform.openai.com |
| Dashboard no muestra datos | SUPABASE_URL/KEY incorrectas | Revisar variables en paso 4 |
| Test script error CSRF | Flask no esta corriendo | Iniciar Flask primero |
| Gmail no envia | OAuth no configurado | Configurar Google Cloud Console + consent screen |
