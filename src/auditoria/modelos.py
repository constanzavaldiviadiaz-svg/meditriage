"""Forma de las decisiones auditadas. Cada clase corresponde a un schema de api/openapi.yaml."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class Decision(BaseModel):
    decisionId: UUID
    # Referencias opacas: el UUID del encuentro y del paciente, nunca su RUT ni su nombre.
    encuentroRef: str
    pacienteRef: str
    resultado: Literal["sugerencia_ia", "derivado_triage_manual"]
    categoriaSugerida: int | None
    # La justificación tal como la entregó la IA (resumen y factores).
    justificacion: dict | None
    motivoDerivacion: Literal["timeout", "servicio_no_disponible", "respuesta_invalida"] | None
    categoriaFinal: int | None
    confirmadaPor: str | None
    registradaEn: datetime
    hashIntegridad: str


class PaginaDecisiones(BaseModel):
    datos: list[Decision]
    siguienteCursor: str | None
