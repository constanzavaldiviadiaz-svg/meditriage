"""Las decisiones de triage, tal como quedaron en la auditoría append-only (HU05).

Una decisión es una evaluación (la sugerencia de la IA o la derivación a triage manual) más su
última confirmación. Se arma solo con los registros de la base de auditoría, que la API lee con
un rol de solo lectura: no depende de los datos clínicos, que podrían cambiar.

Cada decisión trae el hash de integridad de su último registro. Con él, un auditor puede
comprobar que nada se alteró (auditoria.verificar_cadena()).
"""

from datetime import UTC

from src import bd
from src.auditoria.modelos import Decision

TIPOS_EVALUACION = ("triage.completed", "triage.derived_to_manual")

_COLUMNAS = "secuencia, tipo, aggregate_id, payload, registrado_en, hash_integridad"


def _confirmaciones(conexion, encuentros):
    """La última confirmación de cada evaluación, buscando por los encuentros."""
    filas = conexion.execute(
        "SELECT payload, hash_integridad FROM auditoria.registro"
        " WHERE tipo = 'triage.confirmed' AND aggregate_id = ANY(%s) ORDER BY secuencia",
        (list(encuentros),),
    ).fetchall()
    # Ordenadas por secuencia: la última que se escribe para cada evaluación es la vigente.
    return {payload.get("evaluacionId"): (payload, hash_) for payload, hash_ in filas}


def _armar(fila, confirmaciones):
    _, tipo, aggregate_id, payload, registrado_en, hash_integridad = fila
    sugerencia = tipo == "triage.completed"
    confirmacion, hash_confirmacion = confirmaciones.get(payload["evaluacionId"], (None, None))
    return Decision(
        decisionId=payload["evaluacionId"],
        encuentroRef=str(aggregate_id),
        pacienteRef=payload["pacienteId"],
        resultado="sugerencia_ia" if sugerencia else "derivado_triage_manual",
        categoriaSugerida=payload.get("categoriaEsi") if sugerencia else None,
        justificacion=payload.get("justificacion") if sugerencia else None,
        motivoDerivacion=None if sugerencia else payload.get("motivo"),
        categoriaFinal=confirmacion["categoriaEsi"] if confirmacion else None,
        confirmadaPor=confirmacion.get("confirmadaPor") if confirmacion else None,
        registradaEn=registrado_en.astimezone(UTC),
        hashIntegridad=hash_confirmacion or hash_integridad,
    )


def _con_confirmaciones(conexion, filas):
    confirmaciones = _confirmaciones(conexion, {fila[2] for fila in filas})
    return [_armar(fila, confirmaciones) for fila in filas]


def listar(desde, hasta, cursor, limite):
    """Las decisiones, las más recientes primero. `cursor` es la secuencia desde la que se
    sigue (exclusiva). Devuelve las decisiones y el cursor de la página siguiente, o None."""
    with bd.auditoria_lectura() as conexion:
        filas = conexion.execute(
            f"SELECT {_COLUMNAS} FROM auditoria.registro WHERE tipo = ANY(%s)"
            " AND (%s::timestamptz IS NULL OR registrado_en >= %s)"
            " AND (%s::timestamptz IS NULL OR registrado_en < %s)"
            " AND (%s::bigint IS NULL OR secuencia < %s)"
            " ORDER BY secuencia DESC LIMIT %s",
            (list(TIPOS_EVALUACION), desde, desde, hasta, hasta, cursor, cursor, limite + 1),
        ).fetchall()
        hay_mas = len(filas) > limite
        filas = filas[:limite]
        decisiones = _con_confirmaciones(conexion, filas)
    siguiente = filas[-1][0] if hay_mas else None
    return decisiones, siguiente


def obtener(decision_id):
    """Una decisión por su id (el de la evaluación), o None si no está en la auditoría."""
    with bd.auditoria_lectura() as conexion:
        fila = conexion.execute(
            f"SELECT {_COLUMNAS} FROM auditoria.registro"
            " WHERE tipo = ANY(%s) AND payload->>'evaluacionId' = %s",
            (list(TIPOS_EVALUACION), str(decision_id)),
        ).fetchone()
        if fila is None:
            return None
        [decision] = _con_confirmaciones(conexion, [fila])
    return decision
