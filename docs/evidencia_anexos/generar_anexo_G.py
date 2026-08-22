"""
======================================================================
REGENERADOR DEL ANEXO G - a partir del JSON real del workflow
El Anexo G actual (texto pegado en el .docx) fue generado con una
version vieja del workflow: numeracion de nodos, posiciones x/y y el
paso de persistencia en Supabase ya no coinciden con
"n8n_workflow/Pipeline de Leads con IA.json" (v3, 21 nodos).

En particular, la version actual persiste en DOS pasos:
  1) INSERT temprano (apenas valida el email) con SUPABASE_ANON_KEY
     -> permitido por la policy RLS "anon_can_insert_leads".
  2) UPDATE posterior (con el resultado de la IA) con
     SUPABASE_SERVICE_ROLE_KEY -> obligatorio, porque la policy RLS
     "authenticated_can_update_leads" solo otorga UPDATE al rol
     'authenticated', y n8n no abre sesion como usuario autenticado.
     service_role bypassea RLS y es la unica forma de que el UPDATE
     funcione.

Este script lee el JSON real (nodos + conexiones + credenciales por
header) y regenera el bloque de Anexo G para que quede coherente con
el artefacto, en vez de mantenerlo escrito a mano. Cada corrida estampa
su propia fecha de generacion (UTC) al pie del documento -no repetir
manualmente una fecha vieja-, para que el Anexo G nunca quede fechado
antes de la corrida que dice documentar (M-14).

USO:
    python docs/evidencia_anexos/generar_anexo_G.py

SALIDA:
    docs/evidencia_anexos/Anexo_G_Pipeline_n8n.txt
    (reemplaza la version vieja/desactualizada del mismo nombre)
======================================================================
"""
import json
import os
import subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSON_PATH = os.path.join(ROOT, "n8n_workflow", "Pipeline de Leads con IA.json")
OUT_PATH = os.path.join(ROOT, "docs", "evidencia_anexos", "Anexo_G_Pipeline_n8n.txt")
REPO_URL = "https://github.com/Martinlepez031/Sistema-Inteligente-de-Gestion-de-Leads"


def get_commit_hash():
    try:
        h = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return h
    except Exception:
        return None

# Descripciones funcionales (no estan en el JSON, se documentan a mano
# una sola vez aca; todo lo demas -orden, nombre, tipo, auth- sale del JSON)
DESCRIPCIONES = {
    "📥 Webhook: Recibir Lead desde Flask":
        "Recibe POST desde Flask. Responde HTTP 200 inmediatamente (fast ack).",
    "⚙️ Normalización ETL + Enriquecimiento":
        "5 submodulos ETL: mapeo unificado, normalizacion TitleCase/lowercase, "
        "validacion email RFC 5322 + telefono, UUID v4 + timestamp ISO 8601, "
        "preparacion de campos para IA.",
    "✅ Validar: Email OK?":
        "Si el email no supera la validacion, va a registro de errores y corta el flujo.",
    "Persistir Early (Insert)":
        "INSERT temprano del lead en la tabla leads, ANTES de invocar la IA. "
        "Garantiza que el lead no se pierda si OpenAI falla o hace timeout.",
    "🤖 IA: Clasificar Intención (GPT-4o-mini)":
        "Clasifica el mensaje: clasificacion, prioridad (1-100), confianza, resumen.",
    "📊 Parsear: Extraer Clasificación IA":
        "Parsea el JSON devuelto por GPT-4o-mini. Fallback seguro si falla el parseo.",
    "🚫 ¿Es SPAM?":
        "Si la IA clasifica como SPAM, no se genera email; igual se actualiza el registro.",
    "🤖 IA: Generar Email Personalizado (GPT-4o-mini)":
        "Genera el email HTML personalizado segun la intencion del lead.",
    "📊 Parsear: Extraer Email Generado por IA":
        "Parsea el JSON con el email generado. Fallback generico si falla el parseo.",
    "Actualizar IA en Supabase":
        "UPDATE (PATCH por id_lead) con los resultados de la IA: clasificacion, "
        "prioridad, confianza, resumen y email HTML generado.",
    "⚠️ Registrar: Lead Inválido en Log de Errores":
        "Procesa leads que no superan la validacion. Registra tipo_evento='validacion_fallo'.",
    "🛡️ Error Trigger":
        "Se activa ante cualquier excepcion no capturada en el flujo principal (fail-loudly).",
    "📧 Gmail: Enviar Email al Lead":
        "Envia el email personalizado. Si la generacion IA fallo, usa mensaje generico.",
    "🔔 Slack: Notificar al Equipo de Ventas":
        "Notifica #nuevos-leads con los datos del lead y el resultado del scoring IA.",
    "🚨 Slack: Alerta Crítica de Error":
        "Alerta al equipo tecnico con los detalles del error. Canal #alertas-sistema.",
}


def auth_env_var(node):
    """Para nodos httpRequest: devuelve la env var usada en el header apikey."""
    if node["type"] != "n8n-nodes-base.httpRequest":
        return None
    headers = node["parameters"].get("headerParameters", {}).get("parameters", [])
    for h in headers:
        if h["name"] == "apikey":
            val = h["value"]
            if "SUPABASE_SERVICE_ROLE_KEY" in val:
                return "SUPABASE_SERVICE_ROLE_KEY (service_role -> bypassea RLS)"
            if "SUPABASE_ANON_KEY" in val:
                return "SUPABASE_ANON_KEY (anon -> requiere policy explicita)"
    return None


def topo_order(nodes, connections):
    by_name = {n["name"]: n for n in nodes if n["type"] != "n8n-nodes-base.stickyNote"}
    edges = {name: [] for name in by_name}
    indeg = {name: 0 for name in by_name}
    for src, outputs in connections.items():
        if src not in by_name:
            continue
        for out_list in outputs.get("main", []):
            for c in out_list:
                tgt = c["node"]
                if tgt not in by_name:
                    continue
                edges[src].append(tgt)
                indeg[tgt] += 1

    roots = [n for n in by_name if indeg[n] == 0]

    order = []
    seen = set()

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        order.append(name)
        for tgt in edges.get(name, []):
            visit(tgt)

    for r in roots:
        visit(r)
    for n in by_name:
        visit(n)

    return order, by_name, edges


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        wf = json.load(f)

    order, by_name, edges = topo_order(wf["nodes"], wf["connections"])
    funcionales = [n for n in wf["nodes"] if n["type"] != "n8n-nodes-base.stickyNote"]
    sticky = [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.stickyNote"]

    lineas = []
    lineas.append("=" * 72)
    lineas.append("ANEXO G — EVIDENCIA DEL PIPELINE DE AUTOMATIZACION (n8n)")
    lineas.append("=" * 72)
    lineas.append(f"Workflow: {wf['name']}")
    lineas.append(f"Total nodos: {len(wf['nodes'])} ({len(funcionales)} funcionales + {len(sticky)} sticky notes)")
    lineas.append(
        "Timezone: no configurada explicitamente en el contenedor n8n "
        "(GENERIC_TIMEZONE sin definir; usa el default de n8n, no se asume "
        "America/Argentina/Buenos_Aires salvo que se configure esa variable)."
    )
    lineas.append("")
    lineas.append("NODOS DEL PIPELINE (orden de ejecucion real, extraido del JSON):")
    lineas.append("-" * 72)
    for i, name in enumerate(order, 1):
        node = by_name[name]
        tipo = node["type"].split(".")[-1]
        lineas.append(f"{i:3d}. [{tipo:15s}] {name}")
        desc = DESCRIPCIONES.get(name, "(sin descripcion documentada)")
        lineas.append(f"     Funcion: {desc}")
        auth = auth_env_var(node)
        if auth:
            lineas.append(f"     Autenticacion: {auth}")
        lineas.append("")

    lineas.append("CONEXIONES ENTRE NODOS (real, desde el JSON):")
    lineas.append("-" * 72)
    for name in order:
        for tgt in edges.get(name, []):
            lineas.append(f"  {name}  ->  {tgt}")

    lineas.append("")
    lineas.append("POR QUE DOS CLAVES DISTINTAS (para OE5 / 3.4 / Anexo J):")
    lineas.append("-" * 72)
    lineas.append(
        "El pipeline escribe en 'leads' en dos momentos con dos roles distintos:\n"
        "  1) INSERT temprano (nodo 'Persistir Early (Insert)') con SUPABASE_ANON_KEY,\n"
        "     apenas el lead pasa la validacion de email -> antes de llamar a la IA.\n"
        "     Valido porque la policy RLS 'anon_can_insert_leads' otorga INSERT a anon.\n"
        "  2) UPDATE posterior (nodo 'Actualizar IA en Supabase', metodo PATCH) con\n"
        "     SUPABASE_SERVICE_ROLE_KEY, una vez la IA genera clasificacion y email.\n"
        "     Es obligatorio usar service_role aca: la policy RLS\n"
        "     'authenticated_can_update_leads' solo otorga UPDATE al rol 'authenticated',\n"
        "     y n8n no abre una sesion de usuario autenticado. Con anon key, ese UPDATE\n"
        "     seria bloqueado por RLS (0 filas afectadas). service_role bypassea RLS.\n"
        "  Diseno: el INSERT temprano con anon key existe para no perder el lead si la\n"
        "  IA falla o hace timeout; el UPDATE con service_role llega despues, solo si la\n"
        "  IA responde bien, y requiere el rol privilegiado por la propia politica de la\n"
        "  tabla."
    )

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    commit_hash = get_commit_hash()
    lineas.append("")
    lineas.append(f"Documento generado: {ahora}")
    lineas.append("Fuente: n8n_workflow/Pipeline de Leads con IA.json")
    if commit_hash:
        lineas.append(f"Commit HEAD al generar (M-13): {commit_hash}")
        lineas.append(f"Enlace: {REPO_URL}/tree/{commit_hash}")

    contenido = "\n".join(lineas) + "\n"
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(contenido)

    total = len(order)
    print(f"OK -> {OUT_PATH}")
    print(f"Nodos funcionales (sin sticky notes): {total}")
    print(f"Generado: {ahora}")


if __name__ == "__main__":
    main()
