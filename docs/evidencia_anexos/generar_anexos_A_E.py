"""
======================================================================
GENERADOR DE FRAGMENTOS REALES - ANEXOS A a E
Extrae codigo/config real (no descripciones) desde los archivos fuente
del proyecto, para pegar directamente en el TFI (Word).

M-13: cada corrida estampa el commit de git (HEAD) sobre el que se
genero el fragmento, para que la evidencia sea trazable a una version
exacta del repositorio (y no quede "flotando" sin referencia).

Los anexos A y C ahora se extraen por marcador de texto (no por numero
de linea fijo): un numero de linea hardcodeado queda desactualizado en
cuanto alguien edita el archivo fuente por otro motivo -es justamente
el tipo de fragilidad que hace irreproducible la evidencia-.

USO:
    python docs/evidencia_anexos/generar_anexos_A_E.py

SALIDA:
    docs/evidencia_anexos/Anexos_A_E_Fragmentos_Reales.txt
======================================================================
"""
import json
import os
import re
import subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_PATH = os.path.join(ROOT, "docs", "evidencia_anexos", "Anexos_A_E_Fragmentos_Reales.txt")
REPO_URL = "https://github.com/Martinlepez031/Sistema-Inteligente-de-Gestion-de-Leads"

SEP = "=" * 72


def read_lines(rel_path, start, end):
    """Lee lineas [start, end] (1-indexed, inclusive) de un archivo."""
    path = os.path.join(ROOT, rel_path)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[start - 1:end]).rstrip("\n")


def read_between(rel_path, start_marker, end_marker, include_start=True, include_end=True):
    """Extrae el texto entre la primera linea que contiene start_marker y
    la primera linea posterior que contiene end_marker. Robusto a que el
    archivo gane o pierda lineas en otra parte -a diferencia de un rango
    de numeros de linea fijo-."""
    path = os.path.join(ROOT, rel_path)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_idx = next((i for i, l in enumerate(lines) if start_marker in l), None)
    if start_idx is None:
        raise ValueError(f"[{rel_path}] no se encontro start_marker: {start_marker!r}")
    end_idx = next(
        (i for i in range(start_idx + 1, len(lines)) if end_marker in lines[i]), None
    )
    if end_idx is None:
        raise ValueError(f"[{rel_path}] no se encontro end_marker: {end_marker!r}")

    if not include_start:
        start_idx += 1
    if include_end:
        end_idx += 1

    return "".join(lines[start_idx:end_idx]).rstrip("\n")


def find_node(nodes, name):
    for n in nodes:
        if n.get("name") == name:
            return n
    raise KeyError(f"Nodo no encontrado: {name}")


def extraer_system_prompt(json_body_expr):
    """Los nodos IA ahora son HTTP Request que arman el body con
    JSON.stringify({...}) en una expresion de n8n. El primer mensaje
    role=system es el prompt; se extrae con una regex que respeta
    comillas escapadas (\\") dentro del string JS."""
    m = re.search(
        r'role:\s*"system",\s*content:\s*"((?:[^"\\]|\\.)*)"',
        json_body_expr,
    )
    if not m:
        raise ValueError("no se encontro el system prompt dentro del jsonBody")
    crudo = m.group(1)
    return crudo.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")


def get_commit_hash():
    try:
        h = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return h, branch
    except Exception:
        return None, None


def build_anexo_b():
    """Extrae del JSON de n8n: codigo del nodo ETL, ambos system prompts
    (ahora embebidos en el jsonBody de los nodos HTTP Request que llaman
    a la API de OpenAI con response_format: json_schema) y la
    configuracion de la llamada REST a Supabase."""
    json_path = os.path.join(ROOT, "n8n_workflow", "Pipeline de Leads con IA.json")
    with open(json_path, "r", encoding="utf-8") as f:
        wf = json.load(f)
    nodes = wf["nodes"]

    etl_code = find_node(nodes, "⚙️ Normalización ETL + Enriquecimiento")["parameters"]["jsCode"]

    clasif_node = find_node(nodes, "\U0001f916 IA: Clasificar Intención (GPT-4o-mini)")
    email_node = find_node(nodes, "\U0001f916 IA: Generar Email Personalizado (GPT-4o-mini)")
    clasif_prompt = extraer_system_prompt(clasif_node["parameters"]["jsonBody"])
    email_prompt = extraer_system_prompt(email_node["parameters"]["jsonBody"])

    supabase_req = find_node(nodes, "Persistir Early (Insert)")["parameters"]
    supabase_req_pretty = json.dumps(
        {
            "method": supabase_req.get("method"),
            "url": supabase_req.get("url"),
            "headerParameters": supabase_req.get("headerParameters"),
        },
        indent=2,
        ensure_ascii=False,
    )

    return (
        f"--- Nodo Code: Normalizacion ETL + Enriquecimiento "
        f"(n8n_workflow/Pipeline de Leads con IA.json) ---\n\n"
        f"{etl_code}\n\n"
        f"--- System prompt: IA Clasificar Intencion (HTTP Request -> OpenAI, "
        f"response_format: json_schema) ---\n\n"
        f"{clasif_prompt}\n\n"
        f"--- System prompt: IA Generar Email Personalizado (HTTP Request -> OpenAI, "
        f"response_format: json_schema) ---\n\n"
        f"{email_prompt}\n\n"
        f"--- Config REST: Persistir Early (Insert) -> Supabase ---\n\n"
        f"{supabase_req_pretty}"
    )


def main():
    partes = []

    commit_hash, branch = get_commit_hash()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if commit_hash:
        cabecera = (
            f"NOTA DE VERSION (M-13): estos fragmentos se extrajeron en vivo de los\n"
            f"archivos fuente al momento de generar este documento. El commit de git\n"
            f"que estaba en HEAD en ese momento fue:\n"
            f"  commit: {commit_hash}\n"
            f"  rama:   {branch}\n"
            f"  enlace: {REPO_URL}/tree/{commit_hash}\n"
            f"Generado: {ahora}\n"
            f"IMPORTANTE: si este mismo archivo se commitea DESPUES de generarse, el\n"
            f"commit resultante sera distinto al citado arriba (un commit no puede\n"
            f"referenciar su propio hash). El hash correcto para citar es el del\n"
            f"commit inmediatamente POSTERIOR a esta generacion -confirmar en el\n"
            f"historial de git cual quedo justo despues de este archivo-.\n"
        )
    else:
        cabecera = (
            "NOTA DE VERSION (M-13): no se pudo determinar el commit de git al "
            f"generar este documento ({ahora}).\n"
        )

    partes.append(cabecera)

    # ------------------------------------------------------------
    # ANEXO A - Flask security headers
    # ------------------------------------------------------------
    anexo_a = read_between(
        "landing_page/app.py",
        "# SECURITY HEADERS (aplicados a TODAS las respuestas)",
        "return response",
    )
    partes.append(
        f"{SEP}\nANEXO A - CODIGO FLASK: SECURITY HEADERS\n"
        f"Fuente: landing_page/app.py (funcion set_security_headers)\n{SEP}\n\n"
        + anexo_a
    )

    # ------------------------------------------------------------
    # ANEXO B - Workflow n8n
    # ------------------------------------------------------------
    partes.append(
        f"{SEP}\nANEXO B - WORKFLOW n8n: Pipeline de Leads con IA.json\n"
        f"Fuente: n8n_workflow/Pipeline de Leads con IA.json\n{SEP}\n\n"
        + build_anexo_b()
    )

    # ------------------------------------------------------------
    # ANEXO C - Schema SQL / RLS
    # ------------------------------------------------------------
    ddl_leads = read_between("database/schema.sql", "CREATE TABLE leads (", ");")
    rls_block = read_between(
        "database/schema.sql",
        "POLÍTICAS PARA TABLA leads",
        "7. ROLES PERSONALIZADOS",
        include_end=False,
    )
    partes.append(
        f"{SEP}\nANEXO C - SCHEMA SQL: ROW LEVEL SECURITY\n"
        f"Fuente: database/schema.sql\n{SEP}\n\n"
        f"--- DDL: CREATE TABLE leads ---\n\n{ddl_leads}\n\n"
        f"--- Politicas RLS P1 a P11: 7 son CREATE POLICY, "
        f"4 (P4, P5, P8, P10/P11) son ausencia deliberada de politica "
        f"(deny-by-default), documentada en comentario ---\n\n{rls_block}"
    )

    # ------------------------------------------------------------
    # ANEXO D - Dashboard Streamlit
    # ------------------------------------------------------------
    conexion = read_lines("dashboard/dashboard.py", 30, 41)
    kpis = read_lines("dashboard/dashboard.py", 189, 232)
    detalle = read_lines("dashboard/dashboard.py", 260, 303)
    partes.append(
        f"{SEP}\nANEXO D - DASHBOARD STREAMLIT: KPIs\n"
        f"Fuente: dashboard/dashboard.py\n{SEP}\n\n"
        f"--- Conexion a Supabase (lineas 30-41) ---\n\n{conexion}\n\n"
        f"--- 5 KPI cards (lineas 189-232) ---\n\n{kpis}\n\n"
        f"--- Vista de lista + detalle del lead (lineas 260-303) ---\n\n{detalle}"
    )

    # ------------------------------------------------------------
    # ANEXO E - Script de pruebas
    # ------------------------------------------------------------
    docstring = read_lines("tests/test_100_leads.py", 1, 23)
    cp01 = read_lines("tests/test_100_leads.py", 64, 103)
    lrt = read_lines("tests/test_100_leads.py", 460, 509)
    export = read_lines("tests/test_100_leads.py", 570, 608)
    partes.append(
        f"{SEP}\nANEXO E - SCRIPT DE PRUEBAS: test_100_leads.py\n"
        f"Fuente: tests/test_100_leads.py\n{SEP}\n\n"
        f"--- Cabecera / metodologia (lineas 1-23) ---\n\n{docstring}\n\n"
        f"--- Generacion de casos CP-01 como ejemplo (lineas 64-103) ---\n\n{cp01}\n\n"
        f"--- Medicion de LRT por caso (lineas 460-509) ---\n\n{lrt}\n\n"
        f"--- Exportacion CSV/JSON + metadata (lineas 570-608) ---\n\n{export}"
    )

    contenido = "\n\n\n".join(partes) + "\n"
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"OK -> {OUT_PATH}")
    print(f"({len(contenido.splitlines())} lineas generadas)")
    print(f"Commit HEAD al generar: {commit_hash} ({branch})")


if __name__ == "__main__":
    main()
