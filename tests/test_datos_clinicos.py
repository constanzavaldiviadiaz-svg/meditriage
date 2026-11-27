"""Pruebas de PUT /v1/encuentros/{id}/datos-clinicos (HU02): signos vitales, síntomas y alertas."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app
from tests.ayudantes import (
    SIGNOS_NORMALES,
    abrir_encuentro,
    datos_clinicos,
    registrar_datos,
    registrar_paciente,
)
from tests.conftest import BASE_PRINCIPAL, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)
URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


def nuevo_encuentro(**datos_del_paciente):
    return abrir_encuentro(cliente, registrar_paciente(cliente, **datos_del_paciente))


def enviar(encuentro_id, cuerpo):
    return cliente.put(f"/v1/encuentros/{encuentro_id}/datos-clinicos", json=cuerpo)


def consultar(sql, *parametros):
    with admin(BASE_PRINCIPAL) as conexion:
        return conexion.execute(sql, parametros).fetchall()


def eventos(tipo):
    return [payload for (payload,) in consultar(
        "SELECT payload FROM clinico.outbox_evento WHERE tipo = %s ORDER BY creado_en", tipo)]


def test_saturacion_85_responde_alerta_critica():
    # Escenario de HU02: la enfermera registra una saturación de 85 %.
    encuentro_id = nuevo_encuentro()

    respuesta = enviar(encuentro_id, datos_clinicos(saturacionOxigeno=85))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["encuentroId"] == str(encuentro_id)
    assert cuerpo["alertas"] == [
        {"signo": "saturacion_oxigeno", "valor": "85", "nivel": "critico"}
    ]


def test_pasa_el_encuentro_a_en_espera():
    encuentro_id = nuevo_encuentro()

    registrar_datos(cliente, encuentro_id)

    [(estado, motivo)] = consultar(
        "SELECT estado, motivo_consulta FROM clinico.encuentro WHERE encuentro_id = %s",
        encuentro_id)
    assert (estado, motivo) == ("en_espera", "Dolor torácico")


def test_sin_motivo_da_422_con_campos_faltantes():
    cuerpo = datos_clinicos()
    del cuerpo["motivoConsulta"]

    respuesta = enviar(nuevo_encuentro(), cuerpo)

    assert respuesta.status_code == 422
    problema = respuesta.json()
    assert problema["type"] == URL_PROBLEMAS + "datos-clinicos-incompletos"
    assert problema["camposFaltantes"] == ["motivoConsulta"]
    assert problema["detail"] == (
        "Falta el motivo de consulta. El caso no se envió al motor de evaluación.")


def test_motivo_en_blanco_cuenta_como_faltante():
    respuesta = enviar(nuevo_encuentro(), datos_clinicos(motivo="   "))

    assert respuesta.status_code == 422
    assert respuesta.json()["camposFaltantes"] == ["motivoConsulta"]


def test_falta_un_signo_obligatorio():
    cuerpo = datos_clinicos()
    del cuerpo["signosVitales"]["saturacionOxigeno"]

    respuesta = enviar(nuevo_encuentro(), cuerpo)

    assert respuesta.status_code == 422
    assert respuesta.json()["camposFaltantes"] == ["signosVitales.saturacionOxigeno"]


def test_sin_signos_vitales_faltan_los_cinco_obligatorios():
    cuerpo = datos_clinicos()
    del cuerpo["signosVitales"]

    respuesta = enviar(nuevo_encuentro(), cuerpo)

    assert respuesta.json()["camposFaltantes"] == [
        "signosVitales.presionSistolica",
        "signosVitales.presionDiastolica",
        "signosVitales.frecuenciaCardiaca",
        "signosVitales.temperatura",
        "signosVitales.saturacionOxigeno",
    ]


def test_la_frecuencia_respiratoria_es_opcional():
    cuerpo = datos_clinicos()
    del cuerpo["signosVitales"]["frecuenciaRespiratoria"]

    assert enviar(nuevo_encuentro(), cuerpo).status_code == 200


def test_fuera_de_rango_da_400():
    respuesta = enviar(nuevo_encuentro(), datos_clinicos(saturacionOxigeno=30))

    assert respuesta.status_code == 400
    assert respuesta.json()["type"] == URL_PROBLEMAS + "solicitud-mal-formada"


def test_encuentro_inexistente_da_404():
    respuesta = enviar(uuid4(), datos_clinicos())

    assert respuesta.status_code == 404
    assert respuesta.json()["type"] == URL_PROBLEMAS + "recurso-no-encontrado"


def test_cada_put_agrega_una_medicion_y_reemplaza_los_sintomas():
    encuentro_id = nuevo_encuentro()
    enviar(encuentro_id, datos_clinicos(sintomas=["fiebre", "tos"]))
    enviar(encuentro_id, datos_clinicos(sintomas=["disnea"], saturacionOxigeno=91))

    [(mediciones,)] = consultar(
        "SELECT count(*) FROM clinico.signos_vitales WHERE encuentro_id = %s", encuentro_id)
    sintomas = consultar(
        "SELECT descripcion FROM clinico.sintoma WHERE encuentro_id = %s", encuentro_id)
    assert mediciones == 2
    assert sintomas == [("disnea",)]


def test_cada_alerta_guarda_el_umbral_aplicado():
    registrar_datos(cliente, nuevo_encuentro(), saturacionOxigeno=85)

    assert consultar("SELECT signo, nivel, umbral FROM clinico.alerta_signo_vital") == [
        ("saturacion_oxigeno", "critico", "SatO2 < 90")
    ]


def test_las_alertas_usan_la_edad_del_encuentro():
    # 170 lpm: normal para un recién nacido (límite 180), crítico para un adulto (> 150).
    hace_30_dias = (datetime.now(UTC) - timedelta(days=30)).date().isoformat()
    bebe = nuevo_encuentro(fechaNacimiento=hace_30_dias)
    adulto = nuevo_encuentro(fechaNacimiento="1980-01-01")

    assert registrar_datos(cliente, bebe, frecuenciaCardiaca=170)["alertas"] == []
    assert registrar_datos(cliente, adulto, frecuenciaCardiaca=170)["alertas"] == [
        {"signo": "frecuencia_cardiaca", "valor": "170", "nivel": "critico"}
    ]


def test_eventos_sin_texto_libre():
    encuentro_id = nuevo_encuentro()
    registrar_datos(cliente, encuentro_id, saturacionOxigeno=85)

    [capturados] = eventos("vitals.captured")
    [reportados] = eventos("symptoms.reported")
    [critico] = eventos("vitals.critical_detected")
    assert capturados["encuentroId"] == str(encuentro_id)
    assert {"signosVitalesId", "medidoEn"} <= set(capturados)
    # El texto de los síntomas no viaja en el evento: podría traer datos personales.
    assert reportados == {"encuentroId": str(encuentro_id), "cantidadSintomas": 1}
    assert critico == {"encuentroId": str(encuentro_id), "signo": "saturacion_oxigeno",
                       "nivel": "critico", "umbralAplicado": "SatO2 < 90"}


def test_las_advertencias_no_emiten_vitals_critical_detected():
    registrar_datos(cliente, nuevo_encuentro(), saturacionOxigeno=91)

    assert eventos("vitals.critical_detected") == []


def test_los_signos_se_guardan_tal_cual():
    registrar_datos(cliente, nuevo_encuentro())

    [fila] = consultar(
        "SELECT presion_sistolica, presion_diastolica, frecuencia_cardiaca,"
        " frecuencia_respiratoria, temperatura, saturacion_oxigeno FROM clinico.signos_vitales")
    assert [float(v) for v in fila] == [SIGNOS_NORMALES[c] for c in (
        "presionSistolica", "presionDiastolica", "frecuenciaCardiaca",
        "frecuenciaRespiratoria", "temperatura", "saturacionOxigeno")]
