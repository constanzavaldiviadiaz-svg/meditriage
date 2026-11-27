"""Forma de los datos que entran y salen del módulo de Evaluación.

Cada clase corresponde a un schema de api/openapi.yaml, con el mismo nombre y los mismos
campos.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class EstadoEncuentro(str, Enum):
    abierto = "abierto"
    en_espera = "en_espera"
    evaluado = "evaluado"
    derivado_triage_manual = "derivado_triage_manual"
    confirmado = "confirmado"
    atendido = "atendido"


class AbrirEncuentroInput(BaseModel):
    pacienteId: UUID


class Encuentro(BaseModel):
    encuentroId: UUID
    pacienteId: UUID
    estado: EstadoEncuentro
    abiertoEn: datetime
