"""Configuración de la aplicación.

Todo valor que cambia entre ambientes (desarrollo, staging, producción) se lee desde
variables de entorno, nunca se escribe fijo en el código. Es el factor III del checklist
12-Factor: el mismo código corre en cualquier ambiente, solo cambia su configuración.
"""

import os

# Puerto en el que escucha la aplicación. Kubernetes lo usa para llegar a ella.
PUERTO = int(os.getenv("PUERTO", "8080"))

# Nombre del ambiente: "desarrollo", "staging" o "produccion".
AMBIENTE = os.getenv("AMBIENTE", "desarrollo")

# Cada cuántos segundos el worker lleva los eventos de la outbox a la auditoría.
INTERVALO_RELAY = float(os.getenv("INTERVALO_RELAY", "1"))

# Las direcciones de las bases se leen en src/bd.py, al abrir la primera conexión. Traen la
# clave, así que vienen de un Secret de Kubernetes. La API usa solo BASE_DATOS_URL; el worker,
# además, AUDITORIA_URL.
