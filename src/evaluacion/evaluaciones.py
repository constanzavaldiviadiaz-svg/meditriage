"""Dónde se guardan las evaluaciones: la sugerencia de la IA o la derivación (HU03, HU06).

La ruta está en rutas.py y la llamada a la IA, en servicio.py. Cada función de este archivo
guarda la evaluación, cambia el estado del encuentro y deja su evento en la outbox, en una
sola transacción.
"""

from dataclasses import dataclass
from uuid import uuid4

from psycopg.types.json import Jsonb

from src import bd
from src.auditoria.eventos import encolar
from src.evaluacion import encuentros
from src.evaluacion.modelos import DerivacionManual, SugerenciaIa


@dataclass(frozen=True)
class EvaluacionInterna:
    """Lo que la confirmación necesita saber de la última evaluación."""

    evaluacion_id: object
    resultado: str
    categoria_sugerida: int | None


def guardar_sugerencia(encuentro, categoria, justificacion, duracion_ms, modelo,
                       version_prompt, respuesta_original, trace_id):
    """La IA respondió a tiempo con una categoría válida. El encuentro queda evaluado.

    La hora la pone PostgreSQL (clock_timestamp(), en microsegundos): la de Python, en Windows,
    puede repetirse entre dos evaluaciones seguidas, y "la última" quedaría ambigua."""
    evaluacion_id = uuid4()
    with bd.principal() as conexion:
        [generada_en] = conexion.execute(
            "INSERT INTO clinico.evaluacion (evaluacion_id, encuentro_id, resultado,"
            " categoria_sugerida, justificacion, duracion_ms, modelo, version_prompt,"
            " respuesta_ia_original, generada_en, trace_id)"
            " VALUES (%s, %s, 'sugerencia_ia', %s, %s, %s, %s, %s, %s, clock_timestamp(), %s)"
            " RETURNING generada_en",
            (evaluacion_id, encuentro.encuentro_id, categoria,
             Jsonb(justificacion.model_dump()), duracion_ms, modelo, version_prompt,
             respuesta_original, trace_id),
        ).fetchone()
        sugerencia = SugerenciaIa(evaluacionId=evaluacion_id,
                                  encuentroId=encuentro.encuentro_id, categoriaEsi=categoria,
                                  justificacion=justificacion, duracionMs=duracion_ms,
                                  generadaEn=generada_en)
        encuentros.cambiar_estado(conexion, encuentro.encuentro_id, "evaluado")
        encolar(conexion, "triage.completed", encuentro.encuentro_id, trace_id, {
            "encuentroId": str(encuentro.encuentro_id),
            "evaluacionId": str(sugerencia.evaluacionId),
            "pacienteId": str(encuentro.paciente_id),
            "categoriaEsi": categoria,
            "justificacion": justificacion.model_dump(),
            "duracionMs": duracion_ms,
            # Para reconstruir la decisión (G5): qué modelo y qué versión del prompt.
            "modelo": modelo,
            "versionPrompt": version_prompt,
        })
    return sugerencia


def guardar_derivacion(encuentro, motivo, duracion_ms, trace_id):
    """La IA no respondió a tiempo, está caída o respondió algo inválido (HU06). El caso pasa a
    triage manual: no es un error, es el camino previsto."""
    evaluacion_id = uuid4()
    with bd.principal() as conexion:
        [generada_en] = conexion.execute(
            "INSERT INTO clinico.evaluacion (evaluacion_id, encuentro_id, resultado,"
            " motivo_derivacion, duracion_ms, generada_en, trace_id)"
            " VALUES (%s, %s, 'derivado_triage_manual', %s, %s, clock_timestamp(), %s)"
            " RETURNING generada_en",
            (evaluacion_id, encuentro.encuentro_id, motivo, duracion_ms, trace_id),
        ).fetchone()
        derivacion = DerivacionManual(evaluacionId=evaluacion_id,
                                      encuentroId=encuentro.encuentro_id, motivo=motivo,
                                      duracionMs=duracion_ms, generadaEn=generada_en)
        encuentros.cambiar_estado(conexion, encuentro.encuentro_id, "derivado_triage_manual")
        encolar(conexion, "triage.derived_to_manual", encuentro.encuentro_id, trace_id, {
            "encuentroId": str(encuentro.encuentro_id),
            "evaluacionId": str(derivacion.evaluacionId),
            "pacienteId": str(encuentro.paciente_id),
            "motivo": motivo,
            "duracionMs": duracion_ms,
        })
    return derivacion


def obtener(evaluacion_id):
    """Una evaluación ya guardada, en la forma del contrato. Para la idempotencia."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT evaluacion_id, encuentro_id, resultado, categoria_sugerida, justificacion,"
            " motivo_derivacion, duracion_ms, generada_en FROM clinico.evaluacion"
            " WHERE evaluacion_id = %s", (evaluacion_id,)).fetchone()
    (evaluacion_id, encuentro_id, resultado, categoria, justificacion, motivo, duracion,
     generada_en) = fila
    comun = {"evaluacionId": evaluacion_id, "encuentroId": encuentro_id,
             "duracionMs": duracion, "generadaEn": generada_en}
    if resultado == "sugerencia_ia":
        return SugerenciaIa(categoriaEsi=categoria, justificacion=justificacion, **comun)
    return DerivacionManual(motivo=motivo, **comun)


def buscar_por_clave(clave):
    """(encuentro_id, evaluacion_id) de la evaluación ya hecha con esta clave, o None."""
    with bd.principal() as conexion:
        return conexion.execute(
            "SELECT encuentro_id, evaluacion_id FROM clinico.solicitud_evaluacion"
            " WHERE clave = %s", (clave,)).fetchone()


def recordar_clave(clave, encuentro_id, evaluacion_id):
    """Asocia la clave a la evaluación. Si dos solicitudes con la misma clave llegaron a la vez,
    queda la primera."""
    with bd.principal() as conexion:
        conexion.execute(
            "INSERT INTO clinico.solicitud_evaluacion (clave, encuentro_id, evaluacion_id)"
            " VALUES (%s, %s, %s) ON CONFLICT (clave) DO NOTHING",
            (clave, encuentro_id, evaluacion_id))


def ultima(encuentro_id):
    """La evaluación más reciente del encuentro, o None si todavía no tiene."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT evaluacion_id, resultado, categoria_sugerida FROM clinico.evaluacion"
            " WHERE encuentro_id = %s ORDER BY generada_en DESC LIMIT 1",
            (encuentro_id,),
        ).fetchone()
    return EvaluacionInterna(*fila) if fila else None
