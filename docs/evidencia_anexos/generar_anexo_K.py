"""
======================================================================
GENERADOR DE ANEXO K - CORPUS DE PRUEBA COMPLETO (100 CASOS)
Pendiente M-09 de la devolucion: "Anexo K con el corpus de prueba
completo" (texto de los 100 mensajes con su etiqueta).

Extrae en vivo la funcion generar_100_casos() de tests/test_100_leads.py,
que es la UNICA fuente reproducible del corpus (evita repetir el problema
de la Tabla F.1 original, que no se pudo trazar a ningun archivo del
repositorio). Cada corrida estampa el commit de git (HEAD), igual que los
Anexos A-E/G/I (M-13).

USO:
    python docs/evidencia_anexos/generar_anexo_K.py

SALIDA:
    docs/evidencia_anexos/Anexo_K_Corpus_Prueba_100_Casos.txt
    docs/evidencia_anexos/Anexo_K_Corpus_Prueba_100_Casos.csv
======================================================================
"""
import csv
import importlib.util
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_PATH = os.path.join(ROOT, "tests", "test_100_leads.py")
OUT_TXT = os.path.join(ROOT, "docs", "evidencia_anexos", "Anexo_K_Corpus_Prueba_100_Casos.txt")
OUT_CSV = os.path.join(ROOT, "docs", "evidencia_anexos", "Anexo_K_Corpus_Prueba_100_Casos.csv")
REPO_URL = "https://github.com/Martinlepez031/Sistema-Inteligente-de-Gestion-de-Leads"

SEP = "=" * 72

# Etiqueta legible por tipo interno (para la columna "Etiqueta")
ETIQUETAS = {
    "compra_inmediata": "Compra inmediata",
    "solicita_info": "Solicita informacion",
    "email_invalido": "Email invalido (negativo)",
    "telefono_invalido": "Telefono invalido (negativo)",
    "duplicado": "Duplicado",
    "soporte": "Soporte tecnico",
    "spam": "Spam",
    "caracteres_especiales": "Caracteres especiales / idioma",
    "mensaje_borde": "Mensaje de borde",
    "adversarial": "Adversarial (prompt injection / jailbreak)",
    "multilingue": "Multilingue",
}


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


def cargar_casos():
    """Importa tests/test_100_leads.py por ruta de archivo (sin depender de
    que 'tests' sea un paquete importable) y devuelve generar_100_casos()."""
    spec = importlib.util.spec_from_file_location("test_100_leads", SRC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generar_100_casos()


def main():
    casos = cargar_casos()
    commit_hash, branch = get_commit_hash()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if commit_hash:
        cabecera = (
            f"NOTA DE VERSION (M-09 / M-13): este corpus se extrajo en vivo de\n"
            f"tests/test_100_leads.py::generar_100_casos(), la unica fuente\n"
            f"reproducible de los 100 casos de prueba (CP-01 a CP-12). El commit\n"
            f"de git que estaba en HEAD al generar este anexo fue:\n"
            f"  commit: {commit_hash}\n"
            f"  rama:   {branch}\n"
            f"  enlace: {REPO_URL}/tree/{commit_hash}\n"
            f"Generado: {ahora}\n"
            f"IMPORTANTE: si este archivo se commitea DESPUES de generarse, el\n"
            f"commit resultante sera distinto al citado arriba (un commit no puede\n"
            f"referenciar su propio hash). El hash correcto para citar es el del\n"
            f"commit inmediatamente POSTERIOR a esta generacion.\n"
        )
    else:
        cabecera = f"NOTA DE VERSION (M-09): no se pudo determinar el commit de git al generar este documento ({ahora}).\n"

    declaracion_etica = (
        "DECLARACION DE PROCEDENCIA DE LOS DATOS (M-08): los 100 mensajes de\n"
        "este corpus son sinteticos, redactados por el autor del TFI para cubrir\n"
        "las categorias de prueba CP-01 a CP-12. No provienen de leads reales ni\n"
        "de terceros: todos los nombres, emails (dominio @test-tfi.local) y\n"
        "telefonos son ficticios y fueron generados exclusivamente para la\n"
        "validacion funcional y de seguridad del pipeline. Ningun dato personal\n"
        "real fue utilizado ni expuesto en este anexo.\n"
    )

    conteo = Counter(c["categoria"] for c in casos)
    resumen_lineas = [
        f"  {cat:<10s} {n:>3d} casos  -> {ETIQUETAS.get(casos_por_cat(casos, cat), casos_por_cat(casos, cat))}"
        for cat, n in sorted(conteo.items())
    ]

    partes = [cabecera, declaracion_etica]

    partes.append(
        f"{SEP}\nANEXO K - CORPUS DE PRUEBA COMPLETO (100 CASOS, CP-01 a CP-12)\n"
        f"Fuente: tests/test_100_leads.py (funcion generar_100_casos)\n{SEP}\n\n"
        f"Total de casos: {len(casos)}\n\n"
        "Distribucion por categoria:\n" + "\n".join(resumen_lineas) + "\n"
    )

    tabla = [
        f"{'ID':<12s} {'Categoria':<10s} {'Etiqueta':<42s} {'Clasif. esperada':<20s} Mensaje",
        "-" * 160,
    ]
    for c in casos:
        etiqueta = ETIQUETAS.get(c["tipo"], c["tipo"])
        clasif_esp = c.get("esperado", {}).get("ia_clasificacion", "n/a")
        mensaje = c["mensaje"].replace("\n", " ").replace("\r", " ")
        tabla.append(f"{c['id']:<12s} {c['categoria']:<10s} {etiqueta:<42s} {clasif_esp:<20s} {mensaje}")

    partes.append("DETALLE CASO POR CASO:\n\n" + "\n".join(tabla))

    contenido = "\n\n".join(partes) + "\n"
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(contenido)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "categoria", "tipo", "etiqueta", "clasificacion_esperada", "mensaje"])
        for c in casos:
            writer.writerow([
                c["id"], c["categoria"], c["tipo"], ETIQUETAS.get(c["tipo"], c["tipo"]),
                c.get("esperado", {}).get("ia_clasificacion", "n/a"), c["mensaje"],
            ])

    print(f"OK -> {OUT_TXT}")
    print(f"OK -> {OUT_CSV}")
    print(f"Total casos: {len(casos)}")
    print(f"Commit HEAD al generar: {commit_hash} ({branch})")


def casos_por_cat(casos, cat):
    """Devuelve el 'tipo' representativo de una categoria (para el resumen)."""
    for c in casos:
        if c["categoria"] == cat:
            return c["tipo"]
    return cat


if __name__ == "__main__":
    main()
