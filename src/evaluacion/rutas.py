"""Rutas del módulo de Evaluación: encuentros, datos clínicos y categoría final (HU02, HU03)."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from src.errores import Problema
from src.evaluacion import encuentros
from src.evaluacion.modelos import AbrirEncuentroInput, Encuentro
from src.registro import almacen

router = APIRouter(tags=["Encuentros"])


def _no_encontrado(detalle):
    return Problema("recurso-no-encontrado", "Recurso no encontrado", 404, detalle)


@router.post("/v1/encuentros", status_code=201, response_model=Encuentro)
def abrir_encuentro(
    datos: AbrirEncuentroInput,
    request: Request,
    response: Response,
    clave: UUID = Header(alias="Idempotency-Key"),
):
    try:
        encuentro = _abrir(datos, clave, request.state.trace_id)
    except encuentros.Duplicado:
        # Otra solicitud usó la misma clave un instante antes: al repetir, se encuentra.
        encuentro = _abrir(datos, clave, request.state.trace_id)

    response.headers["Location"] = f"/v1/encuentros/{encuentro.encuentroId}"
    return encuentro


def _abrir(datos, clave, trace_id):
    # 1. Idempotencia: si la enfermera apretó "enviar" dos veces, no se abren dos encuentros.
    anterior = encuentros.buscar_por_clave(clave)
    if anterior:
        hash_anterior, encuentro_anterior = anterior
        if hash_anterior != encuentros.hash_cuerpo(datos):
            raise Problema("conflicto-idempotencia", "Conflicto de idempotencia", 409,
                           "La clave ya se usó con un cuerpo distinto.")
        return encuentro_anterior

    # 2. El paciente tiene que estar registrado.
    paciente = almacen.datos_para_triage(datos.pacienteId)
    if paciente is None:
        raise _no_encontrado("No hay un paciente registrado con ese pacienteId.")

    # 3. Se abre, con la foto de la edad y el sexo. Un paciente no puede tener dos encuentros
    #    sin atender.
    edad_dias = None
    if paciente.fecha_nacimiento:
        edad_dias = (datetime.now(UTC).date() - paciente.fecha_nacimiento).days
    try:
        return encuentros.abrir(datos.pacienteId, edad_dias, paciente.sexo, clave,
                                encuentros.hash_cuerpo(datos), trace_id)
    except encuentros.EncuentroAbierto:
        # El id se busca de nuevo, en vez de tomarlo de la excepción: una respuesta de error
        # nunca se arma con la excepción capturada (regla meditriage-error-filtra-excepcion).
        existente = encuentros.activo(datos.pacienteId)
        raise Problema("encuentro-abierto", "Encuentro abierto", 409,
                       "El paciente ya tiene un encuentro sin atender.",
                       encuentroId=str(existente)) from None
