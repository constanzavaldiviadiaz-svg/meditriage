"""El servicio de evaluación (HU03 y HU06): pide la sugerencia a la IA dentro de los 3 segundos
o deriva a triage manual.

Deriva si:
- el circuito está abierto o la IA falla (servicio_no_disponible);
- la IA no responde a tiempo (timeout);
- la respuesta no termina normalmente o no calza con el esquema (respuesta_invalida, G3).

La derivación no es un error: es el resultado previsto, y la enfermera sigue sin esperar.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from pydantic import BaseModel, Field, ValidationError

from src import config
from src.evaluacion import breaker, datos_clinicos, evaluaciones, motor, prompt, solicitud
from src.evaluacion.modelos import Justificacion


class SalidaIa(BaseModel):
    """Lo que tiene que traer la respuesta de la IA para llegar como sugerencia."""

    categoriaEsi: int = Field(ge=1, le=5)
    justificacion: Justificacion


# Hilos para las llamadas a la IA. Si una se pasa del plazo, la respuesta al cliente no la
# espera; el hilo termina solo cuando el SDK corta la conexión.
_hilos = ThreadPoolExecutor(max_workers=8, thread_name_prefix="motor-ia")


def _con_plazo(funcion, plazo):
    """El resultado de `funcion`, o FallaMotor("timeout") si no termina en `plazo` segundos.

    El SDK aplica su timeout a cada fase de la conexión (conectar, enviar, recibir), no al
    total: con una conexión nueva, la suma puede pasar de 3 s. HU06 exige 3 s en total."""
    futuro = _hilos.submit(funcion)
    try:
        return futuro.result(timeout=plazo)
    except TimeoutError:
        raise motor.FallaMotor("timeout") from None


def _validar(respuesta):
    """La salida de la IA, o None si no sirve como sugerencia (G3)."""
    if respuesta.stop_reason != "end_turn":
        return None
    try:
        return SalidaIa.model_validate(json.loads(respuesta.texto))
    except (ValueError, ValidationError):
        return None


def evaluar(encuentro, trace_id):
    datos = solicitud.construir(datos_clinicos.ultimos(encuentro.encuentro_id))
    inicio = perf_counter()

    def transcurrido():
        return int((perf_counter() - inicio) * 1000)

    def derivar(motivo):
        return evaluaciones.guardar_derivacion(encuentro, motivo, transcurrido(), trace_id)

    if not breaker.circuito.permite():
        return derivar("servicio_no_disponible")
    try:
        sugeridor = motor.obtener()
        respuesta = _con_plazo(lambda: sugeridor.sugerir(datos, config.TIMEOUT_IA),
                               config.TIMEOUT_IA)
    except motor.FallaMotor as falla:
        breaker.circuito.falla()
        return derivar(falla.motivo)
    breaker.circuito.exito()

    salida = _validar(respuesta)
    if salida is None:
        return derivar("respuesta_invalida")
    return evaluaciones.guardar_sugerencia(
        encuentro, salida.categoriaEsi, salida.justificacion, transcurrido(),
        respuesta.modelo, prompt.VERSION_PROMPT, respuesta.texto, trace_id)
