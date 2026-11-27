"""La categoría final: la decide la enfermera, no la IA (HU03).

Una categoría distinta de la sugerida exige justificación. La confirmación, su origen y quién
la hizo quedan en la outbox para la auditoría (amenazas T4 y R1 del threat model).
"""

from datetime import UTC, datetime

from src import bd
from src.auditoria.eventos import encolar
from src.evaluacion import encuentros
from src.evaluacion.modelos import CategoriaFinal


def decidir_origen(evaluacion, categoria):
    """De dónde sale la categoría final, comparada con la última evaluación."""
    if evaluacion.resultado == "derivado_triage_manual":
        return "asignada_triage_manual"
    if categoria == evaluacion.categoria_sugerida:
        return "confirmada_sugerencia_ia"
    return "modificada_por_enfermera"


def confirmar(encuentro, evaluacion, datos, origen, confirmada_por, trace_id):
    """Fija la categoría final (o la reemplaza) y deja el encuentro confirmado."""
    justificacion = datos.justificacionCambio.strip() if datos.justificacionCambio else None
    categoria = CategoriaFinal(encuentroId=encuentro.encuentro_id,
                               categoriaEsi=datos.categoriaEsi, origen=origen,
                               justificacionCambio=justificacion,
                               confirmadaEn=datetime.now(UTC))
    with bd.principal() as conexion:
        conexion.execute(
            "INSERT INTO clinico.categoria_final (encuentro_id, evaluacion_id, categoria_esi,"
            " origen, justificacion_cambio, confirmada_por, confirmada_en)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (encuentro_id) DO UPDATE SET evaluacion_id = excluded.evaluacion_id,"
            " categoria_esi = excluded.categoria_esi, origen = excluded.origen,"
            " justificacion_cambio = excluded.justificacion_cambio,"
            " confirmada_por = excluded.confirmada_por, confirmada_en = excluded.confirmada_en",
            (encuentro.encuentro_id, evaluacion.evaluacion_id, datos.categoriaEsi, origen,
             justificacion, confirmada_por, categoria.confirmadaEn),
        )
        encuentros.cambiar_estado(conexion, encuentro.encuentro_id, "confirmado")
        comun = {"encuentroId": str(encuentro.encuentro_id),
                 "evaluacionId": str(evaluacion.evaluacion_id)}
        encolar(conexion, "triage.confirmed", encuentro.encuentro_id, trace_id, comun | {
            "categoriaEsi": datos.categoriaEsi, "origen": origen,
            "confirmadaPor": confirmada_por,
        })
        # Acompaña al anterior cuando la enfermera cambia la sugerencia: deja el motivo.
        if origen == "modificada_por_enfermera":
            encolar(conexion, "triage.category_overridden", encuentro.encuentro_id, trace_id,
                    comun | {
                        "categoriaSugerida": evaluacion.categoria_sugerida,
                        "categoriaFinal": datos.categoriaEsi,
                        "justificacionCambio": justificacion,
                        "confirmadaPor": confirmada_por,
                    })
    return categoria
