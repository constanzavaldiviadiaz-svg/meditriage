"""Dónde se guardan los pacientes.

PROVISORIO: por ahora se guardan en memoria, en diccionarios de Python. Se pierden al
reiniciar la aplicación y cada réplica tiene los suyos. Es suficiente para empaquetar,
desplegar y probar la aplicación; la base de datos PostgreSQL del ADR 0004 reemplazará este
archivo sin cambiar el resto del código.
"""

# Pacientes registrados, por RUT. Sirve para detectar un RUT ya registrado.
pacientes_por_rut = {}

# Respuestas ya entregadas, por clave de idempotencia. Ver rutas.py.
respuestas_por_clave = {}


def vaciar():
    """Borra todo. Lo usan las pruebas para empezar cada una desde cero."""
    pacientes_por_rut.clear()
    respuestas_por_clave.clear()
