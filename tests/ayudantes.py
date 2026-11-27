"""Ayudantes para armar los casos de las pruebas del flujo clínico.

Solo datos sintéticos: los RUT se generan con un dígito verificador válido y el nombre es
siempre el mismo.
"""

import itertools
from uuid import UUID, uuid4

NOMBRE = "Paciente de Prueba"
_numeros = itertools.count(20_000_001)


def rut_valido(numero):
    """Un RUT sintético con su dígito verificador correcto (módulo 11)."""
    suma = sum(int(d) * f for d, f in zip(reversed(str(numero)), itertools.cycle(range(2, 8))))
    resto = 11 - suma % 11
    dv = {10: "K", 11: "0"}.get(resto, str(resto))
    return f"{numero}-{dv}"


def registrar_paciente(cliente, **cambios):
    """Registra un paciente con consentimiento y devuelve su pacienteId."""
    cuerpo = {
        "rut": rut_valido(next(_numeros)),
        "nombre": NOMBRE,
        "consentimiento": {"estado": "otorgado"},
    } | cambios
    respuesta = cliente.post("/v1/pacientes", json=cuerpo,
                             headers={"Idempotency-Key": str(uuid4())})
    assert respuesta.status_code == 201, respuesta.text
    return UUID(respuesta.json()["pacienteId"])


def abrir_encuentro(cliente, paciente_id):
    """Abre un encuentro para el paciente y devuelve su encuentroId."""
    respuesta = cliente.post("/v1/encuentros", json={"pacienteId": str(paciente_id)},
                             headers={"Idempotency-Key": str(uuid4())})
    assert respuesta.status_code == 201, respuesta.text
    return UUID(respuesta.json()["encuentroId"])
