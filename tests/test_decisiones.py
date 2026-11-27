"""Pruebas de GET /v1/auditoria/decisiones y /{decisionId} (HU05).

Una decisión es una evaluación (la sugerencia de la IA o la derivación) más su última
confirmación. Se arma desde la base de auditoría append-only, así que cada prueba deja los
eventos en la outbox y corre el relay antes de consultar.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src import bd
from src.auditoria import relay
from src.main import app
from tests.ayudantes import (
    NOMBRE,
    abrir_encuentro,
    derivar,
    evaluar,
    registrar_datos,
    registrar_paciente,
)
from tests.conftest import BASE_AUDITORIA, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)
URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


def caso(categoria=2, confirmar=True, derivado=False, rut=None):
    """Registra, abre, mide y evalúa (o deriva) un caso, y opcionalmente lo confirma.

    Devuelve (paciente_id, encuentro_id, evaluacion_id)."""
    cambios = {"rut": rut} if rut else {}
    paciente_id = registrar_paciente(cliente, **cambios)
    encuentro_id = abrir_encuentro(cliente, paciente_id)
    registrar_datos(cliente, encuentro_id, saturacionOxigeno=85)
    evaluacion_id = derivar(encuentro_id) if derivado else evaluar(encuentro_id, categoria)
    if confirmar:
        confirmar_categoria(encuentro_id, categoria)
    return paciente_id, encuentro_id, evaluacion_id


def confirmar_categoria(encuentro_id, categoria, justificacion=None):
    cuerpo = {"categoriaEsi": categoria}
    if justificacion:
        cuerpo["justificacionCambio"] = justificacion
    respuesta = cliente.put(f"/v1/encuentros/{encuentro_id}/categoria-final", json=cuerpo,
                            headers={"X-Usuario": "enfermera-demo-1"})
    assert respuesta.status_code == 200, respuesta.text


def hash_del_ultimo(tipo):
    with admin(BASE_AUDITORIA) as conexion:
        return conexion.execute(
            "SELECT hash_integridad FROM auditoria.registro WHERE tipo = %s"
            " ORDER BY secuencia DESC LIMIT 1", (tipo,)).fetchone()[0]


def decisiones(**parametros):
    return cliente.get("/v1/auditoria/decisiones", params=parametros)


def test_una_sugerencia_confirmada_aparece_como_decision():
    paciente_id, encuentro_id, evaluacion_id = caso(categoria=2)
    relay.procesar_pendientes()

    respuesta = decisiones()

    assert respuesta.status_code == 200
    [decision] = respuesta.json()["datos"]
    assert decision["decisionId"] == str(evaluacion_id)
    assert decision["encuentroRef"] == str(encuentro_id)
    assert decision["pacienteRef"] == str(paciente_id)
    assert decision["resultado"] == "sugerencia_ia"
    assert decision["categoriaSugerida"] == 2
    assert decision["justificacion"]["factores"]
    assert decision["motivoDerivacion"] is None
    assert decision["categoriaFinal"] == 2
    assert decision["confirmadaPor"] == "enfermera-demo-1"
    # El hash es el del último registro de la decisión: aquí, su confirmación.
    assert decision["hashIntegridad"] == hash_del_ultimo("triage.confirmed")


def test_una_derivacion_aparece_con_su_motivo():
    _, _, evaluacion_id = caso(derivado=True, confirmar=False)
    relay.procesar_pendientes()

    respuesta = cliente.get(f"/v1/auditoria/decisiones/{evaluacion_id}")

    assert respuesta.status_code == 200
    decision = respuesta.json()
    assert (decision["resultado"], decision["motivoDerivacion"]) == (
        "derivado_triage_manual", "timeout")
    assert decision["categoriaSugerida"] is None
    assert decision["categoriaFinal"] is None
    assert decision["confirmadaPor"] is None
    assert decision["hashIntegridad"] == hash_del_ultimo("triage.derived_to_manual")


def test_una_reconfirmacion_actualiza_la_decision():
    _, encuentro_id, evaluacion_id = caso(categoria=2)
    confirmar_categoria(encuentro_id, 1, justificacion="Empeoró en la sala de espera")
    relay.procesar_pendientes()

    decision = cliente.get(f"/v1/auditoria/decisiones/{evaluacion_id}").json()

    assert decision["categoriaFinal"] == 1
    assert decision["hashIntegridad"] == hash_del_ultimo("triage.confirmed")


def test_una_decision_sin_auditar_todavia_no_aparece():
    caso()

    assert decisiones().json()["datos"] == []


def test_no_lleva_rut_ni_nombre():
    caso(rut="12345678-5")
    relay.procesar_pendientes()

    texto = decisiones().text

    assert "12345678" not in texto
    assert NOMBRE not in texto


def test_mas_recientes_primero_y_pagina_con_cursor():
    ids = [caso()[2] for _ in range(3)]
    relay.procesar_pendientes()

    primera = decisiones(limite=2).json()
    segunda = decisiones(limite=2, cursor=primera["siguienteCursor"]).json()

    assert [d["decisionId"] for d in primera["datos"]] == [str(ids[2]), str(ids[1])]
    assert primera["siguienteCursor"] is not None
    assert [d["decisionId"] for d in segunda["datos"]] == [str(ids[0])]
    assert segunda["siguienteCursor"] is None


def test_filtra_por_rango_de_fechas():
    caso()
    relay.procesar_pendientes()
    ahora = datetime.now(UTC)

    assert len(decisiones(desde=(ahora - timedelta(hours=1)).isoformat()).json()["datos"]) == 1
    assert decisiones(desde=(ahora + timedelta(hours=1)).isoformat()).json()["datos"] == []
    assert decisiones(hasta=(ahora - timedelta(hours=1)).isoformat()).json()["datos"] == []


@pytest.mark.parametrize("cursor", ["%%%", "YWJj", "LTE"])  # basura, "abc" y "-1"
def test_cursor_invalido_da_422(cursor):
    respuesta = decisiones(cursor=cursor)

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == URL_PROBLEMAS + "cursor-invalido"


def test_rango_invalido_da_422():
    momento = datetime.now(UTC).isoformat()

    respuesta = decisiones(desde=momento, hasta=momento)

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == URL_PROBLEMAS + "rango-invalido"


def test_limite_fuera_de_rango_da_400():
    assert decisiones(limite=0).status_code == 400
    assert decisiones(limite=101).status_code == 400


def test_decision_inexistente_da_404():
    respuesta = cliente.get(f"/v1/auditoria/decisiones/{uuid4()}")

    assert respuesta.status_code == 404
    assert respuesta.json()["type"] == URL_PROBLEMAS + "recurso-no-encontrado"


def test_la_api_no_usa_la_credencial_de_escritura(monkeypatch):
    # La API lee la auditoría con el rol de solo lectura. La credencial que puede escribir
    # la tiene solo el worker.
    caso()
    relay.procesar_pendientes()
    monkeypatch.delenv("AUDITORIA_URL")
    bd.cerrar()
    try:
        respuesta = decisiones()
    finally:
        monkeypatch.undo()
        bd.cerrar()

    assert respuesta.status_code == 200
    assert len(respuesta.json()["datos"]) == 1
