
"""Punto de entrada de MediTriage.

Arma la aplicación y la pone a escuchar. Se ejecuta con:

    python -m src.main
"""

import re
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src import bd, config
from src.errores import Problema, registrar_manejadores
from src.evaluacion.rutas import router as rutas_evaluacion
from src.observabilidad import registrar_solicitud
from src.registro.rutas import router as rutas_registro
from src.tablero.rutas import router as rutas_tablero


@asynccontextmanager
async def ciclo_de_vida(app):
    """Al apagar, cierra las conexiones a la base.

    La API no escribe en la auditoría: deja los eventos en la outbox, y el worker
    (src/auditoria/relay.py) los lleva a la base de auditoría.
    """
    yield
    bd.cerrar()


app = FastAPI(title="MediTriage API", version="1.0.0", lifespan=ciclo_de_vida)

registrar_manejadores(app)
app.include_router(rutas_registro)
app.include_router(rutas_evaluacion)
app.include_router(rutas_tablero)


@app.middleware("http")
async def agregar_trace_id(request: Request, siguiente):
    """Agrega trazabilidad, metricas HTTP y logs estructurados."""

    trace_id = request.headers.get("X-Trace-Id", "")

    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", trace_id):
        trace_id = uuid4().hex[:12]

    request.state.trace_id = trace_id

    trace_id_log = (
        "[REDACTED]"
        if request.headers.get("X-Trace-Id") == trace_id
        else trace_id
    )

    inicio = perf_counter()
    estado = 500

    try:
        respuesta = await siguiente(request)
        estado = respuesta.status_code
        respuesta.headers["X-Trace-Id"] = trace_id
        return respuesta

    finally:
        ruta = request.scope.get("route")
        ruta_normalizada = getattr(ruta, "path", "unknown")

        if ruta_normalizada not in {"/metrics", "/health", "/ready"}:
            registrar_solicitud(
                method=request.method,
                route=ruta_normalizada,
                status=estado,
                duration=perf_counter() - inicio,
                trace_id=trace_id_log,
            )


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expone las metricas en formato Prometheus."""
    return Response(
        content=generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )


@app.get("/health", include_in_schema=False)
def health():
    """¿Está vivo el proceso? Si no responde, Kubernetes reinicia el contenedor."""
    return {"estado": "ok"}


@app.get("/ready", include_in_schema=False)
def ready():
    """¿Está listo para recibir pacientes? Si no, Kubernetes no le envía tráfico.

    Sin la base principal no se puede registrar a nadie, así que la aplicación no está lista.
    """
    if not bd.principal_disponible():
        raise Problema(
            "servicio-no-disponible",
            "Servicio no disponible",
            503,
            "La base de datos no responde.",
        )
    return {"estado": "listo", "ambiente": config.AMBIENTE}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PUERTO,
        access_log=False,
    )
