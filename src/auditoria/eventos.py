"""Eventos de dominio que llegan a la auditoría, a través de la outbox (ADR 0004).

Un evento se guarda en la misma transacción que el hecho que lo origina: o quedan los dos o
ninguno. El relay lo lleva después a la base de auditoría.
"""

from uuid import uuid4

from psycopg.types.json import Jsonb

VERSION = "1.0"


def encolar(conexion, tipo, aggregate_id, trace_id, payload):
    """Guarda un evento en la outbox, dentro de la transacción de `conexion`.

    El payload nunca lleva RUT ni nombre: solo referencias opacas y datos ya enmascarados.
    """
    conexion.execute(
        "INSERT INTO clinico.outbox_evento"
        " (evento_id, tipo, version, aggregate_id, trace_id, payload)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (uuid4(), tipo, VERSION, aggregate_id, trace_id, Jsonb(payload)),
    )
