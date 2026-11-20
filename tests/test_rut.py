"""Pruebas de la validación y el enmascaramiento del RUT."""

from src.registro.rut import calcular_digito_verificador, enmascarar_rut, es_rut_valido


def test_digito_verificador_numerico():
    assert calcular_digito_verificador("12345678") == "5"


def test_digito_verificador_cero():
    # Cuando 11 - resto da 11, el dígito es 0.
    assert calcular_digito_verificador("10000004") == "0"


def test_digito_verificador_k():
    # Cuando 11 - resto da 10, el dígito es K.
    assert calcular_digito_verificador("10000013") == "K"


def test_rut_valido():
    assert es_rut_valido("12345678-5")


def test_rut_con_digito_incorrecto():
    assert not es_rut_valido("12345678-0")


def test_rut_con_k_minuscula():
    assert es_rut_valido("10000013-k")


def test_enmascarar_rut_de_8_digitos():
    assert enmascarar_rut("12345678-5") == "12.***.***-5"


def test_enmascarar_rut_de_7_digitos():
    assert enmascarar_rut("1234567-4") == "1.***.***-4"
