"""Rutas del módulo de Evaluación: encuentros, datos clínicos, evaluación con IA y categoría
final (HU02, HU03, HU06)."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from src import config
from src.errores import Problema
from src.evaluacion import confirmacion, datos_clinicos, encuentros, evaluaciones, servicio
from src.evaluacion.modelos import (
    AbrirEncuentroInput,
    CategoriaFinal,
    ConfirmacionInput,
    DatosClinicos,
    DatosClinicosInput,
    DerivacionManual,
    Encuentro,
    SugerenciaIa,
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


@router.post("/v1/encuentros/{encuentro_id}/evaluaciones", status_code=201,
             response_model=SugerenciaIa | DerivacionManual)
def solicitar_evaluacion(
    encuentro_id: UUID,
    request: Request,
    response: Response,
    clave: UUID = Header(alias="Idempotency-Key"),
):
    # 1. Idempotencia: la misma clave devuelve la misma evaluación, sin volver a llamar a la IA.
    anterior = evaluaciones.buscar_por_clave(clave)
    if anterior:
        encuentro_anterior, evaluacion_id = anterior
        if encuentro_anterior != encuentro_id:
            raise Problema("conflicto-idempotencia", "Conflicto de idempotencia", 409,
                           "La clave ya se usó para evaluar otro encuentro.")
        evaluacion = evaluaciones.obtener(evaluacion_id)
    else:
        evaluacion = _evaluar(encuentro_id, request.state.trace_id)
        evaluaciones.recordar_clave(clave, encuentro_id, evaluacion.evaluacionId)

    response.headers["Location"] = (
        f"/v1/encuentros/{encuentro_id}/evaluaciones/{evaluacion.evaluacionId}")
    return evaluacion


def _evaluar(encuentro_id, trace_id):
    encuentro = encuentros.obtener(encuentro_id)
    if encuentro is None:
        raise _no_encontrado("No existe un encuentro con ese encuentroId.")
    if encuentro.estado == "abierto":
        raise Problema("datos-clinicos-incompletos", "Datos clínicos incompletos", 422,
                       "El encuentro no tiene datos clínicos. El caso no se envió al motor de"
                       " evaluación.")
    if encuentro.estado in ("confirmado", "atendido"):
        # La enfermera ya decidió: una evaluación nueva no cambia esa decisión.
        raise Problema("encuentro-confirmado", "Encuentro confirmado", 409,
                       "La categoría final ya fue confirmada.")
    return servicio.evaluar(encuentro, trace_id)


# Estados desde los que se puede fijar la categoría: hay una evaluación vigente. Si después de
# evaluar se registraron datos clínicos nuevos, el encuentro volvió a "en_espera" y la
# evaluación anterior ya no corresponde a lo medido.
ESTADOS_CON_EVALUACION = {"evaluado", "derivado_triage_manual", "confirmado"}


@router.put("/v1/encuentros/{encuentro_id}/categoria-final", response_model=CategoriaFinal)
def confirmar_categoria(
    encuentro_id: UUID,
    datos: ConfirmacionInput,
    request: Request,
    # Quién confirma, mientras no haya autenticación (#103). Solo se acepta en desarrollo: en
    # cualquier otro ambiente se ignora, porque cualquiera podría escribirla. No es parte del
    # contrato (api/openapi.yaml); aparece en /docs para la demo.
    usuario: str | None = Header(default=None, alias="X-Usuario", pattern=r"^[a-z0-9-]{1,64}$",
                                 description="Solo en desarrollo: referencia opaca a quien "
                                             "confirma, p. ej. enfermera-demo-1."),
):
    encuentro = encuentros.obtener(encuentro_id)
    if encuentro is None:
        raise _no_encontrado("No existe un encuentro con ese encuentroId.")

    evaluacion = evaluaciones.ultima(encuentro_id)
    if encuentro.estado not in ESTADOS_CON_EVALUACION or evaluacion is None:
        raise Problema("encuentro-sin-evaluacion", "Encuentro sin evaluación", 409,
                       "El encuentro no tiene una evaluación vigente para sus datos clínicos.")

    origen = confirmacion.decidir_origen(evaluacion, datos.categoriaEsi)
    sin_motivo = not (datos.justificacionCambio or "").strip()
    if origen == "modificada_por_enfermera" and sin_motivo:
        raise Problema("justificacion-requerida", "Justificación requerida", 422,
                       "La categoría final difiere de la sugerida y no se indicó el motivo.")

    confirmada_por = usuario if config.AMBIENTE == "desarrollo" else None
    return confirmacion.confirmar(encuentro, evaluacion, datos, origen, confirmada_por,
                                  request.state.trace_id)
