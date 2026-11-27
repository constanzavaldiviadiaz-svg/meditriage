"""Decide si el DAST bloquea el PR (#117, ADR 0007).

Lee el informe JSON de ZAP y falla si hay alguna alerta de riesgo Medium o superior que no
esté en la lista de excepciones. Las alertas Low e Informational se muestran, pero no bloquean.

Uso: python3 .zap/evaluar.py <reporte-zap.json> <excepciones.tsv>
"""

import json
import sys

RIESGOS = {0: "Informational", 1: "Low", 2: "Medium", 3: "High"}
UMBRAL = 2  # Medium


def leer_excepciones(ruta):
    """Devuelve {id de la regla: justificación}. Una línea por excepción; '#' comenta."""
    excepciones = {}
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            regla, _, justificacion = linea.partition("\t")
            if not justificacion.strip():
                sys.exit(f"La excepción de la regla {regla} no tiene justificación.")
            excepciones[regla.strip()] = justificacion.strip()
    return excepciones


def evaluar(reporte, excepciones):
    """Muestra cada alerta con su decisión y devuelve cuántas bloquean."""
    bloqueantes = 0
    for sitio in reporte.get("site", []):
        for alerta in sitio.get("alerts", []):
            riesgo = int(alerta["riskcode"])
            regla = alerta["pluginid"]
            if riesgo < UMBRAL:
                decision = "no bloquea"
            elif regla in excepciones:
                decision = f"excepción ({excepciones[regla]})"
            else:
                decision = "BLOQUEA"
                bloqueantes += 1
            print(f"{RIESGOS[riesgo]:<14}{decision:<12} {alerta['alert']} [{regla}], "
                  f"{alerta['count']} instancia(s)")
    return bloqueantes


def main(ruta_reporte, ruta_excepciones):
    excepciones = leer_excepciones(ruta_excepciones)
    with open(ruta_reporte, encoding="utf-8") as archivo:
        reporte = json.load(archivo)
    bloqueantes = evaluar(reporte, excepciones)
    if bloqueantes:
        print(f"\n{bloqueantes} alerta(s) de riesgo Medium o superior: el DAST bloquea.")
        return 1
    print("\nNinguna alerta de riesgo Medium o superior.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
