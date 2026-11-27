
"""Punto de entrada de MediTriage.

Arma la aplicación y la pone a escuchar. Se ejecuta con:

    python -m src.main
"""

import re
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src import config
from src.errores import registrar_manejadores
from src.observabilidad import registrar_solicitud
from src.registro.rutas import router as rutas_registro

app = FastAPI(title="MediTriage API", version="1.0.0")


@app.middleware("http")
async def cors_abierto(request: Request, call_next):  # PRUEBA #97: debe bloquear el DAST
    respuesta = await call_next(request)
    respuesta.headers["Access-Control-Allow-Origin"] = "*"
    return respuesta

registrar_manejadores(app)
app.include_router(rutas_registro)


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

    PENDIENTE: cuando exista la base de datos, revisar aquí que haya conexión.
    """
    return {"estado": "listo", "ambiente": config.AMBIENTE}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PUERTO,
        access_log=False,
    )
