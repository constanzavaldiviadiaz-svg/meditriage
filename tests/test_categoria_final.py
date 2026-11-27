"""Pruebas de PUT /v1/encuentros/{id}/categoria-final (HU03): la enfermera decide.

La IA sugiere y la enfermera confirma o cambia la categoría. Un cambio exige justificación, y
la auditoría registra quién confirmó (amenaza R1 del threat model).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src import config
from src.main import app
from tests.ayudantes import (
    abrir_encuentro,
    derivar,
    evaluar,
    registrar_datos,
    registrar_paciente,
)
from tests.conftest import BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)
URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


def encuentro_en_espera():
    encuentro_id = abrir_encuentro(cliente, registrar_paciente(cliente))
    registrar_datos(cliente, encuentro_id, saturacionOxigeno=85)
    return encuentro_id


def confirmar(encuentro_id, categoria, justificacion=None, usuario=None):
    cuerpo = {"categoriaEsi": categoria}
    if justificacion is not None:
        cuerpo["justificacionCambio"] = justificacion
    cabeceras = {"X-Usuario": usuario} if usuario else {}
    return cliente.put(f"/v1/encuentros/{encuentro_id}/categoria-final", json=cuerpo,
                       headers=cabeceras)


def consultar(sql, *parametros):
    with admin(BASE_PRINCIPAL) as conexion:
        return conexion.execute(sql, parametros).fetchall()


def eventos(tipo):
    return [payload for (payload,) in consultar(
        "SELECT payload FROM clinico.outbox_evento WHERE tipo = %s ORDER BY creado_en", tipo)]


def test_confirma_la_sugerencia():
    encuentro_id = encuentro_en_espera()
    evaluacion_id = evaluar(encuentro_id, categoria=2)

    respuesta = confirmar(encuentro_id, 2)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["encuentroId"], cuerpo["categoriaEsi"], cuerpo["origen"]) == (
        str(encuentro_id), 2, "confirmada_sugerencia_ia")
    assert cuerpo["justificacionCambio"] is None
    assert consultar("SELECT estado FROM clinico.encuentro") == [("confirmado",)]
    assert eventos("triage.confirmed") == [{
        "encuentroId": str(encuentro_id), "evaluacionId": str(evaluacion_id),
        "categoriaEsi": 2, "origen": "confirmada_sugerencia_ia", "confirmadaPor": None,
    }]
    assert eventos("triage.category_overridden") == []


def test_modificar_sin_justificacion_da_422():
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id, categoria=2)

    respuesta = confirmar(encuentro_id, 3)

    assert respuesta.status_code == 422
    assert respuesta.json()["type"] == URL_PROBLEMAS + "justificacion-requerida"
    assert respuesta.json()["detail"] == (
        "La categoría final difiere de la sugerida y no se indicó el motivo.")


def test_una_justificacion_en_blanco_no_cuenta():
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id, categoria=2)

    assert confirmar(encuentro_id, 3, justificacion="   ").status_code == 422


def test_modificar_con_justificacion():
    encuentro_id = encuentro_en_espera()
    evaluacion_id = evaluar(encuentro_id, categoria=2)

    respuesta = confirmar(encuentro_id, 3, justificacion="Dolor controlado con analgesia")

    assert respuesta.status_code == 200
    assert respuesta.json()["origen"] == "modificada_por_enfermera"
    assert respuesta.json()["justificacionCambio"] == "Dolor controlado con analgesia"
    assert eventos("triage.category_overridden") == [{
        "encuentroId": str(encuentro_id), "evaluacionId": str(evaluacion_id),
        "categoriaSugerida": 2, "categoriaFinal": 3,
        "justificacionCambio": "Dolor controlado con analgesia", "confirmadaPor": None,
    }]
    [confirmado] = eventos("triage.confirmed")
    assert confirmado["origen"] == "modificada_por_enfermera"


def test_tras_derivacion_es_asignada_triage_manual():
    encuentro_id = encuentro_en_espera()
    derivar(encuentro_id)

    respuesta = confirmar(encuentro_id, 4)

    assert respuesta.status_code == 200
    assert respuesta.json()["origen"] == "asignada_triage_manual"
    assert eventos("triage.category_overridden") == []


def test_sin_evaluacion_da_409():
    respuesta = confirmar(encuentro_en_espera(), 2)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == URL_PROBLEMAS + "encuentro-sin-evaluacion"


def test_encuentro_inexistente_da_404():
    respuesta = confirmar(uuid4(), 2)

    assert respuesta.status_code == 404
    assert respuesta.json()["type"] == URL_PROBLEMAS + "recurso-no-encontrado"


def test_categoria_fuera_de_rango_da_400():
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id)

    assert confirmar(encuentro_id, 6).status_code == 400


def test_datos_nuevos_tras_evaluar_impiden_confirmar():
    # La enfermera vuelve a medir después de la evaluación: la sugerencia ya no corresponde a
    # los datos actuales, y no se puede confirmar hasta evaluar de nuevo.
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id, categoria=2)
    registrar_datos(cliente, encuentro_id, saturacionOxigeno=97)

    respuesta = confirmar(encuentro_id, 2)

    assert respuesta.status_code == 409
    assert respuesta.json()["type"] == URL_PROBLEMAS + "encuentro-sin-evaluacion"


def test_reconfirmar_reemplaza_la_categoria():
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id, categoria=2)
    confirmar(encuentro_id, 2)

    respuesta = confirmar(encuentro_id, 1, justificacion="Empeoró en la sala de espera")

    assert respuesta.status_code == 200
    assert consultar("SELECT categoria_esi, origen FROM clinico.categoria_final") == [
        (1, "modificada_por_enfermera")
    ]


def test_x_usuario_en_desarrollo_queda_registrado():
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id, categoria=2)

    confirmar(encuentro_id, 2, usuario="enfermera-demo-1")

    [confirmado] = eventos("triage.confirmed")
    assert confirmado["confirmadaPor"] == "enfermera-demo-1"
    assert consultar("SELECT confirmada_por FROM clinico.categoria_final") == [
        ("enfermera-demo-1",)
    ]


def test_x_usuario_fuera_de_desarrollo_se_ignora(monkeypatch):
    # Sin autenticación (#103), cualquiera podría escribir la cabecera. Solo se acepta en
    # desarrollo, para la demo; en producción quien confirma saldrá del token.
    monkeypatch.setattr(config, "AMBIENTE", "produccion")
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id, categoria=2)

    confirmar(encuentro_id, 2, usuario="enfermera-demo-1")

    [confirmado] = eventos("triage.confirmed")
    assert confirmado["confirmadaPor"] is None


def test_x_usuario_invalido_da_400():
    # Solo una referencia opaca: minúsculas, dígitos y guiones. Nunca un nombre ni un RUT.
    encuentro_id = encuentro_en_espera()
    evaluar(encuentro_id)

    assert confirmar(encuentro_id, 2, usuario="Ana Perez").status_code == 400
