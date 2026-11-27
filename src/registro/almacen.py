"""Dónde se guardan los pacientes: PostgreSQL, en el contexto de identidad (ADR 0004).

Cada registro guarda, en una sola transacción, el paciente, su consentimiento, la clave de
idempotencia y el evento para la auditoría. O queda todo o no queda nada.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import uuid4

from psycopg import errors

from src import bd
from src.auditoria.eventos import encolar
from src.registro.modelos import ConsentimientoRegistrado, Paciente
from src.registro.rut import enmascarar_rut

_PACIENTE = (
    "SELECT p.paciente_id, p.rut, p.registrado_en, c.estado, c.registrado_en"
    " FROM identidad.paciente p JOIN identidad.consentimiento c USING (paciente_id)"
)


@dataclass(frozen=True)
class DatosParaTriage:
    """Lo que el contexto clínico necesita saber de un paciente: nada que lo identifique."""

    fecha_nacimiento: date | None
    sexo: str | None


class Duplicado(Exception):
    """Otra solicitud registró el mismo RUT o usó la misma clave un instante antes."""


def hash_cuerpo(datos):
    """Hash del cuerpo de la solicitud. Basta para saber si una clave se reusó con otro
    cuerpo, sin guardar el RUT ni el nombre."""
    return hashlib.sha256(datos.model_dump_json().encode()).hexdigest()


def _a_paciente(fila):
    paciente_id, rut, registrado_en, estado, consentido_en = fila
    return Paciente(
        pacienteId=paciente_id,
        rutEnmascarado=enmascarar_rut(rut),
        consentimiento=ConsentimientoRegistrado(
            estado=estado,
            registradoEn=consentido_en.astimezone(UTC),
        ),
        registradoEn=registrado_en.astimezone(UTC),
    )


def buscar_por_clave(clave):
    """La respuesta ya entregada para esta clave de idempotencia, con el hash del cuerpo con
    que se usó. None si la clave es nueva."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT s.hash_cuerpo, p.paciente_id, p.rut, p.registrado_en, c.estado,"
            " c.registrado_en FROM identidad.solicitud_registro s"
            " JOIN identidad.paciente p USING (paciente_id)"
            " JOIN identidad.consentimiento c USING (paciente_id) WHERE s.clave = %s",
            (clave,),
        ).fetchone()
    if fila is None:
        return None
    return fila[0], _a_paciente(fila[1:])


def buscar_id_por_rut(rut):
    """El pacienteId de quien ya tiene este RUT registrado, o None."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT paciente_id FROM identidad.paciente WHERE rut = %s", (rut,)
        ).fetchone()
    return fila[0] if fila else None


def datos_para_triage(paciente_id):
    """La fecha de nacimiento y el sexo del paciente, o None si no existe. Nunca el RUT ni el
    nombre: el contexto clínico no los necesita (ADR 0002)."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT fecha_nacimiento, sexo FROM identidad.paciente WHERE paciente_id = %s",
            (paciente_id,),
        ).fetchone()
    return DatosParaTriage(*fila) if fila else None


def nombres_por_id(ids):
    """El nombre de cada paciente pedido. Solo para mostrarlo en la sala de espera: nunca va a
    un log ni a un evento."""
    if not ids:
        return {}
    with bd.principal() as conexion:
        filas = conexion.execute(
            "SELECT paciente_id, nombre FROM identidad.paciente WHERE paciente_id = ANY(%s)",
            (list(ids),),
        ).fetchall()
    return dict(filas)


def guardar(datos, rut, clave, trace_id):
    """Registra al paciente con su consentimiento y deja el evento en la outbox."""
    paciente_id = uuid4()
    ahora = datetime.now(UTC)
    try:
        with bd.principal() as conexion:
            conexion.execute(
                "INSERT INTO identidad.paciente"
                " (paciente_id, rut, nombre, fecha_nacimiento, sexo, registrado_en)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (paciente_id, rut, datos.nombre, datos.fechaNacimiento,
                 datos.sexo.value if datos.sexo else None, ahora),
            )
            conexion.execute(
                "INSERT INTO identidad.consentimiento"
                " (paciente_id, estado, observacion, registrado_en) VALUES (%s, %s, %s, %s)",
                (paciente_id, datos.consentimiento.estado.value,
                 datos.consentimiento.observacion, ahora),
            )
            conexion.execute(
                "INSERT INTO identidad.solicitud_registro (clave, hash_cuerpo, paciente_id)"
                " VALUES (%s, %s, %s)",
                (clave, hash_cuerpo(datos), paciente_id),
            )
            encolar(conexion, "patient.registered", paciente_id, trace_id,
                    {"pacienteId": str(paciente_id),
                     "consentimiento": datos.consentimiento.estado.value})
            fila = conexion.execute(_PACIENTE + " WHERE paciente_id = %s",
                                    (paciente_id,)).fetchone()
    except errors.UniqueViolation:
        # "from None" descarta el error original: su mensaje trae el RUT repetido, y no debe
        # terminar en un log.
        raise Duplicado from None
    return _a_paciente(fila)


def _registrar_intento(tipo, trace_id, **payload):
    """Deja en la auditoría un intento de registro rechazado.

    No se guarda al paciente ni ningún dato suyo, ni siquiera el RUT enmascarado: el
    catálogo de eventos lo prohíbe. El intento lo identifica un UUID que genera el servidor.
    """
    intento_id = uuid4()
    with bd.principal() as conexion:
        encolar(conexion, tipo, intento_id, trace_id, {"intentoId": str(intento_id), **payload})


def registrar_rechazo(trace_id):
    """Un registro bloqueado porque el paciente rechazó el consentimiento."""
    _registrar_intento("consent.rejected", trace_id)


def registrar_rut_invalido(trace_id):
    """Un registro rechazado porque el dígito verificador no corresponde al número."""
    _registrar_intento("rut.rejected", trace_id, motivo="digito_verificador_invalido")
