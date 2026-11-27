"""Pruebas de las reglas de alerta de signos vitales (HU02).

Los umbrales vienen del manual ESI (zona de peligro de signos vitales) y del diseño del #122.
No necesitan base de datos: calcular_alertas es una función pura.
"""

import pytest

from src.evaluacion.alertas import Alerta, calcular_alertas

ADULTO = 30 * 365


def signos(**cambios):
    normales = {
        "presionSistolica": 120,
        "presionDiastolica": 80,
        "frecuenciaCardiaca": 80,
        "frecuenciaRespiratoria": 16,
        "temperatura": 36.8,
        "saturacionOxigeno": 98,
    }
    return normales | cambios


def niveles(alertas):
    return {a.signo: a.nivel for a in alertas}


def test_saturacion_85_es_critica():
    # Escenario de HU02: SatO2 de 85 %.
    assert calcular_alertas(signos(saturacionOxigeno=85), ADULTO) == [
        Alerta(signo="saturacion_oxigeno", valor="85", nivel="critico", umbral="SatO2 < 90")
    ]


def test_signos_normales_no_alertan():
    assert calcular_alertas(signos(), ADULTO) == []


@pytest.mark.parametrize("edad_dias, limite", [(30, 180), (400, 160), (2000, 140), (5000, 100)])
def test_fc_por_tramo_de_edad(edad_dias, limite):
    assert calcular_alertas(signos(frecuenciaCardiaca=limite), edad_dias) == []
    alertas = calcular_alertas(signos(frecuenciaCardiaca=limite + 1), edad_dias)
    assert niveles(alertas) == {"frecuencia_cardiaca": "advertencia"}


@pytest.mark.parametrize("edad_dias, limite", [(30, 50), (400, 40), (2000, 30), (5000, 20)])
def test_fr_por_tramo_de_edad(edad_dias, limite):
    assert calcular_alertas(signos(frecuenciaRespiratoria=limite), edad_dias) == []
    alertas = calcular_alertas(signos(frecuenciaRespiratoria=limite + 1), edad_dias)
    assert niveles(alertas) == {"frecuencia_respiratoria": "advertencia"}


def test_los_bordes_de_los_tramos_de_edad():
    # 89 días todavía es "< 3 meses"; 90 ya es "3 meses a 3 años".
    assert calcular_alertas(signos(frecuenciaCardiaca=170), 89) == []
    assert niveles(calcular_alertas(signos(frecuenciaCardiaca=170), 90)) == {
        "frecuencia_cardiaca": "advertencia"
    }


def test_sin_edad_usa_umbrales_de_adulto():
    assert niveles(calcular_alertas(signos(frecuenciaCardiaca=101), None)) == {
        "frecuencia_cardiaca": "advertencia"
    }
    assert niveles(calcular_alertas(signos(frecuenciaCardiaca=151), None)) == {
        "frecuencia_cardiaca": "critico"
    }
    assert niveles(calcular_alertas(signos(presionSistolica=85), None)) == {
        "presion_arterial": "critico"
    }


def test_pas_baja_es_critica_solo_en_adultos():
    assert calcular_alertas(signos(presionSistolica=85), 3000) == []
    assert niveles(calcular_alertas(signos(presionSistolica=85), ADULTO)) == {
        "presion_arterial": "critico"
    }


def test_fc_extrema_es_critica_solo_en_adultos():
    # A los 30 días, 181 lpm es advertencia, no crítico: el criterio crítico de FC es de adultos.
    assert niveles(calcular_alertas(signos(frecuenciaCardiaca=181), 30)) == {
        "frecuencia_cardiaca": "advertencia"
    }
    assert niveles(calcular_alertas(signos(frecuenciaCardiaca=39), ADULTO)) == {
        "frecuencia_cardiaca": "critico"
    }


def test_critico_gana_a_advertencia():
    # 89 % cumple "< 92" (advertencia) y "< 90" (crítico): queda una sola alerta, crítica.
    alertas = calcular_alertas(signos(saturacionOxigeno=89), ADULTO)
    assert [(a.signo, a.nivel) for a in alertas] == [("saturacion_oxigeno", "critico")]


@pytest.mark.parametrize("temperatura, nivel", [(37.9, None), (38.0, "advertencia"),
                                                (39.9, "advertencia"), (40.0, "critico"),
                                                (35.0, None), (34.9, "critico")])
def test_temperatura(temperatura, nivel):
    alertas = calcular_alertas(signos(temperatura=temperatura), ADULTO)
    assert niveles(alertas).get("temperatura") == nivel


def test_presion_alta_es_advertencia_y_muestra_las_dos_cifras():
    [alerta] = calcular_alertas(signos(presionSistolica=185, presionDiastolica=115), ADULTO)
    assert (alerta.signo, alerta.valor, alerta.nivel) == ("presion_arterial", "185/115",
                                                          "advertencia")
    assert niveles(calcular_alertas(signos(presionDiastolica=110), ADULTO)) == {
        "presion_arterial": "advertencia"
    }


def test_sin_frecuencia_respiratoria_no_alerta_por_ella():
    sin_fr = signos()
    del sin_fr["frecuenciaRespiratoria"]
    assert calcular_alertas(sin_fr, 30) == []


def test_cada_alerta_dice_el_umbral_que_la_disparo():
    [alerta] = calcular_alertas(signos(frecuenciaCardiaca=161), 400)
    assert alerta.umbral == "FC > 160 (3 meses a 3 años)"
