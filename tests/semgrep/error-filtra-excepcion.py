# Casos de prueba de la regla meditriage-error-filtra-excepcion.
# "ruleid" marca una línea que la regla debe detectar; "ok", una que debe dejar pasar.
import logging

from fastapi.responses import JSONResponse

from src.errores import Problema

logger = logging.getLogger(__name__)


def con_mensaje_interno(evaluar):
    try:
        evaluar()
    except TimeoutError as error:
        # ruleid: meditriage-error-filtra-excepcion
        raise Problema("ia-no-disponible", "IA no disponible", 503, str(error)) from error


def con_f_string(evaluar):
    try:
        evaluar()
    except ValueError as e:
        # ruleid: meditriage-error-filtra-excepcion
        return JSONResponse(status_code=500, content={"detail": f"Falló: {e}"})


def correcto(evaluar):
    try:
        evaluar()
    except TimeoutError as error:
        logger.warning("Timeout del servicio de IA: %s", error)
        # ok: meditriage-error-filtra-excepcion
        raise Problema(
            "ia-no-disponible", "IA no disponible", 503, "Se derivó a triage manual."
        ) from error


def con_argumento_con_nombre(evaluar):
    try:
        evaluar()
    except KeyError as error:
        # ruleid: meditriage-error-filtra-excepcion
        raise Problema("error-interno", "Error interno", 500, detalle=repr(error)) from error
