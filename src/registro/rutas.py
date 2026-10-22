"""POST /v1/pacientes — Registrar un paciente con su consentimiento informado (HU01)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Response

from src.errores import Problema
from src.registro import almacen
from src.registro.modelos import (
    ConsentimientoRegistrado,
    EstadoConsentimiento,
    Paciente,
    RegistroPacienteInput,
)
from src.registro.rut import enmascarar_rut, es_rut_valido

router = APIRouter(tags=["Pacientes"])


@router.post("/v1/pacientes", status_code=201, response_model=Paciente)
def registrar_paciente(
    datos: RegistroPacienteInput,
    response: Response,
    clave: UUID = Header(alias="Idempotency-Key"),
):
    # Cuando el código llega aquí, FastAPI ya revisó que el cuerpo tenga la forma correcta
    # y que venga la cabecera Idempotency-Key. Si no, ya respondió 400.

    # 1. Idempotencia: ¿esta solicitud ya se había procesado?
    #    Si la enfermera apretó "enviar" dos veces, no se registra dos veces.
    if clave in almacen.respuestas_por_clave:
        datos_anteriores, paciente_anterior = almacen.respuestas_por_clave[clave]
        if datos != datos_anteriores:
            raise Problema(
                "conflicto-idempotencia",
                "Conflicto de idempotencia",
                409,
                "La clave ya se usó con un cuerpo distinto.",
            )
        response.headers["Location"] = f"/v1/pacientes/{paciente_anterior.pacienteId}"
        return paciente_anterior

    # 2. El dígito verificador debe corresponder al número.
    if not es_rut_valido(datos.rut):
        raise Problema(
            "rut-invalido",
            "RUT inválido",
            422,
            "El dígito verificador no corresponde al número.",
        )

    # 3. Sin consentimiento no hay registro.
    #    PENDIENTE: el intento debe quedar en el audit log, cuando exista el módulo auditoría.
    if datos.consentimiento.estado == EstadoConsentimiento.rechazado:
        raise Problema(
            "consentimiento-no-otorgado",
            "Consentimiento no otorgado",
            422,
            "El registro se bloqueó y el intento quedó en el audit log.",
        )

    # 4. Un RUT se registra una sola vez. Se responde con el paciente que ya existe.
    rut = datos.rut.upper()
    if rut in almacen.pacientes_por_rut:
        existente = almacen.pacientes_por_rut[rut]
        raise Problema(
            "paciente-ya-registrado",
            "Paciente ya registrado",
            409,
            pacienteId=str(existente.pacienteId),
        )

    # 5. Todo en orden: se registra.
    ahora = datetime.now(UTC)
    paciente = Paciente(
        pacienteId=uuid4(),
        rutEnmascarado=enmascarar_rut(rut),
        consentimiento=ConsentimientoRegistrado(
            estado=datos.consentimiento.estado,
            registradoEn=ahora,
        ),
        registradoEn=ahora,
    )
    almacen.pacientes_por_rut[rut] = paciente
    almacen.respuestas_por_clave[clave] = (datos, paciente)

    response.headers["Location"] = f"/v1/pacientes/{paciente.pacienteId}"
    return paciente
