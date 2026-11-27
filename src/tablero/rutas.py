"""GET /v1/sala-de-espera — La sala de espera priorizada (HU04)."""

from datetime import UTC, datetime

from fastapi import APIRouter

from src.tablero import sala
from src.tablero.modelos import SalaDeEspera

router = APIRouter(tags=["Sala de espera"])


@router.get("/v1/sala-de-espera", response_model=SalaDeEspera)
def consultar_sala_de_espera():
    return sala.consultar(datetime.now(UTC))
