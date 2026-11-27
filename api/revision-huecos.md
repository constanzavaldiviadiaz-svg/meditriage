Revisión de huecos: contrato API vs escenarios Gherkin (QA Lead)

Se cruzaron los escenarios de error de docs/scenarios/ con las respuestas definidas en api/openapi.yaml (versión 1.1.0).

Conclusión: los cuatro escenarios revisados están cubiertos por el contrato. No hay huecos. Una versión anterior de este documento proponía agregar respuestas 403, 502, 503 y 504. No hacía falta: el contrato ya las resuelve, y en el caso de la IA lo hace con un diseño distinto al de un error HTTP.

#	Escenario	Dónde lo cubre el contrato
1	HU01. Registro sin consentimiento informado	POST /v1/pacientes (registrarPaciente) responde 422 consentimiento-no-otorgado (ejemplo consentimientoNoOtorgado). El contrato indica que el intento queda en el audit log con la PII enmascarada.
2	HU05. Acceso sin permisos de auditoría	GET /v1/auditoria/decisiones y GET /v1/auditoria/decisiones/{decisionId} responden 401 (NoAutenticado) y 403 acceso-denegado (AccesoDenegado). Piden el scope auditoria:read, que solo tiene el auditor clínico. La respuesta 403 indica que el intento queda en el log de seguridad.
3	HU03. Respuesta malformada del modelo	POST /v1/encuentros/{encuentroId}/evaluaciones (solicitarEvaluacion) responde 201 con resultado: derivado_triage_manual y motivo: respuesta_invalida (schema DerivacionManual).
4	HU06. Timeout y servicio caído	La misma operación responde 201 con motivo: timeout (ejemplo derivacionPorTimeout) o motivo: servicio_no_disponible.
Por qué los puntos 3 y 4 no son errores HTTP

Es una decisión de diseño defendida en la S05: si la IA falla, demora o responde algo ininterpretable, la respuesta no es un error sino un resultado diseñado (derivado_triage_manual). La enfermera sigue trabajando sin esperar y la derivación queda en el audit log. Un 502, 503 o 504 le exigiría a la aplicación cliente manejar un error en un caso que el diseño considera normal.

Otros escenarios de error que también quedaron cubiertos
Escenario	Dónde lo cubre el contrato
HU01. RUT con dígito verificador inválido	422 rut-invalido en registrarPaciente (ejemplo rutInvalido; ver api/examples/hu01-validation-*).
HU02. Formulario sin los síntomas principales	422 datos-clinicos-incompletos con camposFaltantes (ejemplo datosClinicosIncompletos).
HU03. Cambio de la categoría sugerida sin justificación	422 justificacion-requerida (ejemplo justificacionRequerida).
HU05. Filtro por rango de fechas	GET /v1/auditoria/decisiones acepta los parámetros desde y hasta.
Lo que esta revisión no cubre
Solo se comparó el contrato con los escenarios. No se verificó que la API implementada lo cumpla: hoy solo POST /v1/pacientes está implementada.
La desconexión del tablero (HU04) es un comportamiento del cliente (reconexión y aviso de datos desactualizados), no una respuesta del contrato.
