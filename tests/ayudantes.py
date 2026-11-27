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


SIGNOS_NORMALES = {
    "presionSistolica": 120,
    "presionDiastolica": 80,
    "frecuenciaCardiaca": 80,
    "frecuenciaRespiratoria": 16,
    "temperatura": 36.8,
    "saturacionOxigeno": 98,
}


def datos_clinicos(motivo="Dolor torácico", sintomas=("dolor opresivo",), **signos):
    """Un cuerpo de DatosClinicosInput con signos normales, salvo los que se cambien."""
    return {
        "motivoConsulta": motivo,
        "sintomas": list(sintomas),
        "signosVitales": SIGNOS_NORMALES | signos,
    }


def registrar_datos(cliente, encuentro_id, **signos):
    """Registra datos clínicos para el encuentro y devuelve la respuesta en JSON."""
    respuesta = cliente.put(f"/v1/encuentros/{encuentro_id}/datos-clinicos",
                            json=datos_clinicos(**signos))
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def justificacion_de_prueba():
    from src.evaluacion.modelos import Factor, Justificacion

    return Justificacion(
        resumen="Saturación baja con dificultad respiratoria.",
        factores=[Factor(factor="saturacion_oxigeno", descripcion="85 %, bajo el umbral")],
    )


def evaluar(encuentro_id, categoria=2):
    """Simula la sugerencia del motor de IA (lo que hará el #123) y devuelve su evaluacionId."""
    from src.evaluacion import encuentros, evaluaciones

    sugerencia = evaluaciones.guardar_sugerencia(
        encuentros.obtener(encuentro_id), categoria, justificacion_de_prueba(), 850,
        "modelo-de-prueba", "v1", f'{{"categoria": {categoria}}}', "traza-prueba")
    return sugerencia.evaluacionId


def derivar(encuentro_id, motivo="timeout"):
    """Simula una derivación a triage manual y devuelve su evaluacionId."""
    from src.evaluacion import encuentros, evaluaciones

    derivacion = evaluaciones.guardar_derivacion(
        encuentros.obtener(encuentro_id), motivo, 3000, "traza-prueba")
    return derivacion.evaluacionId
