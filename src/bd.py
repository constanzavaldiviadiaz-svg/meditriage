"""Conexiones a PostgreSQL (ADR 0004).

La aplicación usa dos bases:

- **Principal** (`BASE_DATOS_URL`): los contextos de identidad y clínico, y la outbox.
- **Auditoría** (`AUDITORIA_URL`): el registro append-only, en una base separada. El worker
  entra con un rol que solo puede insertar.
- **Auditoría, solo lectura** (`AUDITORIA_LECTURA_URL`): la misma base, con un rol que solo
  puede leer. Lo usa la API para consultar las decisiones (HU05); nunca recibe la credencial
  que escribe.

Las direcciones vienen de variables de entorno (factor III del 12-Factor). En Kubernetes,
de un Secret que crea Terraform (ADR 0005). Nunca se escriben en el código.

Cada base tiene un pool de conexiones, que se abre la primera vez que se usa.
"""

import os
from contextlib import contextmanager

from psycopg_pool import ConnectionPool

# Cuánto esperar una conexión libre antes de rendirse, en segundos. Corto a propósito: la
# respuesta de triage tiene un presupuesto de 3 segundos.
ESPERA_CONEXION = 2

_pools = {}


def _pool(variable):
    if variable not in _pools:
        pool = ConnectionPool(
            os.environ[variable],
            min_size=1,
            max_size=5,
            kwargs={"connect_timeout": ESPERA_CONEXION},
            open=False,
        )
        pool.open(wait=False)
        _pools[variable] = pool
    return _pools[variable]


@contextmanager
def principal():
    """Una conexión a la base principal. Al salir del bloque se confirma la transacción; si
    hubo un error, se deshace completa."""
    with _pool("BASE_DATOS_URL").connection(timeout=ESPERA_CONEXION) as conexion:
        yield conexion


@contextmanager
def auditoria():
    """Una conexión a la base de auditoría, con permiso solo para insertar."""
    with _pool("AUDITORIA_URL").connection(timeout=ESPERA_CONEXION) as conexion:
        yield conexion


@contextmanager
def auditoria_lectura():
    """Una conexión a la base de auditoría, con permiso solo para leer."""
    with _pool("AUDITORIA_LECTURA_URL").connection(timeout=ESPERA_CONEXION) as conexion:
        yield conexion


def principal_disponible():
    """¿Responde la base principal? Lo usa la sonda /ready.

    La de auditoría no se revisa a propósito: si se cae, los eventos esperan en la outbox y
    el triage sigue funcionando (ADR 0004). Marcar la aplicación como no lista por eso
    dejaría sin servicio a la sala de espera.
    """
    try:
        with principal() as conexion:
            conexion.execute("SELECT 1")
    except Exception:
        return False
    return True


def cerrar():
    """Cierra todos los pools. Al apagar la aplicación, y en las pruebas para simular un
    reinicio."""
    while _pools:
        _, pool = _pools.popitem()
        pool.close()
