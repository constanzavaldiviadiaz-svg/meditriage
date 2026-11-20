"""Pruebas de POST /v1/pacientes y de las sondas de salud.

Cada prueba corresponde a un escenario de docs/scenarios/hu01.feature o a una regla del
contrato api/openapi.yaml.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.registro import almacen

cliente = TestClient(app)

URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


@pytest.fixture(autouse=True)
def empezar_de_cero():
    """Cada prueba parte con el almacén vacío."""
    almacen.vaciar()


def un_paciente(rut="12345678-5", consentimiento="otorgado"):
    return {
        "rut": rut,
        "nombre": "Paciente de Prueba",
        "consentimiento": {"estado": consentimiento},
    }


def registrar(cuerpo, clave=None):
    return cliente.post(
        "/v1/pacientes",
        json=cuerpo,
        headers={"Idempotency-Key": str(clave or uuid4())},
    )


# --- Sondas de salud --------------------------------------------------------------------


def test_health():
    assert cliente.get("/health").status_code == 200


def test_ready():
    assert cliente.get("/ready").status_code == 200


# --- Camino feliz -----------------------------------------------------------------------


def test_registro_exitoso():
    respuesta = registrar(un_paciente())

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["rutEnmascarado"] == "12.***.***-5"
    assert cuerpo["consentimiento"]["estado"] == "otorgado"
    assert respuesta.headers["Location"] == f"/v1/pacientes/{cuerpo['pacienteId']}"


def test_la_respuesta_no_expone_el_nombre_ni_el_rut():
    cuerpo = registrar(un_paciente()).json()

    assert "nombre" not in cuerpo
    assert "12345678" not in str(cuerpo)


def test_exencion_por_emergencia_vital():
    respuesta = registrar(un_paciente(consentimiento="exencion_emergencia_vital"))
    assert respuesta.status_code == 201


def test_toda_respuesta_lleva_trace_id():
    assert "X-Trace-Id" in registrar(un_paciente()).headers


def test_se_respeta_el_trace_id_del_cliente():
    respuesta = cliente.get("/health", headers={"X-Trace-Id": "abc123"})
    assert respuesta.headers["X-Trace-Id"] == "abc123"


# --- Reglas del dominio (422) -----------------------------------------------------------


def test_rut_con_digito_verificador_incorrecto():
    respuesta = registrar(un_paciente(rut="12345678-0"))

    assert respuesta.status_code == 422
    assert respuesta.headers["Content-Type"] == "application/problem+json"
    assert respuesta.json()["type"] == URL_PROBLEMAS + "rut-invalido"


def test_consentimiento_rechazado_bloquea_el_registro():
    respuesta = registrar(un_paciente(consentimiento="rechazado"))

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == URL_PROBLEMAS + "consentimiento-no-otorgado"


# --- Conflictos (409) -------------------------------------------------------------------


def test_rut_ya_registrado():
    primero = registrar(un_paciente()).json()
    respuesta = registrar(un_paciente())  # mismo RUT, otra clave de idempotencia

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == URL_PROBLEMAS + "paciente-ya-registrado"
    assert respuesta.json()["pacienteId"] == primero["pacienteId"]


# --- Idempotencia -----------------------------------------------------------------------


def test_misma_clave_y_mismo_cuerpo_devuelve_la_respuesta_original():
    clave = uuid4()
    primera = registrar(un_paciente(), clave)
    segunda = registrar(un_paciente(), clave)

    assert segunda.status_code == 201
    assert segunda.json() == primera.json()


def test_misma_clave_con_otro_cuerpo_es_conflicto():
    clave = uuid4()
    registrar(un_paciente(), clave)
    respuesta = registrar(un_paciente(rut="10000013-K"), clave)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == URL_PROBLEMAS + "conflicto-idempotencia"


# --- Solicitudes mal formadas (400) -----------------------------------------------------


def test_sin_clave_de_idempotencia():
    respuesta = cliente.post("/v1/pacientes", json=un_paciente())

    assert respuesta.status_code == 400
    assert respuesta.json()["type"] == URL_PROBLEMAS + "solicitud-mal-formada"


def test_rut_con_formato_incorrecto():
    respuesta = registrar(un_paciente(rut="12.345.678-5"))  # con puntos: el contrato no los admite
    assert respuesta.status_code == 400


def test_falta_el_consentimiento():
    cuerpo = un_paciente()
    del cuerpo["consentimiento"]

    respuesta = registrar(cuerpo)

    assert respuesta.status_code == 400
    assert "consentimiento" in respuesta.json()["detail"]


# --- Rutas inexistentes -----------------------------------------------------------------


def test_ruta_inexistente_responde_404_en_formato_rfc_7807():
    respuesta = cliente.get("/v1/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["type"] == URL_PROBLEMAS + "recurso-no-encontrado"
    assert "trace_id" in respuesta.json()
