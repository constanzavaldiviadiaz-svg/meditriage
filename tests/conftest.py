"""Bases de datos de prueba.

Las pruebas corren contra un PostgreSQL real, no contra un sustituto en memoria: lo que se
quiere probar (permisos, triggers, la cadena de hashes) solo existe en la base de datos.

Necesitan la variable PRUEBAS_ADMIN_URL, con un usuario administrador. Por ejemplo, con un
PostgreSQL en Docker:

    docker run -d --name meditriage-pg-pruebas -p 5433:5432 -e POSTGRES_PASSWORD=<clave> postgres:17
    export PRUEBAS_ADMIN_URL="postgresql://postgres:<clave>@localhost:5433/postgres"

En cada ejecución se crean desde cero dos bases, prueba_meditriage y prueba_auditoria, con los
mismos scripts de db/sql/ que usa el ambiente real.
"""

import os
import secrets
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from src import bd

RAIZ = Path(__file__).resolve().parent.parent
ADMIN_URL = os.getenv("PRUEBAS_ADMIN_URL")

BASE_PRINCIPAL = "prueba_meditriage"
BASE_AUDITORIA = "prueba_auditoria"

# Claves al azar en cada ejecución: no hay ninguna escrita en el repositorio.
CLAVES = {rol: secrets.token_urlsafe(16) for rol in
          ("meditriage_app", "auditoria_escritor", "auditoria_lector")}

SIN_BASE = (
    "Las pruebas necesitan PostgreSQL. Define PRUEBAS_ADMIN_URL con un usuario administrador; "
    "las instrucciones están al inicio de tests/conftest.py."
)


def url(base, usuario=None):
    """Cadena de conexión a una base de prueba, con el administrador o con un rol."""
    datos = conninfo_to_dict(ADMIN_URL)
    datos["dbname"] = base
    if usuario:
        datos["user"] = usuario
        datos["password"] = CLAVES[usuario]
    return make_conninfo(**datos)


def admin(base):
    """Conexión de administrador a una base de prueba."""
    return psycopg.connect(url(base), autocommit=True)


@pytest.fixture(scope="session")
def bases():
    """Crea las dos bases de prueba y apunta la aplicación a ellas."""
    if not ADMIN_URL:
        pytest.fail(SIN_BASE, pytrace=False)

    with psycopg.connect(ADMIN_URL, autocommit=True) as conexion:
        for base in (BASE_PRINCIPAL, BASE_AUDITORIA):
            conexion.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)")
                             .format(sql.Identifier(base)))
            conexion.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(base)))

    with admin(BASE_PRINCIPAL) as conexion:
        conexion.execute((RAIZ / "db/sql/meditriage.sql").read_text(encoding="utf-8"))
    with admin(BASE_AUDITORIA) as conexion:
        conexion.execute((RAIZ / "db/sql/auditoria.sql").read_text(encoding="utf-8"))
        for rol, clave in CLAVES.items():
            conexion.execute(sql.SQL("ALTER ROLE {} PASSWORD {}")
                             .format(sql.Identifier(rol), sql.Literal(clave)))

    os.environ["BASE_DATOS_URL"] = url(BASE_PRINCIPAL, "meditriage_app")
    os.environ["AUDITORIA_URL"] = url(BASE_AUDITORIA, "auditoria_escritor")
    os.environ["AUDITORIA_LECTURA_URL"] = url(BASE_AUDITORIA, "auditoria_lector")
    bd.cerrar()
    yield
    bd.cerrar()


@pytest.fixture
def base_limpia(bases):
    """Cada prueba parte con las tablas vacías."""
    with admin(BASE_PRINCIPAL) as conexion:
        # Todas las tablas de los dos contextos, para no tener que mantener la lista a mano.
        tablas = conexion.execute(
            "SELECT string_agg(format('%I.%I', schemaname, tablename), ', ')"
            " FROM pg_tables WHERE schemaname IN ('identidad', 'clinico')"
        ).fetchone()[0]
        conexion.execute(f"TRUNCATE {tablas}")
    with admin(BASE_AUDITORIA) as conexion:
        # El trigger rechaza TRUNCATE. Solo un superusuario puede saltárselo, y solo aquí.
        conexion.execute("SET session_replication_role = replica")
        conexion.execute("TRUNCATE auditoria.registro")
