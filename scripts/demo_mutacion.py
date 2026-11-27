"""Script de demostración en vivo: anula una función, corre pytest y restaura el archivo.

Uso:
    python scripts/demo_mutacion.py dv
    python scripts/demo_mutacion.py mascara
    python scripts/demo_mutacion.py idempotencia
"""

from pathlib import Path
import subprocess
import sys

CASOS = {
    "dv": {
        "archivo": Path("src/registro/rut.py"),
        "buscar": "def calcular_digito_verificador(cuerpo: str) -> str:",
        "reemplazar": 'def calcular_digito_verificador(cuerpo: str) -> str:\n    return "X"  # MUTACION DEMO',
        "test": "tests/test_rut.py",
        "descripcion": "Anula el cálculo de dígito verificador (rompe casos 'K', '0' y dígitos válidos)",
    },
    "mascara": {
        "archivo": Path("src/registro/rut.py"),
        "buscar": "def enmascarar_rut(rut: str) -> str:",
        "reemplazar": "def enmascarar_rut(rut: str) -> str:\n    return rut  # MUTACION DEMO (expone PII)",
        "test": "tests/test_rut.py",
        "descripcion": "Anula el enmascaramiento de RUT (expone dato sensible sin ocultar)",
    },
    "idempotencia": {
        "archivo": Path("src/registro/almacen.py"),
        "buscar": "def obtener_por_idempotencia(",
        "reemplazar": "def obtener_por_idempotencia(*args, **kwargs):\n    return None  # MUTACION DEMO",
        "test": "tests/test_pacientes.py",
        "descripcion": "Anula la consulta por clave de idempotencia (provoca registros duplicados)",
    },
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in CASOS:
        print("Uso: python scripts/demo_mutacion.py [dv|mascara|idempotencia]")
        return 2

    caso = CASOS[sys.argv[1]]
    ruta: Path = caso["archivo"]
    original = ruta.read_text(encoding="utf-8")

    if caso["buscar"] not in original:
        print(f"No se encontró la firma esperada en {ruta}: {caso['buscar']}")
        return 1

    print(f"=== DEMO DE MUTACIÓN: {caso['descripcion']} ===")
    print(f"Archivo modificado temporalmente: {ruta}")

    try:
        mutado = original.replace(caso["buscar"], caso["reemplazar"], 1)
        ruta.write_text(mutado, encoding="utf-8")
        resultado = subprocess.run([sys.executable, "-m", "pytest", "-v", caso["test"]])
        if resultado.returncode != 0:
            print("\n[OK] La prueba falló en rojo como se esperaba al romper la función.")
        else:
            print("\n[ALERTA] La prueba pasó en verde pese a borrar la lógica de la función.")
        return 0
    finally:
        ruta.write_text(original, encoding="utf-8")
        print(f"Archivo restaurado a su estado original: {ruta}")


if __name__ == "__main__":
    raise SystemExit(main())
