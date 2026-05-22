# Sistema Inteligente de Gestion de Leads

## Integracion de Orquestacion Low-Code, IA Generativa y Desarrollo Web Seguro con Python

> **TFI - Tecnicatura Superior en Programacion - UTN FRM - 2026**
> **Autores:** Fracapani, Fabricio - Lepez, Martin
> **Norma:** APA 7a edicion | **Costo total del stack:** $0

---

## 1. Problema

Las PyMEs pierden entre el 35% y 50% de sus oportunidades de venta por no responder a tiempo a los leads que llegan por formularios web. Un estudio de Harvard Business Review (2011) muestra que responder en menos de 5 minutos genera 6 a 10 veces mas probabilidades de conversion que hacerlo 30 minutos despues. Sin embargo, la mayoria opera con procesos manuales: un vendedor revisa el correo, copia datos a una planilla y eventualmente responde. El resultado son demoras de 4 a 8 horas, errores de carga, perdida de trazabilidad y fuga de leads hacia la competencia.

**Pregunta de investigacion:** Es tecnicamente viable construir un sistema automatizado de gestion de leads que integre captura web, IA generativa, persistencia profesional y dashboard, usando exclusivamente herramientas gratuitas y con estandares de seguridad y SEO?

---

## 2. Solucion - Arquitectura

Sistema compuesto por **4 modulos** construidos por los autores:

### 2.1 Landing Page (Flask + Bootstrap 5.3)
- Formulario de captura con validacion en 2 capas (JavaScript frontend + Python backend)
- 13 medidas de seguridad: CSP, HSTS, X-Frame-Options DENY, CSRF, Rate Limiting, Input Sanitization, Honeypot anti-spam, Logging sin PII
- 14 elementos SEO: Open Graph, Twitter Cards, JSON-LD (ProfessionalService), Sitemap XML, robots.txt, Canonical URL, Semantic HTML, aria-*
- POST a n8n via webhook con fast acknowledgment

### 2.2 Pipeline de Procesamiento (n8n + GPT-4o-mini)
- 14 nodos en 5 capas: Ingesta -> ETL -> IA Scoring -> IA Email -> Accion
- **IA Scoring:** GPT-4o-mini clasifica la intencion del lead en 4 categorias (compra_inmediata, solicita_info, soporte, spam) y asigna prioridad 1-100
- **IA Email Generator:** GPT-4o-mini genera un email HTML personalizado segun la intencion detectada
- Error Trigger con principio fail-loudly (alerta a Slack #alertas-sistema)

### 2.3 Base de Datos (Supabase PostgreSQL + Row Level Security)
- 4 tablas con RLS: leads, lead_events (append-only), ia_config, api_keys
- 3 roles: anon (solo INSERT), authenticated (SELECT/UPDATE), service_role (bypass total)
- 11 politicas de seguridad granulares
- Hashing SHA-256 automatico de email y telefono, anonimizacion de IP
- API Keys con expiracion y permisos granulares

### 2.4 Dashboard de Ventas (Streamlit)
- 5 KPIs: total leads, compra inmediata, solicita info, spam, prioridad promedio
- Filtros: fecha, clasificacion IA, estado, prioridad, fuente
- Vista detallada con mensaje original + resumen IA + email generado
- Conexion a Supabase con cache de 30 segundos

---

## 3. Que Construimos

| Componente | Tecnologia | Archivos | Evidencia de Programacion |
|---|---|---|---|
| Landing Page | Flask 3.x + Bootstrap 5.3 | app.py (457 lineas), index.html, gracias.html, style.css | Desarrollo web full-stack, seguridad OWASP, SEO |
| Pipeline IA | n8n + GPT-4o-mini | pipeline_leads_ia.json (14 nodos) | Automatizacion low-code, integracion APIs, IA prompts |
| Base de Datos | PostgreSQL (Supabase) | schema.sql (15 KB, DDL + RLS + triggers) | Diseno de bases de datos, seguridad de datos, PL/pgSQL |
| Dashboard | Streamlit | dashboard.py (11 KB) | Visualizacion de datos, Python, APIs REST |
| Tests | Python requests | test_50_leads.py (50 casos CP-01 a CP-10) | Testing automatizado, metricas |

---

## 4. Innovacion - Que Diferencia Este TFI

### 4.1 IA Integrada (no solo "trabajo futuro")
- GPT-4o-mini operativo en el pipeline: clasifica intencion y genera emails personalizados
- Modelo mas economico de OpenAI (~$0.0001 por lead)
- Prompts configurables desde base de datos sin tocar n8n

### 4.2 Seguridad por Diseno (13 medidas, 3 capas)
- **Capa App:** CSP, HSTS, X-Frame-Options, CORS, CSRF, Rate Limiting, Input Sanitization, Honeypot
- **Capa Datos:** Row Level Security (3 roles), SHA-256 PII, IP anonimizacion, API Keys
- **Capa Integracion:** Variables de entorno (no texto plano), Credential Store AES-256

### 4.3 SEO Completo (14 elementos)
- Open Graph + Twitter Cards para redes sociales
- JSON-LD Structured Data para Google rich snippets
- Sitemap XML + robots.txt + canonical URL
- Semantic HTML (header, main, article, footer) + aria-* attributes

### 4.4 Stack 100% Gratuito
- Costo total: $0 (OpenAI ~$0.005 para las 50 pruebas)
- Sin dependencia de servicios pagos ni infraestructura costosa
- Replicable por cualquier PyME o estudiante

---

## 5. Resultados (50 Pruebas Controladas)

### 5.1 Lead Response Time
- **Promedio:** 3.2 segundos
- **96% bajo umbral** de 5 segundos
- Contraste con proceso manual: 4-8 horas

### 5.2 Precision de IA
- **Clasificacion estricta:** 84.4% (38/45 casos validos)
- **Clasificacion flexible:** 95.6% (43/45)
- **Recall de spam:** 100% (5/5 detectados)

### 5.3 Tasa de Ingreso
- **Persistencia exitosa:** 95.6%
- **Cero eventos perdidos** sin registro de error

### 5.4 Comparativa Manual vs Automatizado

| Indicador | Manual | Automatizado |
|---|---|---|
| LRT promedio | 4-8 horas | 3.2 segundos |
| LRT fuera de horario | 12-24 horas | 3.2s (24/7) |
| Registros completos | ~70% | 100% |
| Clasificacion de intencion | No existe | 84% precision IA |
| Perdida silenciosa de datos | Frecuente | 0 |
| Notificacion al equipo | Ad-hoc | < 5 segundos |
| Costo operativo | Horas/persona | $0 |

### 5.5 Verificacion de Hipotesis
La hipotesis alternativa (HA) no fue refutada. Las 4 condiciones de refutacion no se cumplieron en las 50 pruebas.

---

## 6. Limitaciones (Honestidad Academica)

| # | Limitacion | Impacto | Abordaje |
|---|---|---|---|
| L1 | Solo 50 eventos controlados | Sin validez externa | Protocolo extendido disenado |
| L2 | Sin usuarios reales | No mide conversion | Piloto real como trabajo futuro |
| L3 | Dependencia de APIs externas | Robustez condicionada | Error Trigger + diseno de reintentos |
| L4 | Sin test de carga | Escalabilidad no verificada | Disenado en protocolo 5.5 |
| L5 | IA evaluada manualmente | Subjetividad en parciales | Criterios explicitos documentados |

---

## 7. Trabajos Futuros

| Prioridad | Linea | Resultado Esperado |
|---|---|---|
| 1 | Piloto con 10-15 leads reales | Feedback cualitativo + metricas reales |
| 2 | Test de carga (500 eventos) | Curvas LRT vs volumen |
| 3 | Reintentos con backoff | Mayor resiliencia ante fallos |
| 4 | Integracion CRM (HubSpot/Pipedrive) | Pipeline conectado a CRM empresarial |
| 5 | Dashboard multi-tenant | Aislamiento de datos por PyME |
| 6 | Benchmark multi-modelo IA | Comparativa GPT-4o-mini vs Claude vs Gemini |
| 7 | Chatbot WhatsApp + n8n | Leads via mensajeria instantanea |

---

## 8. Stack Tecnologico Completo

| Componente | Tecnologia | Puerto | Costo |
|---|---|---|---|
| Landing Page | Flask 3.x + Bootstrap 5.3 | 5000 | $0 |
| Orquestador | n8n 1.x (Docker) | 5678 | $0 |
| IA | GPT-4o-mini (OpenAI) | API | ~$0.0001/lead |
| Base de Datos | Supabase PostgreSQL | Cloud | $0 |
| Dashboard | Streamlit | 8501 | $0 |
| Email | Gmail API | API | $0 |
| Notificaciones | Slack API | API | $0 |

---

## 9. Preguntas Probables de Defensa

**P: Por que solo 50 eventos?**
R: El diseno experimental priorizo diversidad de casos (10 tipos) sobre volumen. Se documentaron metricas para cada tipo. El protocolo de validacion extendida con 500 eventos esta disenado como trabajo futuro inmediato.

**P: Esto escala a produccion?**
R: La arquitectura por componentes y PostgreSQL con RLS estan disenados para escalar. Pero no tenemos evidencia empirica de escalabilidad. Las pruebas de carga son el siguiente paso. Somos honestos sobre esta limitacion.

**P: Que tan confiable es la IA para decisiones comerciales?**
R: 84.4% de precision estricta y 100% de recall de spam. Es adecuada como sistema de apoyo a la decision, no para decisiones automaticas sin supervision humana. El equipo de ventas siempre tiene la ultima palabra.

**P: Por que Supabase y no Google Sheets?**
R: PostgreSQL ofrece: integridad referencial, Row Level Security granular por rol, API REST autogenerada, ACID compliance, y es el estandar profesional. Google Sheets no tiene ninguna de estas capacidades de seguridad.

**P: Como protegieron los datos personales? (Ley 25.326)**
R: Implementamos 13 medidas en 3 capas. A nivel de datos: RLS con roles, SHA-256 de PII (nunca almacenamos emails en texto plano para busquedas), anonimizacion de IP. A nivel de aplicacion: 13 headers de seguridad OWASP. Cumplimos los principios de finalidad, calidad y confidencialidad de la Ley 25.326.

**P: Cual es el aporte real de este TFI?**
R: Tres aportes: (1) arquitectura documentada y replicable de automatizacion low-code con IA para PyMEs, (2) demostracion de que un stack 100% gratuito puede lograr niveles profesionales de seguridad y SEO, (3) cuatro componentes de software funcionales que evidencian competencias de programacion en desarrollo web, automatizacion, IA, bases de datos y visualizacion.

---

## 10. Glosario

- **Lead:** Cliente potencial que proporciona sus datos de contacto voluntariamente
- **MQL (Marketing Qualified Lead):** Lead que interactuo con contenidos de marketing
- **SQL (Sales Qualified Lead):** Lead con intencion de compra explicita
- **LRT (Lead Response Time):** Tiempo entre la captura y la primera respuesta
- **ETL (Extract, Transform, Load):** Proceso de extraccion, transformacion y carga de datos
- **RLS (Row Level Security):** Seguridad a nivel de fila en bases de datos
- **CSP (Content-Security-Policy):** Header HTTP que controla que recursos puede cargar el navegador
- **HSTS (HTTP Strict Transport Security):** Fuerza conexiones HTTPS
- **CSRF (Cross-Site Request Forgery):** Ataque que fuerza a un usuario a ejecutar acciones no deseadas
- **fail-loudly:** Principio de diseno donde los errores son visibles y notificados inmediatamente
- **Low-Code:** Paradigma de desarrollo que minimiza codigo escrito mediante entornos visuales
- **PII (Personally Identifiable Information):** Datos que pueden identificar a una persona

---

## 11. Para el Video de Defensa

### Estructura sugerida para un video de 10-12 minutos:

1. **(0:00-1:30)** El problema: mostrar datos de HBR/Inside Sales, explicar la fuga de leads en PyMEs
2. **(1:30-3:00)** La solucion: diagrama de los 4 componentes, enfatizar lo que construimos nosotros
3. **(3:00-5:00)** Demo en vivo: formulario Flask -> n8n ejecutandose -> email IA llegando a Gmail -> Slack -> Dashboard
4. **(5:00-7:00)** La IA en accion: mostrar 3 ejemplos (compra inmediata, solicita info, spam) con los prompts y resultados
5. **(7:00-8:30)** Seguridad y SEO: recorrer los 13 headers, RLS en Supabase, JSON-LD en el HTML
6. **(8:30-9:30)** Resultados: tabla comparativa manual vs automatizado, verificacion de hipotesis
7. **(9:30-10:30)** Limitaciones y trabajo futuro (honestidad academica)
8. **(10:30-12:00)** Conclusion y cierre: lo demostrado, lo sugerido, lo abierto

### Slides sugeridas (12-15 slides):

1. Portada (titulo, autores, institucion)
2. El problema (datos HBR + Inside Sales)
3. Arquitectura del sistema (diagrama de 4 componentes)
4. Landing Page (captura del formulario + headers de seguridad)
5. Pipeline n8n (captura del workflow con 14 nodos)
6. IA en accion (3 ejemplos de clasificacion con prompts)
7. Base de Datos (schema SQL + politicas RLS)
8. Dashboard (captura con KPIs y filtros)
9. Seguridad implementada (tabla de 13 medidas)
10. SEO implementado (tabla de 14 elementos)
11. Resultados (tabla comparativa manual vs automatizado)
12. Verificacion de hipotesis (4 condiciones no refutadas)
13. Limitaciones (tabla de 5 limitaciones con abordaje)
14. Trabajos futuros (7 lineas priorizadas)
15. Conclusiones y preguntas

---

*Documento generado para NotebookLM. Usar como fuente para generar: guion de video de defensa, slides de presentacion, FAQ de preguntas frecuentes, y glosario de estudio.*
