"""Errores de la API en formato RFC 7807.

Todos los errores de MediTriage tienen la misma forma (ver `Problema` en api/openapi.yaml):

    {
      "type": "https://api.meditriage.example/problemas/rut-invalido",
      "title": "RUT inválido",
      "status": 422,
      "detail": "El dígito verificador no corresponde al número.",
      "trace_id": "c8f2b1e4a9d7"
    }

Para devolver un error, el código lanza `raise Problema(...)`. Los manejadores de este
archivo lo convierten en esa respuesta JSON.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

URL_PROBLEMAS = "https://api.meditriage.example/problemas/"


class Problema(Exception):
    """Un error de la API. Se lanza con `raise` y se responde en formato RFC 7807."""

    def __init__(self, tipo, titulo, status, detalle=None, **extras):
        self.tipo = tipo          # p. ej. "rut-invalido"
        self.titulo = titulo      # p. ej. "RUT inválido"
        self.status = status      # p. ej. 422
        self.detalle = detalle    # explicación del caso puntual (opcional)
        self.extras = extras      # campos adicionales, p. ej. pacienteId


def respuesta_problema(request: Request, problema: Problema) -> JSONResponse:
    """Arma la respuesta JSON de un problema."""
    cuerpo = {
        "type": URL_PROBLEMAS + problema.tipo,
        "title": problema.titulo,
        "status": problema.status,
    }
    if problema.detalle:
        cuerpo["detail"] = problema.detalle
    cuerpo.update(problema.extras)
    cuerpo["trace_id"] = request.state.trace_id

    return JSONResponse(
        status_code=problema.status,
        content=cuerpo,
        media_type="application/problem+json",
    )


def registrar_manejadores(app: FastAPI) -> None:
    """Conecta los manejadores de error a la aplicación."""

    @app.exception_handler(Problema)
    async def manejar_problema(request: Request, problema: Problema):
        return respuesta_problema(request, problema)

    # El cuerpo no cumple el schema: falta un campo, un tipo es incorrecto, etc.
    # FastAPI lo detecta solo; aquí lo traducimos a nuestro formato.
    @app.exception_handler(RequestValidationError)
    async def manejar_solicitud_mal_formada(request: Request, error: RequestValidationError):
        campos = [".".join(str(parte) for parte in e["loc"]) for e in error.errors()]
        problema = Problema(
            "solicitud-mal-formada",
            "Solicitud mal formada",
            400,
            "Hay campos faltantes o con formato incorrecto: " + ", ".join(campos),
        )
        return respuesta_problema(request, problema)

    # Rutas que no existen (404) y otros errores HTTP genéricos.
    @app.exception_handler(HTTPException)
    async def manejar_error_http(request: Request, error: HTTPException):
        if error.status_code == 404:
            problema = Problema("recurso-no-encontrado", "Recurso no encontrado", 404)
        else:
            problema = Problema("error-http", str(error.detail), error.status_code)
        return respuesta_problema(request, problema)
