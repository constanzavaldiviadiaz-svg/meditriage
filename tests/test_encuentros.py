"""Pruebas de POST /v1/encuentros (HU02): abrir un encuentro para un paciente registrado."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.evaluacion import encuentros
from src.main import app
from tests.ayudantes import abrir_encuentro, registrar_paciente
from tests.conftest import BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)
URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


def abrir(paciente_id, clave=None):
    return cliente.post("/v1/encuentros", json={"pacienteId": str(paciente_id)},
                        headers={"Idempotency-Key": str(clave or uuid4())})


def filas_de_encuentro():
    with admin(BASE_PRINCIPAL) as conexion:
        return conexion.execute(
            "SELECT encuentro_id, paciente_id, estado, edad_dias, sexo FROM clinico.encuentro"
        ).fetchall()


def test_abre_un_encuentro():
    paciente_id = registrar_paciente(cliente)

    respuesta = abrir(paciente_id)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "abierto"
    assert cuerpo["pacienteId"] == str(paciente_id)
    assert respuesta.headers["Location"] == f"/v1/encuentros/{cuerpo['encuentroId']}"


def test_guarda_la_foto_de_edad_y_sexo():
    nacimiento = (datetime.now(UTC) - timedelta(days=400)).date().isoformat()
    paciente_id = registrar_paciente(cliente, fechaNacimiento=nacimiento, sexo="masculino")

    abrir_encuentro(cliente, paciente_id)

    [(_, _, _, edad_dias, sexo)] = filas_de_encuentro()
    assert (edad_dias, sexo) == (400, "masculino")


def test_sin_fecha_de_nacimiento_la_edad_queda_desconocida():
    abrir_encuentro(cliente, registrar_paciente(cliente))

    [(_, _, _, edad_dias, sexo)] = filas_de_encuentro()
    assert (edad_dias, sexo) == (None, None)


def test_paciente_inexistente_da_404():
    respuesta = abrir(uuid4())

    assert respuesta.status_code == 404
    assert respuesta.json()["type"] == URL_PROBLEMAS + "recurso-no-encontrado"


def test_segundo_encuentro_abierto_da_409():
    paciente_id = registrar_paciente(cliente)
    primero = abrir_encuentro(cliente, paciente_id)

    respuesta = abrir(paciente_id)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == URL_PROBLEMAS + "encuentro-abierto"
    assert respuesta.json()["encuentroId"] == str(primero)


def test_misma_clave_mismo_cuerpo_devuelve_el_original():
    paciente_id = registrar_paciente(cliente)
    clave = uuid4()

    primera = abrir(paciente_id, clave)
    segunda = abrir(paciente_id, clave)

    assert segunda.status_code == 201
    assert segunda.json() == primera.json()
    assert len(filas_de_encuentro()) == 1


def test_misma_clave_otro_cuerpo_da_409_conflicto_idempotencia():
    clave = uuid4()
    abrir(registrar_paciente(cliente), clave)

    respuesta = abrir(registrar_paciente(cliente), clave)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == URL_PROBLEMAS + "conflicto-idempotencia"


def test_sin_idempotency_key_da_400():
    respuesta = cliente.post("/v1/encuentros", json={"pacienteId": str(uuid4())})

    assert respuesta.status_code == 400
    assert respuesta.json()["type"] == URL_PROBLEMAS + "solicitud-mal-formada"


def test_dos_aperturas_del_mismo_paciente_dejan_un_solo_encuentro():
    # Dos solicitudes casi simultáneas, con claves distintas (p. ej. dos enfermeras): el índice
    # único parcial deja pasar solo una. La otra recibe el encuentro que ya existe.
    paciente_id = registrar_paciente(cliente)
    primero = encuentros.abrir(paciente_id, None, None, uuid4(), "a" * 64, "prueba")

    with pytest.raises(encuentros.EncuentroAbierto) as error:
        encuentros.abrir(paciente_id, None, None, uuid4(), "b" * 64, "prueba")

    assert error.value.encuentro_id == primero.encuentroId
    assert len(filas_de_encuentro()) == 1
