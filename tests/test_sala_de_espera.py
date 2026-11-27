"""Pruebas de GET /v1/sala-de-espera (HU04): el tablero del médico jefe de turno."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.tablero import sala
from tests.ayudantes import abrir_encuentro, evaluar, registrar_datos, registrar_paciente
from tests.conftest import BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)


def paciente_confirmado(nombre, categoria):
    """Un paciente que llegó, fue evaluado y tiene categoría final. Devuelve su encuentroId."""
    encuentro_id = abrir_encuentro(cliente, registrar_paciente(cliente, nombre=nombre))
    registrar_datos(cliente, encuentro_id)
    evaluar(encuentro_id, categoria=categoria)
    respuesta = cliente.put(f"/v1/encuentros/{encuentro_id}/categoria-final",
                            json={"categoriaEsi": categoria})
    assert respuesta.status_code == 200, respuesta.text
    return encuentro_id


def test_ordena_por_esi_y_luego_por_llegada():
    # Escenario 1 de HU04: llegan Ana (ESI 3), Beto (ESI 1) y Carla (ESI 3), en ese orden.
    paciente_confirmado("Ana", 3)
    paciente_confirmado("Beto", 1)
    paciente_confirmado("Carla", 3)

    respuesta = cliente.get("/v1/sala-de-espera")

    assert respuesta.status_code == 200
    pacientes = respuesta.json()["pacientes"]
    assert [(p["nombre"], p["categoriaEsi"]) for p in pacientes] == [
        ("Beto", 1), ("Ana", 3), ("Carla", 3)
    ]


def test_no_muestra_encuentros_sin_categoria_final():
    paciente_confirmado("Ana", 2)
    en_espera = abrir_encuentro(cliente, registrar_paciente(cliente, nombre="Sin categoría"))
    registrar_datos(cliente, en_espera)

    pacientes = cliente.get("/v1/sala-de-espera").json()["pacientes"]

    assert [p["nombre"] for p in pacientes] == ["Ana"]


def test_muestra_el_nombre_y_los_minutos_de_espera():
    encuentro_id = paciente_confirmado("Ana", 2)
    with admin(BASE_PRINCIPAL) as conexion:
        [(abierto_en,)] = conexion.execute(
            "SELECT abierto_en FROM clinico.encuentro WHERE encuentro_id = %s", (encuentro_id,)
        ).fetchall()

    resultado = sala.consultar(abierto_en + timedelta(minutes=17, seconds=40))

    [paciente] = resultado.pacientes
    assert (paciente.encuentroId, paciente.nombre, paciente.esperaMinutos) == (
        encuentro_id, "Ana", 17)
    assert paciente.llegadaEn == abierto_en


def test_sala_vacia():
    respuesta = cliente.get("/v1/sala-de-espera")

    assert respuesta.status_code == 200
    assert respuesta.json()["pacientes"] == []
    assert "actualizadaEn" in respuesta.json()
