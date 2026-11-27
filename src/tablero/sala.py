"""La sala de espera: quién espera, con qué prioridad y hace cuánto (HU04).

Es una vista de lectura (CQRS liviano, ADR 0004). Se lee de PostgreSQL directamente: la vista
en Redis quedó diferida en el #121. El nombre se pide al contexto de identidad, y solo viaja
en la respuesta: nunca a un log ni a un evento.
"""

from datetime import UTC

from src import bd
from src.registro import almacen
from src.tablero.modelos import PacienteEnEspera, SalaDeEspera


def consultar(ahora):
    """Los encuentros con categoría final que todavía no se atienden: primero la categoría ESI
    más urgente (1) y, dentro de cada una, el que llegó antes."""
    with bd.principal() as conexion:
        filas = conexion.execute(
            "SELECT e.encuentro_id, e.paciente_id, c.categoria_esi, e.abierto_en"
            " FROM clinico.encuentro e JOIN clinico.categoria_final c USING (encuentro_id)"
            " WHERE e.estado <> 'atendido'"
            " ORDER BY c.categoria_esi, e.abierto_en"
        ).fetchall()
    nombres = almacen.nombres_por_id([paciente_id for _, paciente_id, _, _ in filas])
    return SalaDeEspera(
        actualizadaEn=ahora,
        pacientes=[
            PacienteEnEspera(
                encuentroId=encuentro_id,
                nombre=nombres[paciente_id],
                categoriaEsi=categoria,
                esperaMinutos=max(0, int((ahora - abierto_en).total_seconds() // 60)),
                llegadaEn=abierto_en.astimezone(UTC),
            )
            for encuentro_id, paciente_id, categoria, abierto_en in filas
        ],
    )
