"""Pruebas de la outbox y del relay que lleva los eventos a la auditoría (ADR 0004).

El registro de un paciente y su evento se guardan en la misma transacción. El relay copia
después los eventos pendientes a la base de auditoría, fuera del camino de la solicitud.
"""

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src import bd
from src.auditoria import relay
from src.main import app
from tests.conftest import BASE_AUDITORIA, BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)


def registrar(rut="12345678-5", consentimiento="otorgado"):
    return cliente.post(
        "/v1/pacientes",
        json={
            "rut": rut,
            "nombre": "Paciente de Prueba",
            "consentimiento": {"estado": consentimiento},
        },
        headers={"Idempotency-Key": str(uuid4()), "X-Trace-Id": "traza-prueba"},
    )


def pendientes():
    with admin(BASE_PRINCIPAL) as conexion:
        return conexion.execute(
            "SELECT count(*) FROM clinico.outbox_evento WHERE publicado_en IS NULL"
        ).fetchone()[0]


def auditados():
    with admin(BASE_AUDITORIA) as conexion:
        return conexion.execute(
            "SELECT tipo, aggregate_id, trace_id, payload FROM auditoria.registro"
            " ORDER BY secuencia"
        ).fetchall()


def test_registrar_un_paciente_deja_su_evento_en_la_outbox():
    registrar()

    assert pendientes() == 1
    assert auditados() == []


def test_el_relay_lleva_el_evento_a_la_auditoria():
    paciente = registrar().json()

    assert relay.procesar_pendientes() == 1

    [(tipo, aggregate_id, trace_id, payload)] = auditados()
    assert tipo == "paciente.registrado"
    assert str(aggregate_id) == paciente["pacienteId"]
    assert trace_id == "traza-prueba"
    assert payload["estadoConsentimiento"] == "otorgado"
    assert pendientes() == 0


def test_un_evento_ya_auditado_no_se_vuelve_a_procesar():
    registrar()
    relay.procesar_pendientes()

    assert relay.procesar_pendientes() == 0
    assert len(auditados()) == 1


def test_si_el_relay_falla_tras_auditar_el_reintento_no_duplica():
    registrar()
    relay.procesar_pendientes()
    # Simula que el relay se cayó después de escribir en auditoría y antes de marcar la outbox.
    with admin(BASE_PRINCIPAL) as conexion:
        conexion.execute("UPDATE clinico.outbox_evento SET publicado_en = NULL")

    assert relay.procesar_pendientes() == 1
    assert len(auditados()) == 1


def test_el_evento_no_lleva_el_rut_ni_el_nombre():
    registrar()
    relay.procesar_pendientes()

    [(_, _, _, payload)] = auditados()
    assert "12345678" not in str(payload)
    assert "Paciente de Prueba" not in str(payload)


def test_un_registro_bloqueado_por_consentimiento_queda_auditado():
    respuesta = registrar(consentimiento="rechazado")
    relay.procesar_pendientes()

    assert respuesta.status_code == 422
    [(tipo, _, _, payload)] = auditados()
    assert tipo == "consentimiento.rechazado"
    assert payload == {"rutEnmascarado": "12.***.***-5"}


def test_el_relay_en_segundo_plano_audita_sin_intervencion():
    registrar()
    en_segundo_plano = relay.Relay(intervalo=0.05)
    en_segundo_plano.iniciar()
    try:
        limite = time.monotonic() + 5
        while pendientes() and time.monotonic() < limite:
            time.sleep(0.05)
    finally:
        en_segundo_plano.detener()

    assert pendientes() == 0
    assert len(auditados()) == 1


def test_si_la_auditoria_no_responde_los_eventos_esperan_en_la_outbox(monkeypatch, caplog):
    registrar()
    monkeypatch.setenv("AUDITORIA_URL", "postgresql://nadie@127.0.0.1:1/nada?connect_timeout=1")
    bd.cerrar()
    en_segundo_plano = relay.Relay(intervalo=0.05)
    try:
        en_segundo_plano.iniciar()
        limite = time.monotonic() + 10
        while "No se pudo auditar" not in caplog.text and time.monotonic() < limite:
            time.sleep(0.05)
    finally:
        en_segundo_plano.detener()
        monkeypatch.undo()
        bd.cerrar()

    assert "No se pudo auditar" in caplog.text
    assert pendientes() == 1
    # Cuando la auditoría vuelve, el evento llega.
    assert relay.procesar_pendientes() == 1
    assert len(auditados()) == 1


def test_la_api_no_necesita_la_credencial_de_auditoria(monkeypatch):
    # Solo el worker escribe en la auditoría. Si alguien compromete la API, no puede
    # insertar registros falsos (amenaza S3 del threat model).
    monkeypatch.delenv("AUDITORIA_URL")
    bd.cerrar()
    try:
        respuesta = registrar()
        lista = cliente.get("/ready")
    finally:
        monkeypatch.undo()
        bd.cerrar()

    assert respuesta.status_code == 201
    assert lista.status_code == 200


def test_el_worker_se_detiene_al_recibir_la_orden():
    worker = relay.Relay(intervalo=0.05)
    worker.iniciar()
    worker.detener()

    assert not worker.corriendo()
