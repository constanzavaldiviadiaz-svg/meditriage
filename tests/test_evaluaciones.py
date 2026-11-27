"""Pruebas del repositorio de evaluaciones (HU03 y HU06).

La ruta que pide la evaluación al motor de IA llega con el #123. Aquí se prueba lo que ella
va a usar: guardar la sugerencia o la derivación, con su evento, en una transacción.
"""

import pytest
from fastapi.testclient import TestClient

from src.evaluacion import encuentros, evaluaciones
from src.main import app
from tests.ayudantes import (
    abrir_encuentro,
    derivar,
    evaluar,
    justificacion_de_prueba,
    registrar_datos,
    registrar_paciente,
)
from tests.conftest import BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)


def encuentro_listo():
    """Un encuentro con datos clínicos, en espera de la evaluación.

    Devuelve (paciente_id, encuentro_id)."""
    paciente_id = registrar_paciente(cliente)
    encuentro_id = abrir_encuentro(cliente, paciente_id)
    registrar_datos(cliente, encuentro_id, saturacionOxigeno=85)
    return paciente_id, encuentro_id


def consultar(sql, *parametros):
    with admin(BASE_PRINCIPAL) as conexion:
        return conexion.execute(sql, parametros).fetchall()


def estado(encuentro_id):
    [(valor,)] = consultar("SELECT estado FROM clinico.encuentro WHERE encuentro_id = %s",
                           encuentro_id)
    return valor


def evento(tipo):
    [(payload,)] = consultar("SELECT payload FROM clinico.outbox_evento WHERE tipo = %s", tipo)
    return payload


def test_guardar_sugerencia_pasa_a_evaluado_y_encola_triage_completed():
    paciente_id, encuentro_id = encuentro_listo()

    sugerencia = evaluaciones.guardar_sugerencia(
        encuentros.obtener(encuentro_id), 2, justificacion_de_prueba(), 850, "modelo-x", "v1",
        '{"categoria": 2}', "traza")

    assert (sugerencia.resultado, sugerencia.categoriaEsi, sugerencia.duracionMs) == (
        "sugerencia_ia", 2, 850)
    assert estado(encuentro_id) == "evaluado"
    assert evento("triage.completed") == {
        "encuentroId": str(encuentro_id),
        "evaluacionId": str(sugerencia.evaluacionId),
        "pacienteId": str(paciente_id),
        "categoriaEsi": 2,
        "justificacion": justificacion_de_prueba().model_dump(),
        "duracionMs": 850,
    }


def test_guardar_derivacion_pasa_a_derivado_y_encola_triage_derived_to_manual():
    paciente_id, encuentro_id = encuentro_listo()

    derivacion = evaluaciones.guardar_derivacion(
        encuentros.obtener(encuentro_id), "timeout", 3000, "traza")

    assert (derivacion.resultado, derivacion.motivo) == ("derivado_triage_manual", "timeout")
    assert estado(encuentro_id) == "derivado_triage_manual"
    assert evento("triage.derived_to_manual") == {
        "encuentroId": str(encuentro_id),
        "evaluacionId": str(derivacion.evaluacionId),
        "pacienteId": str(paciente_id),
        "motivo": "timeout",
        "duracionMs": 3000,
    }


def test_guarda_la_respuesta_original_y_el_modelo():
    # La IA no es determinista: la auditoría guarda la respuesta exacta (ADR 0002, G5).
    _, encuentro_id = encuentro_listo()
    evaluar(encuentro_id, categoria=3)

    assert consultar(
        "SELECT modelo, version_prompt, respuesta_ia_original, categoria_sugerida"
        " FROM clinico.evaluacion") == [("modelo-de-prueba", "v1", '{"categoria": 3}', 3)]


def test_ultima_devuelve_la_mas_reciente():
    _, encuentro_id = encuentro_listo()
    evaluar(encuentro_id)
    derivacion_id = derivar(encuentro_id)

    ultima = evaluaciones.ultima(encuentro_id)

    assert (ultima.evaluacion_id, ultima.resultado, ultima.categoria_sugerida) == (
        derivacion_id, "derivado_triage_manual", None)


def test_ultima_sin_evaluaciones_es_none():
    _, encuentro_id = encuentro_listo()

    assert evaluaciones.ultima(encuentro_id) is None
