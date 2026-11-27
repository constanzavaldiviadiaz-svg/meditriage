"""Pruebas del registro de auditoría append-only (ADR 0004, sección 5).

Cada capa de protección tiene su prueba: los permisos, el trigger que rechaza cambios y la
cadena de hashes que delata una alteración.
"""

from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from tests.conftest import BASE_AUDITORIA, admin, url

pytestmark = pytest.mark.usefixtures("base_limpia")

GENESIS = "0" * 64


def como(rol):
    return psycopg.connect(url(BASE_AUDITORIA, rol), autocommit=True)


def insertar_evento(conexion, evento_id=None, datos=None):
    conexion.execute(
        "INSERT INTO auditoria.registro"
        " (evento_id, tipo, version, aggregate_id, trace_id, payload, creado_en)"
        " VALUES (%s, 'patient.registered', '1', %s, 'prueba', %s, now())"
        # Sin nombrar la columna: con una columna, PostgreSQL exige permiso de lectura.
        " ON CONFLICT DO NOTHING",
        (evento_id or uuid4(), uuid4(), Jsonb(datos or {"pacienteId": str(uuid4())})),
    )


def registros():
    with admin(BASE_AUDITORIA) as conexion:
        return conexion.execute(
            "SELECT secuencia, hash_anterior, hash_integridad FROM auditoria.registro"
            " ORDER BY secuencia"
        ).fetchall()


def verificar_cadena():
    with como("auditoria_lector") as conexion:
        return conexion.execute("SELECT auditoria.verificar_cadena()").fetchone()[0]


# --- Permisos ---------------------------------------------------------------------------


def test_el_escritor_puede_insertar():
    with como("auditoria_escritor") as conexion:
        insertar_evento(conexion)

    assert len(registros()) == 1


def test_el_escritor_no_puede_modificar_un_registro():
    with como("auditoria_escritor") as conexion:
        insertar_evento(conexion)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexion.execute("UPDATE auditoria.registro SET tipo = 'otro'")


def test_el_escritor_no_puede_borrar_un_registro():
    with como("auditoria_escritor") as conexion:
        insertar_evento(conexion)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexion.execute("DELETE FROM auditoria.registro")


def test_el_lector_no_puede_insertar():
    with como("auditoria_lector") as conexion, pytest.raises(
        psycopg.errors.InsufficientPrivilege
    ):
        insertar_evento(conexion)


# --- Trigger: rechaza cambios aunque haya permiso ---------------------------------------


def test_el_trigger_rechaza_un_update_incluso_del_administrador():
    with como("auditoria_escritor") as conexion:
        insertar_evento(conexion)

    with admin(BASE_AUDITORIA) as conexion, pytest.raises(
        psycopg.errors.RaiseException, match="append-only"
    ):
        conexion.execute("UPDATE auditoria.registro SET tipo = 'otro'")


def test_el_trigger_rechaza_un_delete_incluso_del_administrador():
    with como("auditoria_escritor") as conexion:
        insertar_evento(conexion)

    with admin(BASE_AUDITORIA) as conexion, pytest.raises(
        psycopg.errors.RaiseException, match="append-only"
    ):
        conexion.execute("DELETE FROM auditoria.registro")


def test_el_trigger_rechaza_un_truncate_incluso_del_administrador():
    with admin(BASE_AUDITORIA) as conexion, pytest.raises(
        psycopg.errors.RaiseException, match="append-only"
    ):
        conexion.execute("TRUNCATE auditoria.registro")


# --- Cadena de hashes -------------------------------------------------------------------


def test_cada_registro_se_encadena_con_el_anterior():
    with como("auditoria_escritor") as conexion:
        for _ in range(3):
            insertar_evento(conexion)

    primero, segundo, tercero = registros()
    assert [primero[0], segundo[0], tercero[0]] == [1, 2, 3]
    assert primero[1] == GENESIS
    assert segundo[1] == primero[2]
    assert tercero[1] == segundo[2]


def test_el_escritor_no_puede_imponer_el_hash():
    with como("auditoria_escritor") as conexion:
        conexion.execute(
            "INSERT INTO auditoria.registro (secuencia, evento_id, tipo, version, aggregate_id,"
            " trace_id, payload, creado_en, hash_anterior, hash_integridad)"
            " VALUES (99, %s, 'x', '1.0', %s, 'prueba', '{}', now(), %s, %s)",
            (uuid4(), uuid4(), "f" * 64, "f" * 64),
        )

    [(secuencia, hash_anterior, hash_integridad)] = registros()
    assert secuencia == 1
    assert hash_anterior == GENESIS
    assert hash_integridad != "f" * 64


def test_una_cadena_intacta_se_verifica_sin_errores():
    with como("auditoria_escritor") as conexion:
        for _ in range(3):
            insertar_evento(conexion)

    assert verificar_cadena() is None


def test_la_verificacion_delata_un_registro_alterado():
    with como("auditoria_escritor") as conexion:
        for _ in range(3):
            insertar_evento(conexion)

    # Alguien con acceso total a la base se salta el trigger y cambia el segundo registro.
    with admin(BASE_AUDITORIA) as conexion:
        conexion.execute("SET session_replication_role = replica")
        conexion.execute(
            "UPDATE auditoria.registro SET payload = '{\"pacienteId\": \"otro\"}'"
            " WHERE secuencia = 2"
        )

    assert verificar_cadena() == 2


def test_la_verificacion_delata_un_registro_borrado():
    with como("auditoria_escritor") as conexion:
        for _ in range(3):
            insertar_evento(conexion)

    with admin(BASE_AUDITORIA) as conexion:
        conexion.execute("SET session_replication_role = replica")
        conexion.execute("DELETE FROM auditoria.registro WHERE secuencia = 2")

    assert verificar_cadena() == 3


# --- Idempotencia -----------------------------------------------------------------------


def test_el_mismo_evento_no_se_audita_dos_veces():
    evento_id = uuid4()
    with como("auditoria_escritor") as conexion:
        insertar_evento(conexion, evento_id)
        insertar_evento(conexion, evento_id)

    assert len(registros()) == 1
    assert verificar_cadena() is None
