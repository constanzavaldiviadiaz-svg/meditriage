"""Consulta de las decisiones auditadas (HU05): para el auditor clínico.

GET /v1/auditoria/decisiones y GET /v1/auditoria/decisiones/{decisionId}. Los permisos por rol
(solo el auditor, error acceso-denegado) llegan con la autenticación (#103).
"""

import base64
import binascii
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from src.auditoria import decisiones
from src.auditoria.modelos import Decision, PaginaDecisiones
from src.errores import Problema

router = APIRouter(tags=["Auditoría"])


def _codificar_cursor(secuencia):
    return base64.urlsafe_b64encode(str(secuencia).encode()).rstrip(b"=").decode()


def _decodificar_cursor(cursor):
    """La secuencia que trae el cursor, o None si no es un cursor que haya entregado la API."""
    try:
        texto = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    if not texto.isdigit() or int(texto) < 1:
        return None
    return int(texto)


@router.get("/v1/auditoria/decisiones", response_model=PaginaDecisiones)
def consultar_decisiones(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    cursor: str | None = None,
    limite: int = Query(default=50, ge=1, le=100),
):
    if desde and hasta and desde >= hasta:
        raise Problema("rango-invalido", "Rango inválido", 422,
                       "La fecha desde tiene que ser anterior a la fecha hasta.")
    secuencia = None
    if cursor is not None:
        secuencia = _decodificar_cursor(cursor)
        if secuencia is None:
            raise Problema("cursor-invalido", "Cursor inválido", 422,
                           "El cursor no corresponde a una página entregada por la API.")

    datos, siguiente = decisiones.listar(desde, hasta, secuencia, limite)
    return PaginaDecisiones(
        datos=datos,
        siguienteCursor=_codificar_cursor(siguiente) if siguiente else None,
    )


@router.get("/v1/auditoria/decisiones/{decision_id}", response_model=Decision)
def obtener_decision(decision_id: UUID):
    decision = decisiones.obtener(decision_id)
    if decision is None:
        raise Problema("recurso-no-encontrado", "Recurso no encontrado", 404,
                       "No hay una decisión auditada con ese decisionId.")
    return decision
