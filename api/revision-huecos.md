# Revisión de Huecos: Contrato API vs Escenarios Gherkin (QA Lead)

Al cruzar los escenarios definidos en `docs/scenarios/` con los posibles códigos de error HTTP de un contrato estándar, se detectan los siguientes huecos o requerimientos que el `openapi.yaml` debe contemplar explícitamente:

1. **Rechazo por consentimiento no otorgado (HU01)**
   * **Hueco:** El contrato debe incluir una respuesta `403 Forbidden` o `422 Unprocessable Entity` en el endpoint de registro cuando el campo `consent_accepted` sea `false`.
2. **Acceso denegado por falta de privilegios (HU05)**
   * **Hueco:** El contrato debe documentar una respuesta `401 Unauthorized` o `403 Forbidden` para intentos de lectura de historial o ejecución de fallback manual sin el rol adecuado (ej. usuario no autenticado o rol distinto a médico/enfermera).
3. **Respuesta malformada del modelo (HU03)**
   * **Hueco:** Se requiere un código `502 Bad Gateway` o `500 Internal Server Error` con un código interno tipo `IA_MALFORMED_RESPONSE` si la IA externa responde sin un ESI válido o justificación.
4. **Timeout y servicio caído (HU06)**
   * **Hueco:** El endpoint de sugerencia ESI debe definir explícitamente `504 Gateway Timeout` (> 3 segundos) y `503 Service Unavailable` para activar el flujo alternativo de triage manual documentado.
