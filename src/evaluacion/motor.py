"""El motor de IA, detrás de una interfaz propia (ADR 0008).

`SugeridorEsi` es lo único que el servicio conoce de la IA. Hay dos implementaciones:

- `ClienteClaude`: la API de Claude, con el SDK oficial.
- `Simulador`: para desarrollo, pruebas y CI. Responde sin gastar créditos, y puede simular
  lentitud, caídas y respuestas inválidas para probar cada guardrail.

Se elige con la variable MOTOR_IA. Cambiar de proveedor es escribir otra implementación.
"""

import json
import time
from dataclasses import dataclass
from typing import Protocol

import anthropic

from src import config
from src.evaluacion import prompt


@dataclass(frozen=True)
class RespuestaIa:
    texto: str         # la respuesta exacta, tal como llegó (G5)
    stop_reason: str
    modelo: str


class FallaMotor(Exception):
    """La IA no respondió: `motivo` es "timeout" o "servicio_no_disponible"."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


class SugeridorEsi(Protocol):
    def sugerir(self, solicitud: dict, timeout: float) -> RespuestaIa: ...


class ClienteClaude:
    """La API de Claude (ADR 0008): salida estructurada, sin razonamiento extendido, esfuerzo
    bajo, inferencia en EE. UU. y sin reintentos: un fallo se deriva, no se repite."""

    def __init__(self, cliente=None):
        # Lee ANTHROPIC_API_KEY del ambiente, que viene de un Secret de Kubernetes.
        self.cliente = cliente or anthropic.Anthropic(max_retries=0)

    def sugerir(self, solicitud, timeout):
        try:
            respuesta = self.cliente.messages.create(
                model=config.MODELO_IA,
                max_tokens=400,
                system=prompt.SISTEMA,
                messages=[{"role": "user", "content": prompt.mensaje_usuario(solicitud)}],
                thinking={"type": "disabled"},
                inference_geo="us",
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": prompt.ESQUEMA},
                },
                timeout=timeout,
            )
        except anthropic.APITimeoutError:
            raise FallaMotor("timeout") from None
        except (anthropic.APIConnectionError, anthropic.APIStatusError):
            # La API está caída, rechazó la clave o se acabaron los créditos.
            raise FallaMotor("servicio_no_disponible") from None
        texto = next((b.text for b in respuesta.content if b.type == "text"), "")
        return RespuestaIa(texto=texto, stop_reason=respuesta.stop_reason,
                           modelo=respuesta.model)


class Simulador:
    """Un motor de IA de mentira, configurable. Guarda la última solicitud, para que las
    pruebas comprueben qué habría salido del sistema."""

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.modo = "sugerir"
        self.llamadas = 0
        self.ultima_solicitud = None

    def sugerir(self, solicitud, timeout):
        self.llamadas += 1
        self.ultima_solicitud = solicitud
        if self.modo == "caido":
            raise FallaMotor("servicio_no_disponible")
        if self.modo == "lento":
            time.sleep(timeout)
            raise FallaMotor("timeout")
        if self.modo == "colgado":
            # Responde bien, pero tarde, sin respetar el timeout: como el SDK cuando la suma
            # de las fases de la conexión pasa el límite.
            time.sleep(timeout * 5)

        signos = solicitud.get("signosVitales") or {}
        saturacion = signos.get("saturacionOxigeno") or 100
        categoria = 2 if saturacion < 90 else 3
        salida = {
            "categoriaEsi": categoria,
            "justificacion": {
                "resumen": "Sugerencia del simulador, a partir de la saturación de oxígeno.",
                "factores": [{"factor": "saturacion_oxigeno",
                              "descripcion": f"{saturacion} %"}],
            },
        }
        stop_reason = "end_turn"
        if self.modo == "invalido":
            salida["categoriaEsi"] = 7
        elif self.modo == "sin_factores":
            salida["justificacion"]["factores"] = []
        elif self.modo == "cortado":
            stop_reason = "max_tokens"
        elif self.modo == "rechazo":
            stop_reason = "refusal"
        texto = "{no es json" if self.modo == "json_roto" else json.dumps(salida,
                                                                         ensure_ascii=False)
        return RespuestaIa(texto=texto, stop_reason=stop_reason, modelo="simulador")


simulador = Simulador()
_claude = None


def obtener():
    """El motor que fija MOTOR_IA."""
    global _claude
    if config.MOTOR_IA == "claude":
        if _claude is None:
            _claude = ClienteClaude()
        return _claude
    return simulador
