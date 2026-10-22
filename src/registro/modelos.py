"""Forma de los datos que entran y salen del registro de pacientes.

Cada clase corresponde a un schema de api/openapi.yaml, con el mismo nombre y los mismos
campos. FastAPI usa estas clases para revisar solo cada solicitud: si falta un campo o el
formato no calza, responde 400 antes de que el código de la ruta se ejecute.
"""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class EstadoConsentimiento(str, Enum):
    otorgado = "otorgado"
    exencion_emergencia_vital = "exencion_emergencia_vital"
    rechazado = "rechazado"


class ConsentimientoInput(BaseModel):
    estado: EstadoConsentimiento
    observacion: str | None = Field(default=None, max_length=500)


class RegistroPacienteInput(BaseModel):
    # Formato del contrato: 7 u 8 dígitos, guion y dígito verificador.
    rut: str = Field(pattern=r"^\d{7,8}-[0-9Kk]$")
    nombre: str = Field(min_length=1, max_length=200)
    fechaNacimiento: date | None = None
    consentimiento: ConsentimientoInput


class ConsentimientoRegistrado(BaseModel):
    estado: EstadoConsentimiento
    registradoEn: datetime


class Paciente(BaseModel):
    """Lo que la API devuelve. Nótese que no incluye el nombre ni el RUT completo."""

    pacienteId: UUID
    rutEnmascarado: str
    consentimiento: ConsentimientoRegistrado
    registradoEn: datetime
