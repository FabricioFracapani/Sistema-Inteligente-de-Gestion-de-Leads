"""
=========================================================================
RENDERIZADOR DE DIAGRAMAS - Mermaid a PNG/SVG
Pipeline de Leads con IA - TFI UTN FRM
=========================================================================

Convierte los archivos .mmd en la carpeta docs/diagrams/ a imagenes
PNG y SVG usando la API publica de Mermaid.ink via POST (pako).

USO:
  python docs/diagrams/render_diagrams.py

DEPENDENCIAS:
  pip install requests

NOTA: Si Mermaid.ink no responde, los diagramas en formato .mmd pueden
visualizarse directamente en:
  - https://mermaid.live (copiar y pegar el contenido)
  - GitHub (soporta renderizado nativo de Mermaid en Markdown)
  - VS Code con la extension "Markdown Preview Mermaid Support"
=========================================================================
"""
import os
import sys
import json
import base64
import zlib
import requests

DIAGRAMS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(DIAGRAMS_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def encode_mermaid_pako(mermaid_code):
    """
    Codifica codigo Mermaid usando pako (deflate + base64url)
    compatible con mermaid.ink.
    Ref: https://github.com/jihchi/mermaid.ink
    """
    data = mermaid_code.encode("utf-8")
    compressed = zlib.compress(data, level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return encoded


def render_diagram_http_post(mmd_file, output_basename):
    """
    Renderiza un diagrama usando HTTP POST a mermaid.ink (formato pako).
    """
    with open(mmd_file, "r", encoding="utf-8") as f:
        mermaid_code = f.read().strip()

    if not mermaid_code:
        print(f"  [SKIP] Archivo vacio: {mmd_file}")
        return

    encoded = encode_mermaid_pako(mermaid_code)

    png_path = os.path.join(OUTPUT_DIR, f"{output_basename}.png")
    svg_path = os.path.join(OUTPUT_DIR, f"{output_basename}.svg")

    for ext, fmt, mime in [("png", "PNG", "image/png"), ("svg", "SVG", "image/svg+xml")]:
        path = os.path.join(OUTPUT_DIR, f"{output_basename}.{ext}")
        try:
            resp = requests.post(
                f"https://mermaid.ink/img/pako:{encoded}",
                headers={"Accept": mime},
                timeout=60
            )
            if resp.status_code == 200:
                with open(path, "wb") as f:
                    f.write(resp.content)
                size_kb = len(resp.content) / 1024
                print(f"  [OK]  {fmt}: {os.path.basename(path)} ({size_kb:.1f} KB)")
            else:
                print(f"  [ERR] {fmt}: HTTP {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"  [ERR] {fmt}: {str(e)[:100]}")


def render_diagram_fallback(mmd_file, output_basename):
    """
    Fallback: guarda el codigo Mermaid como .txt y genera un HTML
    auto-contenido que se puede abrir en el navegador.
    """
    with open(mmd_file, "r", encoding="utf-8") as f:
        mermaid_code = f.read()

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{output_basename}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'default'}});</script>
<style>
  body {{ margin: 40px; font-family: system-ui, sans-serif; }}
  h2 {{ color: #333; }}
  .mermaid {{ margin: 20px 0; }}
</style>
</head>
<body>
<h2>{output_basename}</h2>
<div class="mermaid">
{mermaid_code}
</div>
<p style="color:#888;font-size:12px;margin-top:30px;">
TFI - Sistema Inteligente de Gestion de Leads - UTN FRM - 2026
</p>
</body>
</html>"""

    html_path = os.path.join(OUTPUT_DIR, f"{output_basename}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [OK]  HTML: {os.path.basename(html_path)} (abrir en navegador)")


def main():
    print("=" * 60)
    print("  RENDERIZADOR DE DIAGRAMAS")
    print("  TFI - Sistema Inteligente de Gestion de Leads")
    print("=" * 60)
    print()

    mmd_files = sorted(
        [f for f in os.listdir(DIAGRAMS_DIR) if f.endswith(".mmd")]
    )

    if not mmd_files:
        print("  No se encontraron archivos .mmd en:", DIAGRAMS_DIR)
        return

    config = {
        "figura1_arquitectura_componentes.mmd": "Figura 1 - Arquitectura de Componentes",
        "figura2_secuencia_flujo_respuesta.mmd": "Figura 2 - Secuencia del Flujo de Respuesta",
        "figura3_entidad_relacion.mmd": "Figura 3 - Diagrama Entidad-Relacion",
    }

    for mmd_file in mmd_files:
        title = config.get(mmd_file, mmd_file)
        filepath = os.path.join(DIAGRAMS_DIR, mmd_file)
        output_name = mmd_file.replace(".mmd", "")

        print(f"  {title}")
        print(f"  Fuente: {mmd_file}")

        # Intentar renderizar via mermaid.ink
        render_diagram_http_post(filepath, output_name)

        # Siempre generar HTML fallback (auto-contenido)
        render_diagram_fallback(filepath, output_name)

        print()

    print(f"  Archivos generados en: {OUTPUT_DIR}")
    print()
    print("  Para obtener PNG de alta resolucion:")
    print("  1. Abrir los archivos .html en el navegador")
    print("  2. Click derecho -> Inspeccionar -> seleccionar el SVG")
    print("  3. Copiar y pegar en un editor de imagenes o guardar como .svg")
    print("  Alternativa: https://mermaid.live (copiar y pegar el .mmd)")
    print("=" * 60)


if __name__ == "__main__":
    main()
