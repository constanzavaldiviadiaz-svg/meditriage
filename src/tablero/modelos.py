"""Forma de la sala de espera. Cada clase corresponde a un schema de api/openapi.yaml."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PacienteEnEspera(BaseModel):
    encuentroId: UUID
    nombre: str
    categoriaEsi: int
    esperaMinutos: int
    llegadaEn: datetime


class SalaDeEspera(BaseModel):
    actualizadaEn: datetime
    pacientes: list[PacienteEnEspera]
