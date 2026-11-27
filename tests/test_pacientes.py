"""Pruebas de POST /v1/pacientes, de las sondas de salud y de la persistencia.

Cada prueba corresponde a un escenario de docs/scenarios/hu01.feature o a una regla del
contrato api/openapi.yaml.
"""

from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src import bd
from src.main import app
from src.registro import almacen
from tests.conftest import BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)

URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


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


def test_ready_responde_503_si_no_hay_base_de_datos(monkeypatch):
    # Un puerto donde no escucha nadie: la base no está disponible.
    monkeypatch.setenv("BASE_DATOS_URL", "postgresql://nadie@127.0.0.1:1/nada?connect_timeout=1")
    bd.cerrar()
    try:
        respuesta = cliente.get("/ready")
    finally:
        monkeypatch.undo()
        bd.cerrar()

    assert respuesta.status_code == 503
    assert respuesta.json()["type"] == URL_PROBLEMAS + "servicio-no-disponible"


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


def test_un_trace_id_demasiado_largo_se_reemplaza():
    # Viene del cliente y termina guardado en la auditoría, en una columna de 64 caracteres.
    # Uno inválido no se recorta: se reemplaza por uno generado (#148).
    respuesta = cliente.get("/health", headers={"X-Trace-Id": "x" * 500})
    trace_id = respuesta.headers["X-Trace-Id"]
    assert trace_id != "x" * 64
    assert len(trace_id) <= 64


# --- Persistencia -----------------------------------------------------------------------


def test_el_paciente_queda_guardado_en_postgresql():
    paciente = registrar(un_paciente()).json()

    with admin(BASE_PRINCIPAL) as conexion:
        fila = conexion.execute(
            "SELECT p.rut, c.estado FROM identidad.paciente p"
            " JOIN identidad.consentimiento c USING (paciente_id) WHERE paciente_id = %s",
            (paciente["pacienteId"],),
        ).fetchone()
    assert fila == ("12345678-5", "otorgado")


def test_los_pacientes_sobreviven_a_un_reinicio():
    primero = registrar(un_paciente()).json()
    bd.cerrar()  # como al reiniciar el pod: se pierden todas las conexiones

    respuesta = registrar(un_paciente())

    assert respuesta.status_code == 409
    assert respuesta.json()["pacienteId"] == primero["pacienteId"]


def test_la_idempotencia_sobrevive_a_un_reinicio():
    clave = uuid4()
    primera = registrar(un_paciente(), clave)
    bd.cerrar()

    segunda = registrar(un_paciente(), clave)

    assert segunda.status_code == 201
    assert segunda.json() == primera.json()


def test_dos_registros_simultaneos_del_mismo_rut(monkeypatch):
    primero = registrar(un_paciente()).json()
    # Otra réplica registró el mismo RUT entre la revisión y el guardado: la revisión no lo
    # ve, pero la base lo rechaza por la restricción UNIQUE.
    from src.registro import almacen

    buscar = almacen.buscar_id_por_rut
    llamadas = []

    def no_lo_ve_la_primera_vez(rut):
        llamadas.append(rut)
        return None if len(llamadas) == 1 else buscar(rut)

    monkeypatch.setattr(almacen, "buscar_id_por_rut", no_lo_ve_la_primera_vez)

    respuesta = registrar(un_paciente())

    assert respuesta.status_code == 409
    assert respuesta.json()["pacienteId"] == primero["pacienteId"]


def test_la_clave_de_idempotencia_no_guarda_el_rut_ni_el_nombre():
    registrar(un_paciente())

    with admin(BASE_PRINCIPAL) as conexion:
        fila = conexion.execute("SELECT * FROM identidad.solicitud_registro").fetchone()
    assert "12345678" not in str(fila)
    assert "Paciente de Prueba" not in str(fila)


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


# --- Sexo y datos para el triage (#122) -------------------------------------------------


def test_registra_el_sexo():
    cuerpo = un_paciente() | {"sexo": "femenino"}
    respuesta = registrar(cuerpo)

    assert respuesta.status_code == 201
    datos = almacen.datos_para_triage(UUID(respuesta.json()["pacienteId"]))
    assert datos.sexo == "femenino"


def test_sexo_desconocido_da_400():
    respuesta = registrar(un_paciente() | {"sexo": "x"})

    assert respuesta.status_code == 400
    assert respuesta.json()["type"] == URL_PROBLEMAS + "solicitud-mal-formada"


def test_datos_para_triage_traen_la_fecha_de_nacimiento_y_no_identifican():
    cuerpo = un_paciente() | {"fechaNacimiento": "1990-05-01"}
    paciente_id = UUID(registrar(cuerpo).json()["pacienteId"])

    datos = almacen.datos_para_triage(paciente_id)
    assert datos.fecha_nacimiento == date(1990, 5, 1)
    assert datos.sexo is None
    assert "12345678" not in repr(datos)
    assert "Paciente de Prueba" not in repr(datos)


def test_datos_para_triage_de_paciente_inexistente_es_none():
    assert almacen.datos_para_triage(uuid4()) is None


def test_nombres_por_id_devuelve_solo_los_pedidos():
    uno = UUID(registrar(un_paciente(rut="12345678-5")).json()["pacienteId"])
    registrar(un_paciente(rut="11111111-1"))

    assert almacen.nombres_por_id([uno]) == {uno: "Paciente de Prueba"}
    assert almacen.nombres_por_id([]) == {}
