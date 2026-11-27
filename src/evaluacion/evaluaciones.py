"""Dónde se guardan las evaluaciones: la sugerencia de la IA o la derivación (HU03, HU06).

No hay ruta aquí: la ruta que llama al motor de IA llega con el #123 y usa estas funciones.
Cada una guarda la evaluación, cambia el estado del encuentro y deja su evento en la outbox,
en una sola transacción.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
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
    """La IA respondió a tiempo con una categoría válida. El encuentro queda evaluado."""
    sugerencia = SugerenciaIa(evaluacionId=uuid4(), encuentroId=encuentro.encuentro_id,
                              categoriaEsi=categoria, justificacion=justificacion,
                              duracionMs=duracion_ms, generadaEn=datetime.now(UTC))
    with bd.principal() as conexion:
        conexion.execute(
            "INSERT INTO clinico.evaluacion (evaluacion_id, encuentro_id, resultado,"
            " categoria_sugerida, justificacion, duracion_ms, modelo, version_prompt,"
            " respuesta_ia_original, generada_en, trace_id)"
            " VALUES (%s, %s, 'sugerencia_ia', %s, %s, %s, %s, %s, %s, %s, %s)",
            (sugerencia.evaluacionId, encuentro.encuentro_id, categoria,
             Jsonb(justificacion.model_dump()), duracion_ms, modelo, version_prompt,
             respuesta_original, sugerencia.generadaEn, trace_id),
        )
        encuentros.cambiar_estado(conexion, encuentro.encuentro_id, "evaluado")
        encolar(conexion, "triage.completed", encuentro.encuentro_id, trace_id, {
            "encuentroId": str(encuentro.encuentro_id),
            "evaluacionId": str(sugerencia.evaluacionId),
            "pacienteId": str(encuentro.paciente_id),
            "categoriaEsi": categoria,
            "justificacion": justificacion.model_dump(),
            "duracionMs": duracion_ms,
        })
    return sugerencia


def guardar_derivacion(encuentro, motivo, duracion_ms, trace_id):
    """La IA no respondió a tiempo, está caída o respondió algo inválido (HU06). El caso pasa a
    triage manual: no es un error, es el camino previsto."""
    derivacion = DerivacionManual(evaluacionId=uuid4(), encuentroId=encuentro.encuentro_id,
                                  motivo=motivo, duracionMs=duracion_ms,
                                  generadaEn=datetime.now(UTC))
    with bd.principal() as conexion:
        conexion.execute(
            "INSERT INTO clinico.evaluacion (evaluacion_id, encuentro_id, resultado,"
            " motivo_derivacion, duracion_ms, generada_en, trace_id)"
            " VALUES (%s, %s, 'derivado_triage_manual', %s, %s, %s, %s)",
            (derivacion.evaluacionId, encuentro.encuentro_id, motivo, duracion_ms,
             derivacion.generadaEn, trace_id),
        )
        encuentros.cambiar_estado(conexion, encuentro.encuentro_id, "derivado_triage_manual")
        encolar(conexion, "triage.derived_to_manual", encuentro.encuentro_id, trace_id, {
            "encuentroId": str(encuentro.encuentro_id),
            "evaluacionId": str(derivacion.evaluacionId),
            "pacienteId": str(encuentro.paciente_id),
            "motivo": motivo,
            "duracionMs": duracion_ms,
        })
    return derivacion


def ultima(encuentro_id):
    """La evaluación más reciente del encuentro, o None si todavía no tiene."""
    with bd.principal() as conexion:
        fila = conexion.execute(
            "SELECT evaluacion_id, resultado, categoria_sugerida FROM clinico.evaluacion"
            " WHERE encuentro_id = %s ORDER BY generada_en DESC LIMIT 1",
            (encuentro_id,),
        ).fetchone()
    return EvaluacionInterna(*fila) if fila else None
