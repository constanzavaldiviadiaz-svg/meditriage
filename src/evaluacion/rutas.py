"""Rutas del módulo de Evaluación: encuentros, datos clínicos y categoría final (HU02, HU03)."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from src.errores import Problema
from src.evaluacion import datos_clinicos, encuentros
from src.evaluacion.modelos import (
    AbrirEncuentroInput,
    DatosClinicos,
    DatosClinicosInput,
    Encuentro,
)
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


# Lo que el contrato exige para evaluar un caso, en el orden en que se informa.
SIGNOS_OBLIGATORIOS = ["presionSistolica", "presionDiastolica", "frecuenciaCardiaca",
                       "temperatura", "saturacionOxigeno"]


def campos_faltantes(datos):
    """Los campos obligatorios que faltan. Un motivo de consulta en blanco cuenta como falta."""
    faltantes = []
    if not (datos.motivoConsulta or "").strip():
        faltantes.append("motivoConsulta")
    signos = datos.signosVitales
    faltantes += [f"signosVitales.{campo}" for campo in SIGNOS_OBLIGATORIOS
                  if signos is None or getattr(signos, campo) is None]
    return faltantes


@router.put("/v1/encuentros/{encuentro_id}/datos-clinicos", response_model=DatosClinicos)
def registrar_datos_clinicos(encuentro_id: UUID, datos: DatosClinicosInput, request: Request):
    # Cuando el código llega aquí, FastAPI ya revisó tipos y rangos (si no, respondió 400).
    encuentro = encuentros.obtener(encuentro_id)
    if encuentro is None:
        raise _no_encontrado("No existe un encuentro con ese encuentroId.")

    faltantes = campos_faltantes(datos)
    if faltantes:
        detalle = (
            "Falta el motivo de consulta. El caso no se envió al motor de evaluación."
            if faltantes == ["motivoConsulta"]
            else "Faltan datos obligatorios. El caso no se envió al motor de evaluación."
        )
        raise Problema("datos-clinicos-incompletos", "Datos clínicos incompletos", 422,
                       detalle, camposFaltantes=faltantes)

    return datos_clinicos.registrar(encuentro, datos, request.state.trace_id)
