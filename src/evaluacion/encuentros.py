"""Dónde se guardan los encuentros: PostgreSQL, en el contexto clínico (ADR 0004).

Un encuentro es la visita de un paciente, desde que llega a la sala de espera hasta que lo
atienden. Abrirlo no genera un evento: el catálogo (docs/data/event-catalog.md) no lo tiene.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from psycopg import errors

from src import bd
from src.evaluacion.modelos import Encuentro

_ENCUENTRO = "SELECT encuentro_id, paciente_id, estado, abierto_en FROM clinico.encuentro"


class Duplicado(Exception):
    """Otra solicitud usó la misma clave de idempotencia un instante antes."""


class EncuentroAbierto(Exception):
    """El paciente ya tiene un encuentro sin atender."""

    def __init__(self, encuentro_id):
        super().__init__()
        self.encuentro_id = encuentro_id


@dataclass(frozen=True)
class EncuentroInterno:
    """Lo que los demás pasos del triage necesitan saber de un encuentro."""

    encuentro_id: object
    paciente_id: object
    estado: str
    edad_dias: int | None


def hash_cuerpo(datos):
    """Hash del cuerpo de la solicitud, para saber si una clave se reusó con otro cuerpo."""
    return hashlib.sha256(datos.model_dump_json().encode()).hexdigest()


def _a_encuentro(fila):
    encuentro_id, paciente_id, estado, abierto_en = fila
    return Encuentro(encuentroId=encuentro_id, pacienteId=paciente_id, estado=estado,
                     abiertoEn=abierto_en.astimezone(UTC))


def buscar_por_clave(clave):
    """La respuesta ya entregada para esta clave, con el hash del cuerpo con que se usó. None
    si la clave es nueva."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT s.hash_cuerpo, e.encuentro_id, e.paciente_id, e.estado, e.abierto_en"
            " FROM clinico.solicitud_encuentro s JOIN clinico.encuentro e USING (encuentro_id)"
            " WHERE s.clave = %s",
            (clave,),
        ).fetchone()
    if fila is None:
        return None
    return fila[0], _a_encuentro(fila[1:])


def activo(paciente_id):
    """El encuentro sin atender del paciente, o None."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT encuentro_id FROM clinico.encuentro"
            " WHERE paciente_id = %s AND estado <> 'atendido'",
            (paciente_id,),
        ).fetchone()
    return fila[0] if fila else None


def abrir(paciente_id, edad_dias, sexo, clave, hash_del_cuerpo, trace_id):
    """Abre un encuentro con la foto de la edad y el sexo del paciente.

    Lanza EncuentroAbierto si el paciente ya tiene uno sin atender, y Duplicado si otra
    solicitud usó la misma clave al mismo tiempo. `trace_id` queda para cuando el encuentro
    genere un evento.
    """
    encuentro_id = uuid4()
    try:
        with bd.principal() as conexion:
            conexion.execute(
                "INSERT INTO clinico.encuentro"
                " (encuentro_id, paciente_id, estado, abierto_en, edad_dias, sexo)"
                " VALUES (%s, %s, 'abierto', %s, %s, %s)",
                (encuentro_id, paciente_id, datetime.now(UTC), edad_dias, sexo),
            )
            conexion.execute(
                "INSERT INTO clinico.solicitud_encuentro (clave, hash_cuerpo, encuentro_id)"
                " VALUES (%s, %s, %s)",
                (clave, hash_del_cuerpo, encuentro_id),
            )
            fila = conexion.execute(_ENCUENTRO + " WHERE encuentro_id = %s",
                                    (encuentro_id,)).fetchone()
    except errors.UniqueViolation as error:
        if error.diag.constraint_name == "un_encuentro_activo":
            raise EncuentroAbierto(activo(paciente_id)) from None
        raise Duplicado from None
    return _a_encuentro(fila)


def obtener(encuentro_id):
    """El encuentro, o None si no existe."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT encuentro_id, paciente_id, estado, edad_dias FROM clinico.encuentro"
            " WHERE encuentro_id = %s",
            (encuentro_id,),
        ).fetchone()
    return EncuentroInterno(*fila) if fila else None


def cambiar_estado(conexion, encuentro_id, estado):
    """Cambia el estado dentro de la transacción de quien llama, junto con el hecho que lo
    provoca."""
    conexion.execute("UPDATE clinico.encuentro SET estado = %s WHERE encuentro_id = %s",
                     (estado, encuentro_id))
