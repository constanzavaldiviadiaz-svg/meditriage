"""Circuit breaker del motor de IA (ADR 0003).

Si la IA falla varias veces seguidas, deja de llamarla por un tiempo y el servicio deriva a
triage manual de inmediato, sin esperar 3 segundos en cada paciente. Pasado el enfriamiento,
deja pasar una llamada de prueba: si responde, el circuito se cierra.

Vive en memoria de cada réplica: si una réplica abre su circuito, las otras siguen probando.
"""

import threading
import time


class CircuitBreaker:
    def __init__(self, umbral=3, enfriamiento=30.0, reloj=time.monotonic):
        self.umbral = umbral
        self.enfriamiento = enfriamiento
        self.reloj = reloj
        self._candado = threading.Lock()
        self.reiniciar()

    def reiniciar(self):
        self._fallas = 0
        self._abierto_desde = None

    def permite(self):
        """¿Se puede llamar a la IA ahora?"""
        with self._candado:
            if self._abierto_desde is None:
                return True
            return self.reloj() - self._abierto_desde >= self.enfriamiento

    def exito(self):
        with self._candado:
            self._fallas = 0
            self._abierto_desde = None

    def falla(self):
        with self._candado:
            self._fallas += 1
            if self._fallas >= self.umbral:
                self._abierto_desde = self.reloj()


circuito = CircuitBreaker()
