"""Forma de los datos que entran y salen del módulo de Evaluación.

Cada clase corresponde a un schema de api/openapi.yaml, con el mismo nombre y los mismos
campos.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


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


class SignosVitalesInput(BaseModel):
    """Los rangos son los del contrato. Los campos obligatorios se dejan opcionales aquí a
    propósito: si falta uno, la ruta responde 422 datos-clinicos-incompletos con la lista de
    lo que falta, como pide el contrato, y no un 400 genérico."""

    presionSistolica: int | None = Field(default=None, ge=40, le=300)
    presionDiastolica: int | None = Field(default=None, ge=20, le=200)
    frecuenciaCardiaca: int | None = Field(default=None, ge=20, le=250)
    frecuenciaRespiratoria: int | None = Field(default=None, ge=4, le=80)
    temperatura: float | None = Field(default=None, ge=30, le=45)
    saturacionOxigeno: int | None = Field(default=None, ge=50, le=100)


class DatosClinicosInput(BaseModel):
    motivoConsulta: str | None = Field(default=None, max_length=500)
    sintomas: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list)
    signosVitales: SignosVitalesInput | None = None


class AlertaSignoVital(BaseModel):
    signo: str
    valor: str
    nivel: str


class DatosClinicos(BaseModel):
    encuentroId: UUID
    registradoEn: datetime
    alertas: list[AlertaSignoVital]
