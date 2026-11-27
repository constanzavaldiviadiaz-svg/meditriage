"""POST /v1/pacientes — Registrar un paciente con su consentimiento informado (HU01)."""

from uuid import UUID

from fastapi import APIRouter, Header, Request, Response

from src.errores import Problema
from src.registro import almacen
from src.registro.modelos import EstadoConsentimiento, Paciente, RegistroPacienteInput
from src.registro.rut import es_rut_valido

router = APIRouter(tags=["Pacientes"])


@router.post("/v1/pacientes", status_code=201, response_model=Paciente)
def registrar_paciente(
    datos: RegistroPacienteInput,
    request: Request,
    response: Response,
    clave: UUID = Header(alias="Idempotency-Key"),
):
    # Cuando el código llega aquí, FastAPI ya revisó que el cuerpo tenga la forma correcta
    # y que venga la cabecera Idempotency-Key. Si no, ya respondió 400.
    try:
        paciente = _registrar(datos, clave, request.state.trace_id)
    except almacen.Duplicado:
        # Otra solicitud (quizás en otra réplica) registró el mismo RUT o usó la misma clave
        # un instante antes. Al repetir las revisiones, ahora sí se encuentra.
        paciente = _registrar(datos, clave, request.state.trace_id)

    response.headers["Location"] = f"/v1/pacientes/{paciente.pacienteId}"
    return paciente


def _registrar(datos, clave, trace_id):
    # 1. Idempotencia: ¿esta solicitud ya se había procesado?
    #    Si la enfermera apretó "enviar" dos veces, no se registra dos veces.
    anterior = almacen.buscar_por_clave(clave)
    if anterior:
        hash_anterior, paciente_anterior = anterior
        if hash_anterior != almacen.hash_cuerpo(datos):
            raise Problema(
                "conflicto-idempotencia",
                "Conflicto de idempotencia",
                409,
                "La clave ya se usó con un cuerpo distinto.",
            )
        return paciente_anterior

    # 2. El dígito verificador debe corresponder al número.
    if not es_rut_valido(datos.rut):
        raise Problema(
            "rut-invalido",
            "RUT inválido",
            422,
            "El dígito verificador no corresponde al número.",
        )

    # 3. Sin consentimiento no hay registro, pero el intento queda en la auditoría.
    rut = datos.rut.upper()
    if datos.consentimiento.estado == EstadoConsentimiento.rechazado:
        almacen.registrar_rechazo(rut, clave, trace_id)
        raise Problema(
            "consentimiento-no-otorgado",
            "Consentimiento no otorgado",
            422,
            "El registro se bloqueó y el intento quedó en el audit log.",
        )

    # 4. Un RUT se registra una sola vez. Se responde con el paciente que ya existe.
    existente = almacen.buscar_id_por_rut(rut)
    if existente:
        raise Problema(
            "paciente-ya-registrado",
            "Paciente ya registrado",
            409,
            pacienteId=str(existente),
        )

    # 5. Todo en orden: se registra.
    return almacen.guardar(datos, rut, clave, trace_id)
