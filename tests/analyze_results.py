"""
=========================================================================
ANÁLISIS DE RESULTADOS — Matriz de confusión y métricas por clase
Pipeline de Leads con IA — TFI UTN FRM
=========================================================================

Este script post-procesa los resultados de las pruebas del pipeline
completo (Flask + n8n) para generar:

1. Matriz de confusión de clasificación IA
2. Exactitud (accuracy) por clase
3. Recall por clase
4. Reporte de errores por categoría
5. Tabla formateada para el documento académico

USO:
  python tests/analyze_results.py [--input resultados_pruebas.json]
=========================================================================
"""
import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone


CLASES = ["compra_inmediata", "solicita_info", "soporte", "spam"]
CLASES_LABEL = {
    "compra_inmediata": "Compra inmediata",
    "solicita_info": "Solicita información",
    "soporte": "Soporte técnico",
    "spam": "Spam"
}


def cargar_resultados(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def construir_matriz_confusion(resultados):
    """
    Requiere que los resultados incluyan 'clasificacion_esperada' y
    'clasificacion_obtenida'. La clasificación obtenida viene de la IA
    en n8n. Si no está disponible, se omite el caso.
    """
    matriz = defaultdict(lambda: defaultdict(int))
    conteo_real = Counter()
    conteo_predicho = Counter()

    for r in resultados:
        esperada = r.get("clasificacion_esperada", "")
        obtenida = r.get("clasificacion_obtenida", "")

        if not esperada or esperada == "n/a":
            continue
        if not obtenida:
            continue

        matriz[esperada][obtenida] += 1
        conteo_real[esperada] += 1
        conteo_predicho[obtenida] += 1

    return matriz, conteo_real, conteo_predicho


def calcular_metricas(matriz, conteo_real):
    """Calcula exactitud por clase, recall por clase, y exactitud global."""
    metricas = {}

    for clase in CLASES:
        vp = matriz[clase][clase]  # verdaderos positivos
        total_clase = conteo_real.get(clase, 0)

        if total_clase == 0:
            metricas[clase] = {"exactitud": None, "recall": None, "total": 0, "aciertos": vp}
            continue

        recall = vp / total_clase
        metricas[clase] = {
            "exactitud": recall,
            "recall": recall,
            "total": total_clase,
            "aciertos": vp
        }

    # Exactitud global
    total_aciertos = sum(m["aciertos"] for m in metricas.values())
    total_evaluados = sum(m["total"] for m in metricas.values())
    exactitud_global = total_aciertos / max(total_evaluados, 1)

    return metricas, exactitud_global, total_aciertos, total_evaluados


def imprimir_matriz_confusion(matriz, conteo_real):
    """Imprime la matriz de confusión formateada."""
    print()
    print("  MATRIZ DE CONFUSIÓN — Clasificación IA")
    print("  " + "=" * 58)
    print("  " + " " * 22 + " ".join(f"{CLASES_LABEL.get(c, c):>20}" for c in CLASES))
    print("  " + "-" * 58)

    for clase_real in CLASES:
        fila = [matriz[clase_real][clase_pred] for clase_pred in CLASES]
        total = conteo_real.get(clase_real, 0)
        label = CLASES_LABEL.get(clase_real, clase_real)
        valores = " ".join(f"{v:>20}" for v in fila)
        print(f"  {label:<20s} {valores}  (n={total})")

    print("  " + "-" * 58)
    print()


def imprimir_metricas_por_clase(metricas, exactitud_global, total_aciertos, total_evaluados):
    """Imprime tabla de métricas por clase."""
    print(f"  EXACTITUD GLOBAL: {exactitud_global*100:.1f}% "
          f"({total_aciertos}/{total_evaluados} casos)")
    print()
    print(f"  {'Clase':<25s} {'n':>5s} {'Aciertos':>9s} {'Exactitud':>10s} {'Estado':>15s}")
    print("  " + "-" * 68)

    for clase in CLASES:
        m = metricas[clase]
        total = m["total"]
        aciertos = m["aciertos"]
        exact = m["exactitud"]
        if exact is not None:
            exact_str = f"{exact*100:.1f}%"
            if exact >= 0.80:
                estado = "✅ Bueno"
            elif exact >= 0.60:
                estado = "⚠️  Regular"
            else:
                estado = "❌ Deficiente"
        else:
            exact_str = "n/a"
            estado = "—"

        label = CLASES_LABEL.get(clase, clase)
        print(f"  {label:<25s} {total:>5d} {aciertos:>9d} {exact_str:>10s} {estado:>15s}")

    print()


def exportar_tabla_apa(metricas, exactitud_global, total_aciertos, total_evaluados,
                       matriz, conteo_real, output_dir):
    """Exporta una tabla formateada para inclusión en el documento académico."""

    ruta = os.path.join(output_dir, "tabla_matriz_confusion.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("Tabla X\n")
        f.write("Matriz de confusión de la clasificación de intención del lead mediante GPT-4o-mini\n\n")
        f.write(" " * 20 + "".join(f"{CLASES_LABEL.get(c, c):>18}" for c in CLASES) + "\n")
        f.write("-" * 92 + "\n")
        for clase_real in CLASES:
            fila = [str(matriz[clase_real][clase_pred]) for clase_pred in CLASES]
            label = CLASES_LABEL.get(clase_real, clase_real)
            f.write(f"{label:<20s}" + "".join(f"{v:>18}" for v in fila) + f"  (n={conteo_real.get(clase_real, 0)})\n")
        f.write("-" * 92 + "\n\n")
        f.write(f"Nota. Exactitud global = {exactitud_global*100:.1f}% "
                f"({total_aciertos}/{total_evaluados} casos). "
                f"Elaboración propia.\n")

    ruta2 = os.path.join(output_dir, "tabla_exactitud_por_clase.txt")
    with open(ruta2, "w", encoding="utf-8") as f:
        f.write("Tabla Y\n")
        f.write("Exactitud de clasificación por categoría de intención\n\n")
        f.write(f"{'Categoría':<30s} {'n':>6s} {'Exactitud':>12s}\n")
        f.write("-" * 50 + "\n")
        for clase in CLASES:
            m = metricas[clase]
            exact = f"{m['exactitud']*100:.1f}%" if m['exactitud'] is not None else "n/a"
            label = CLASES_LABEL.get(clase, clase)
            f.write(f"{label:<30s} {m['total']:>6d} {exact:>12s}\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Exactitud global':<30s} {total_evaluados:>6d} "
                f"{exactitud_global*100:>11.1f}%\n\n")
        f.write("Nota. n = cantidad de casos de prueba para esa categoría. "
                "Elaboración propia.\n")

    return ruta, ruta2


def main():
    print("=" * 68)
    print("  ANÁLISIS DE RESULTADOS — Clasificación IA")
    print("  TFI — Tecnicatura Superior en Programación — UTN FRM")
    print("=" * 68)

    # Buscar archivo de resultados
    output_dir = os.path.join(os.path.dirname(__file__), "resultados_v2")
    default_input = os.path.join(output_dir, "resultados_pruebas.json")

    input_path = sys.argv[1] if len(sys.argv) > 1 else default_input

    if not os.path.exists(input_path):
        print(f"\n  Archivo no encontrado: {input_path}")
        print("  Ejecutar primero el pipeline completo y luego este script.")
        print("\n  FORMATO ESPERADO DEL JSON:")
        print("  Cada resultado debe incluir:")
        print('    "clasificacion_esperada": "compra_inmediata"')
        print('    "clasificacion_obtenida": "solicita_info"  (de la IA en n8n)')
        print("\n  La clasificación obtenida debe extraerse de la base de datos")
        print("  o de los logs de n8n tras ejecutar el pipeline completo.")
        return

    data = cargar_resultados(input_path)
    resultados = data.get("resultados", data if isinstance(data, list) else [])

    print(f"\n  Archivo: {input_path}")
    print(f"  Total resultados cargados: {len(resultados)}")

    matriz, conteo_real, conteo_predicho = construir_matriz_confusion(resultados)

    total_con_clasificacion = sum(conteo_real.values())
    if total_con_clasificacion == 0:
        print("\n  ⚠️  Ningún resultado tiene clasificación_obtenida.")
        print("  El pipeline n8n debe ejecutarse primero para que la IA")
        print("  clasifique los leads. Luego extraer los resultados de la")
        print("  base de datos y agregar el campo clasificacion_obtenida.")
        return

    metricas, exactitud_global, total_aciertos, total_evaluados = \
        calcular_metricas(matriz, conteo_real)

    imprimir_matriz_confusion(matriz, conteo_real)
    imprimir_metricas_por_clase(metricas, exactitud_global, total_aciertos, total_evaluados)

    r1, r2 = exportar_tabla_apa(
        metricas, exactitud_global, total_aciertos, total_evaluados,
        matriz, conteo_real, output_dir
    )

    print(f"  Tablas APA exportadas a:")
    print(f"    {r1}")
    print(f"    {r2}")
    print("=" * 68)


if __name__ == "__main__":
    main()
