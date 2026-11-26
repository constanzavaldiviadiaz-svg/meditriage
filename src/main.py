"""Punto de entrada de MediTriage.

Arma la aplicación y la pone a escuchar. Se ejecuta con:

    python -m src.main
"""

from contextlib import asynccontextmanager
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request

from src import bd, config
from src.errores import Problema, registrar_manejadores
from src.registro.rutas import router as rutas_registro

# Largo máximo del trace_id: el mismo de la columna en la outbox y en la auditoría.
LARGO_TRACE_ID = 64


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


@app.middleware("http")
async def agregar_trace_id(request: Request, siguiente):
    """Le pone un trace_id a cada solicitud.

    Si el cliente ya trae uno en la cabecera X-Trace-Id, se respeta; si no, se genera.
    Sirve para seguir una solicitud a través de los logs (factor XI del 12-Factor).
    Se recorta a 64 caracteres: viene del cliente y termina guardado en la auditoría.
    """
    trace_id = request.headers.get("X-Trace-Id") or uuid4().hex[:12]
    request.state.trace_id = trace_id[:LARGO_TRACE_ID]
    respuesta = await siguiente(request)
    respuesta.headers["X-Trace-Id"] = request.state.trace_id
    return respuesta


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
    uvicorn.run(app, host="0.0.0.0", port=config.PUERTO)
