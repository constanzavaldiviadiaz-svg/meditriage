"""Forma de los datos que entran y salen del módulo de Evaluación.

Cada clase corresponde a un schema de api/openapi.yaml, con el mismo nombre y los mismos
campos.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
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


class Factor(BaseModel):
    factor: str
    descripcion: str


class Justificacion(BaseModel):
    """Por qué la IA sugiere esa categoría: un resumen y al menos un factor (explicabilidad)."""

    resumen: str
    factores: list[Factor] = Field(min_length=1)


class SugerenciaIa(BaseModel):
    evaluacionId: UUID
    encuentroId: UUID
    resultado: Literal["sugerencia_ia"] = "sugerencia_ia"
    categoriaEsi: int = Field(ge=1, le=5)
    justificacion: Justificacion
    duracionMs: int = Field(ge=0)
    generadaEn: datetime


class DerivacionManual(BaseModel):
    evaluacionId: UUID
    encuentroId: UUID
    resultado: Literal["derivado_triage_manual"] = "derivado_triage_manual"
    motivo: Literal["timeout", "servicio_no_disponible", "respuesta_invalida"]
    duracionMs: int = Field(ge=0)
    generadaEn: datetime


class ConfirmacionInput(BaseModel):
    categoriaEsi: int = Field(ge=1, le=5)
    justificacionCambio: str | None = Field(default=None, max_length=1000)


class CategoriaFinal(BaseModel):
    encuentroId: UUID
    categoriaEsi: int
    origen: Literal["confirmada_sugerencia_ia", "modificada_por_enfermera",
                    "asignada_triage_manual"]
    justificacionCambio: str | None
    confirmadaEn: datetime
