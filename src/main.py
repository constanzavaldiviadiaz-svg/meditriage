"""Punto de entrada de MediTriage.

Arma la aplicación y la pone a escuchar. Se ejecuta con:

    python -m src.main
"""

from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request

from src import config
from src.errores import registrar_manejadores
from src.registro.rutas import router as rutas_registro

app = FastAPI(title="MediTriage API", version="1.0.0")

registrar_manejadores(app)
app.include_router(rutas_registro)


@app.middleware("http")
async def agregar_trace_id(request: Request, siguiente):
    """Le pone un trace_id a cada solicitud.

    Si el cliente ya trae uno en la cabecera X-Trace-Id, se respeta; si no, se genera.
    Sirve para seguir una solicitud a través de los logs (factor XI del 12-Factor).
    """
    request.state.trace_id = request.headers.get("X-Trace-Id") or uuid4().hex[:12]
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

    PENDIENTE: cuando exista la base de datos, revisar aquí que haya conexión.
    """
    return {"estado": "listo", "ambiente": config.AMBIENTE}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.PUERTO)
