# Respuesta a la Devolución Académica v7 — trabajo hecho en esta sesión

Basado en `tests/resultados_v3/Devolucion_TFI_Gestion_de_Leads_v7.pdf` (devolución del 19/08/2026).
Este documento cubre **únicamente los ítems que se trabajaron en esta sesión** (22/08/2026), en el
mismo orden en que se pidieron. No es un resumen de toda la devolución — al final hay una lista de
lo que *falta* según el propio documento de auditoría.

Cada sección trae: qué pedía la devolución, qué se hizo, el dato/texto listo para pegar en el informe,
y el archivo de evidencia.

---

## R-03 / M-05 — Repetir la corrida 3 veces (Bloque 3, punto 13)

**Pedía:** repetir la corrida sobre los mismos 65 casos etiquetados y reportar exactitud media ± desvío
entre corridas, más el % de casos con clasificación estable en las 3.

**Se hizo:** 3 corridas reales del pipeline completo (Flask → n8n → GPT-4o-mini → Supabase) sobre los
65 casos con clasificación esperada (CP-01, CP-02, CP-06/07, CP-08).

**Texto sugerido para el informe (§4.6 / §5.4.1):**
> Se ejecutó el pipeline 3 veces sobre los mismos 65 casos etiquetados. Exactitud por corrida: 93,8 %,
> 96,9 % y 98,5 %. Media ± desvío entre corridas: **96,4 % ± 2,4 %**. Clasificación estable en las 3
> corridas: **62/65 casos (95,4 %)**.

**Evidencia:** `tests/test_r03_replicacion.py`, `tests/resultados_v3/r03_replicacion.csv` / `.json` / `_resumen.txt`

---

## C-02 — Figura de dispersión LRT vs. longitud del mensaje (Bloque 2, punto 7)

**Pedía:** incorporar la longitud del mensaje (caracteres) a la Tabla F.1 y una figura de dispersión LRT
vs. longitud (n=91).

**Se hizo:** se calculó la longitud del mensaje **completo** (no la versión truncada a 200 caracteres que
tiene el CSV de resultados) para los 91 casos con HTTP 200, y se cruzó con el LRT de cada uno.

**Texto sugerido para el informe (§5.4.1 / §6.1, siguiendo también C-02 del propio hallazgo crítico):**
> Longitud de mensaje (n=91): media 69,6 caracteres, mediana 57,0, desvío 67,8, mínimo 3, máximo
> 653. Correlación de Pearson entre longitud y LRT: r = 0,147 (débil). El caso *Muy Largo* (653
> caracteres) es el único que supera el umbral de 8 s (11,62 s) — dependencia real del costo de las
> dos llamadas a GPT-4o-mini con la longitud de entrada, no ruido estadístico aislado.

**Evidencia:** `tests/resultados_v3/c02_longitud_mensajes.csv` (dato por caso, listo para el gráfico) y
`.txt` (metodología y estadísticos).

**Nota:** esto resuelve el requisito de *dato* de C-02. La redacción del análisis del outlier en §5.4.1/§6
(puntos 1, 2 y 4 de la corrección exigida de C-02) sigue pendiente de escribir en el documento.

---

## M-02 — Autenticación del dashboard (Bloque 2, punto 9)

**Pedía:** describir cómo Streamlit obtiene su rol contra Supabase; si usa `anon` o `service_role`
embebida, declararlo como limitación L8.

**Se hizo:** verificado en código (`dashboard/dashboard.py:36`) y en vivo con `curl` (CS-05): el dashboard
usa la **anon key**, `SUPABASE_AUTH_EMAIL`/`PASSWORD` están vacíos en `.env`, por lo tanto **nunca
hace login real**. La policy `anon_can_read_leads` (`USING (true)`) da lectura irrestricta de toda la
tabla `leads` a cualquiera con la anon key.

**Texto sugerido para §3.5.1 (nueva) o limitación L8:**
> El dashboard se conecta con la anon key de Supabase (`dashboard/dashboard.py`) y no ejecuta
> autenticación de usuario real. La política RLS `anon_can_read_leads` otorga lectura irrestricta de la
> tabla `leads` a cualquier poseedor de la anon key, sin login. RLS está activo a nivel de motor pero no
> ejerce control de acceso real para lectura. **Limitación L8.** Abordaje: migrar el dashboard a un login
> real (Supabase Auth) y eliminar `anon_can_read_leads`.

**Evidencia:** `tests/resultados_v3/m02_auth_dashboard_l8.txt`, confirmado en vivo con
`tests/resultados_v3/cs_seguridad/CS-05_rls_select_leads_anon.txt` (devuelve filas reales con PII en
texto plano).

---

## C-05 / M-07 — Alucinación del Anexo H y prompt contradictorio (Bloque 1, punto 4)

**Pedía:** señalar la alucinación (documento adjunto inexistente), eliminar el "link genérico de
calendario" o reemplazarlo por variable, y agregar la restricción de no afirmar adjuntos/enlaces
inexistentes.

**Se hizo:** corregido en el prompt real (`n8n_workflow/Pipeline de Leads con IA.json`, nodo IA Generar
Email): eliminada toda instrucción de incluir un link de calendario; agregada la regla explícita de no
afirmar adjuntos/enlaces/documentos no provistos, con instrucción de usar texto plano para invitar a
agendar. Sincronizado y probado en vivo (ver RF-06/RF-07 más abajo).

**Texto sugerido para el Anexo H:**
> *Obsérvese que la versión inicial de este correo mencionaba un documento adjunto inexistente. Este
> caso constituye evidencia empírica directa de la limitación L7 (riesgo de alucinación). Corrección
> aplicada: el prompt de sistema ahora prohíbe explícitamente afirmar la existencia de adjuntos,
> enlaces o documentos no provistos, y elimina la instrucción original de incluir un "link genérico de
> calendario" que generaba URLs inventadas.*

**Evidencia:** `tests/resultados_v3/c05_m07_sync_n8n.txt` (texto exacto del fix + instrucciones de
sincronización), commits `15db5d0` / `3e4c0df`.

---

## m-07 — Normalizar el JSON del prompt + `response_format: json_schema` (Bloque 2/3)

**Pedía:** normalizar a ASCII sin acentos (`clasificacion`, no `clasificación`, comillas rectas) y usar
`response_format: json_schema`.

**Se hizo:** verificado que las claves del JSON de salida ya eran ASCII/comillas rectas. El nodo nativo
`n8n-nodes-base.openAi` (deprecado) no soporta `response_format` — se reemplazaron los 2 nodos IA
por HTTP Request llamando directo a la API de OpenAI con `response_format: {type: "json_schema",
strict: true}`. Validado en ejecución real (ver M-19/M-20): el `content` de la respuesta sale JSON
válido, sin markdown, sin necesidad de parseo defensivo.

**Evidencia:** `n8n_workflow/Pipeline de Leads con IA.json`, `tests/resultados_v3/c05_m07_sync_n8n.txt`.

---

## M-15 / m-06 (CF-04) — Fallback centinela + prioridad 0 para spam (Bloque 3, y m-06)

**Pedía:** valor centinela `sin_clasificar` con `confianza = NULL` y flag `ia_fallback = true`; forzar
`prioridad = 0` para spam.

**Se hizo:** implementado (no solo documentado) en el nodo "Parsear: Extraer Clasificación IA". De
paso se corrigió un bug relacionado: `||` en vez de `??` pisaba un `prioridad: 0` legítimo de la IA con 50.
Se agregó la columna `ia_fallback` a `database/schema.sql` y se corrigió la constraint
`CHECK (ia_prioridad BETWEEN 1 AND 100)` a `BETWEEN 0 AND 100` (bloqueaba guardar 0). Migración
aplicada en Supabase por el usuario y verificada en vivo (lead de prueba con `ia_fallback: false`
persistido correctamente).

**Texto sugerido para §5.4.3 / correcciones pendientes:**
> Corregido: ante fallo de parseo de la IA, el pipeline asigna `clasificacion = 'sin_clasificar'`,
> `prioridad = NULL`, `confianza = NULL` y `ia_fallback = true`, en vez de fabricar una clasificación
> indistinguible de un acierto real. Adicionalmente, se fuerza `prioridad = 0` para todo lead clasificado
> como spam, sin excepción.

**Evidencia:** `tests/resultados_v3/cf04_fallback_m15_m06.txt`,
`database/migrations/2026-08-22_ia_fallback_cf04.sql` (ya aplicada).

---

## M-13 — Anexos A-E, hash de commit (Bloque 3, punto 14)

**Pedía:** incluir el código real (no descripciones) o, como mínimo, el hash de commit exacto de la
versión validada.

**Se hizo:** se encontró que los generadores de Anexos A-E crasheaban (extraían de una estructura de
nodo que ya no existe) y que `docs/evidencia_anexos/` estaba **enteramente excluido de git**
(`.gitignore`), incluidos los propios generadores — es decir, nada de esto era reproducible desde el
repo. Se corrigió el `.gitignore` (solo se excluyen ya `.docx`/imágenes), se reescribieron los 3
generadores para extraer por marcador de texto (no por línea fija, que quedaba desalineado con cada
edición) y se les agregó referencia automática al commit de HEAD.

**Commit de la versión validada: `15db5d0`** (todas las correcciones de esta sesión).
Commit `3e4c0df` (posterior, solo agrega la cita al hash de `15db5d0` en los anexos — un commit no
puede citar su propio hash).

**Texto sugerido para el informe:**
> Los fragmentos de código de los Anexos A-E corresponden al commit `15db5d0` de la rama
> `Master-Demo`:
> `https://github.com/Martinlepez031/Sistema-Inteligente-de-Gestion-de-Leads/tree/15db5d0`

**Hallazgo adicional:** los Anexos A-E figuran en el índice del `.docx` pero el contenido nunca se pegó
en el cuerpo del documento (solo existe como archivo suelto). Pendiente de que el usuario lo pegue.

**Evidencia:** `docs/evidencia_anexos/Anexos_A_E_Fragmentos_Reales.txt` (con la nota de versión ya
en el encabezado), `docs/evidencia_anexos/generar_anexo*.py`.

---

## M-14 — Anexos G e I fechados antes de la corrida (Bloque 3, punto 14)

**Pedía:** regenerar los Anexos G e I con fecha posterior a la corrida del 18/08, y corregir "v6/6.0.0" a v7.

**Se hizo:** ambos estaban fechados 2026-08-05 (13 días antes del 18/08). Se renombró el workflow de
"v3" a "v7" (coincide con el documento), se reescribió `generar_anexo_G.py` para armar el encabezado
desde el JSON real y estampar la fecha real de generación, y se creó `generar_anexo_I.py` (no existía —
Anexo I era texto a mano y estaba desactualizado, le faltaba la fuente `test_100_v3`). Se corrigió
también el reemplazo real dentro del `.docx` (con backup previo).

**Evidencia:** `tests/resultados_v3/m14_anexos_g_i_regenerados.txt`,
`docs/evidencia_anexos/Anexo_G_Pipeline_n8n.txt`, `Anexo_I_Dashboard_Streamlit.txt` (ambos con
"Documento generado" y hash de commit en el pie).

---

## M-07 — Pruebas negativas de seguridad CS-01 a CS-06 (Bloque 2, punto 11)

**Pedía:** el bloque de 6 pruebas negativas (CSRF, rate limiting, honeypot, sanitización, RLS SELECT en
`leads`, RLS DELETE en `lead_events`) más consultar el campo `mensaje` del caso Html Injection.

**Se hizo:** las 6 pruebas con `curl` puro contra Flask y Supabase. Resultado (4/6 esperado, 2/6
hallazgo real — **corregidos ambos, no solo reportados**):

| Prueba | Resultado | Estado |
|---|---|---|
| CS-01 CSRF sin token | 403 | OK |
| CS-02 Rate limit (61 req/60s) | 429 en el request 61 | OK |
| CS-03 Honeypot `_hp_field` lleno | 200 (bypass) | **corregido**: ahora se valida server-side, re-testeado |
| CS-04 Sanitización `<script>`/`<img onerror>` | tags removidos en Supabase | OK |
| CS-05 RLS SELECT `leads` (anon) | filas reales, PII en texto plano | hallazgo real = M-02/L8 |
| CS-06 RLS DELETE `lead_events` (anon) | 0 filas afectadas | OK |

**Texto sugerido para §5.4 (nuevo bloque CS-01…CS-06):** ver tabla de arriba + nota: "CS-03 detectó
que el honeypot solo se validaba client-side (JavaScript); corregido en `landing_page/app.py` el mismo
día y verificado con re-test (200 pero sin persistir el lead)."

**Sobre la nota relacionada del caso Html Injection:** consultado directamente en Supabase — el
mensaje original `<b>consulta</b> <script>alert('xss')</script>...` quedó persistido como
`consulta alert('xss') sobre automatizacion` (tags eliminados por completo, texto inerte). Confirma que
el HTML fue neutralizado, no crudo ni solo HTML-escapado.

**Evidencia:** `tests/resultados_v3/cs01_a_cs06_seguridad_m07.txt`, `tests/resultados_v3/cs_seguridad/`
(7 archivos), `tests/resultados_v3/m07_html_injection.txt`.

---

## M-06 — Matriz RF → evidencia faltante (RF-06, RF-07) (parte del Bloque de hallazgos mayores)

**Pedía:** capturas de la bandeja de entrada (email recibido) y del canal #nuevos-leads en Slack, o
declarar los requisitos como no verificados.

**Se hizo:** capturas tomadas por el usuario tras disparar leads de prueba reales. En el camino se
encontraron y corrigieron 3 bugs reales que habrían hecho fallar esta misma evidencia:
1. Credencial de Gmail OAuth2 vencida (reconectada por el usuario en n8n).
2. **Ambos nodos de Slack le faltaba el `=` inicial** en el campo `text` — n8n mandaba el texto con
   `{{ }}` literales sin evaluar, en vez del mensaje real. Corregido en el JSON.
3. Nodo Slack "Notificar al Equipo de Ventas" configurado en modo `user` con valor vacío (nunca se
   había terminado de configurar) → `channel_not_found`. Reconfigurado por el usuario a canal
   `#nuevos-leads`.
4. De regalo: la firma del email generado decía literalmente "Tu Nombre" / "Consultora de Software"
   (el prompt no especificaba una firma fija). Corregido: firma fija "Equipo Comercial / Sistema
   Inteligente de Gestión de Leads", y ampliada la prohibición de placeholders más allá de los que
   usan corchetes.

**Texto sugerido para el informe (agregar capturas como Anexo, referenciar en §5.2/matriz RF):**
> RF-06 y RF-07 verificados con evidencia: captura de email recibido en bandeja real y de notificación
> en el canal #nuevos-leads de Slack (ver Anexo [nuevo]). Durante la verificación se detectaron y
> corrigieron 3 defectos de configuración que impedían estas notificaciones (credencial OAuth2
> vencida, expresión de Slack sin evaluar, canal de Slack mal configurado).

**Evidencia:** capturas guardadas por el usuario (pendiente de indicar ubicación final, p. ej.
`docs/evidencia_anexos/RF-06_email_recibido.png` / `RF-07_slack_nuevos_leads.png`).

---

## m-19 / m-20 — Versiones exactas y artefactos de despliegue (Bloque editorial)

**Pedía:** fijar versiones exactas de Flask/n8n/Streamlit, adjuntar `requirements.txt` +
`docker-compose.yml`, e indicar el snapshot exacto del modelo.

**Se hizo:**
- Versiones verificadas: Flask 3.1.0, Streamlit 1.40.0 (coincide 100% con lo ya declarado, sin drift),
  n8n **2.18.7**, imagen Docker pineada por **digest** (no solo tag).
- `docker-compose.yml` nuevo (no existía; n8n se levantaba con `docker run` manual sin versión
  fijada).
- `tests/requirements.txt` corregido (`requests>=2.32.0` → `requests==2.32.3`, exacto).
- **Modelo confirmado empíricamente** (campo `"model"` de una respuesta real de OpenAI, no
  supuesto): **`gpt-4o-mini-2024-07-18`**. Se actualizó el workflow para pedir ese snapshot exacto en
  vez del alias flotante `gpt-4o-mini`, y se verificó con un lead de prueba que el comportamiento no
  cambió.

**Texto sugerido para §4.1 / §4.6:**
> Versiones exactas verificadas: Flask 3.1.0, Streamlit 1.40.0, n8n 2.18.7 (imagen
> `n8nio/n8n@sha256:4613a202...`), Python 3.11.3. Modelo: `gpt-4o-mini-2024-07-18` (snapshot
> confirmado en el campo `model` de la respuesta real de la API, pineado explícitamente en el
> pipeline). Artefactos de despliegue: `docker-compose.yml` (raíz del repo) y `requirements.txt` por
> módulo (`landing_page/`, `dashboard/`, `tests/`).

**Evidencia:** `tests/resultados_v3/m19_m20_versiones_artefactos.txt`, `docker-compose.yml`.

---

## Hallazgo crítico no numerado: service_role key filtrada

No es un ítem de la devolución, pero se encontró trabajando sobre C-05/M-07: la service_role key de
Supabase (bypassea RLS por completo) estaba hardcodeada en texto plano en
`n8n_workflow/Pipeline de Leads con IA.json`, **ya commiteada y pusheada a GitHub**. El usuario la
rotó de inmediato. Se reemplazó el valor hardcodeado por `{{$env.SUPABASE_SERVICE_ROLE_KEY}}`.
Vale la pena mencionarlo en el Anexo J como evidencia adicional de por qué la gestión de secretos
importa — es exactamente el tipo de brecha que el propio Anexo J ya discute en abstracto.

---

## Lo que NO se cubrió en esta sesión (según la propia devolución)

Para que quede claro el alcance — esto sigue pendiente de la devolución completa:

- **C-01** — recomponer §5.1 y Tabla 8 con la composición real del corpus (duplicados 10→5, agregar
  CP-11/CP-12).
- **C-03** — estratificar el LRT (3,29 s → 3,79 s para la ruta completa) y corregir el desvío a s=1,46.
- **M-01** — contradicción numérica del esquema (políticas/índices/funciones).
- **M-04** — precisión/recall/F1 por clase (precisión de spam real: 52,6 %).
- **M-03** — sección de riesgos de inyección de prompt en el Anexo J (aunque C-05 ya corrigió el
  prompt en sí, falta la sección de análisis).
- **M-08** — declaración ética / procedencia de los datos de prueba.
- **M-09** — Anexo K con el corpus de prueba completo.
- **M-10, M-11, M-12** — justificación del umbral de 8s, atribución del dato "21 veces", cifras de la
  columna "Manual".
- **m-01 a m-24** — todos los hallazgos menores y de estilo/APA (Bloque 6 completo).

Estos no requieren nueva ejecución (a diferencia de R-03, que ya se hizo) — son redacción sobre datos
que, en su mayoría, ya están calculados en el propio texto de la devolución.
