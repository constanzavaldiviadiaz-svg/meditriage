# Catálogo de eventos de dominio — MediTriage

Un evento de dominio describe algo relevante que **ya ocurrió** en el sistema. No es un comando
ni una petición: se nombra en pasado y no se modifica nunca.

## Reglas

1. **Nombre en pasado**, con el formato `recurso.hecho_en_pasado`: `triage.completed`,
   `consent.rejected`.
2. **Versionado.** Cada evento declara su versión (`v1`). Un cambio que rompe a los
   consumidores crea una versión nueva; la anterior no se edita.
3. **Trazabilidad.** Todo evento lleva el `trace_id` de la solicitud que lo originó
   (el mismo de la cabecera `X-Trace-Id`).
4. **Inmutable.** Un evento publicado no se modifica ni se borra. Una corrección es un evento
   nuevo.
5. **Sin datos personales.** Ningún evento lleva RUT ni nombre. Solo identificadores opacos
   (`pacienteId`, `encuentroId`) y datos clínicos despersonalizados (ADR 0002 y ADR 0004).
6. **Entrega *at-least-once*.** Un evento puede llegar más de una vez. **Todo consumidor es
   idempotente por `evento_id`**: un evento ya procesado se descarta sin repetir su efecto
   (ADR 0004).

## Esquema base

Todos los eventos comparten este sobre, que corresponde a la tabla `outbox_evento` del DER
(`docs/data/der.puml`). Lo propio de cada evento va en `payload`.

```json
{
  "evento_id": "uuid",
  "tipo": "triage.completed",
  "version": "1",
  "aggregate_id": "uuid",
  "trace_id": "c8f2b1e4a9d7",
  "creado_en": "2026-10-08T14:22:31Z",
  "payload": {}
}
```

| Campo | Descripción |
|---|---|
| `evento_id` | Identificador único del evento. Es la clave de idempotencia de los consumidores. |
| `tipo` | Nombre del evento, en el formato de la regla 1. |
| `version` | Versión del schema del `payload`. |
| `aggregate_id` | Identificador de la entidad a la que pertenece el evento (ver cada ficha). |
| `trace_id` | Identificador de trazabilidad de la solicitud de origen. |
| `creado_en` | Momento en que ocurrió el hecho, en UTC. |
| `payload` | Datos propios del evento. Sus nombres siguen los del contrato (`api/openapi.yaml`). |

## Resumen

| # | Evento | Versión | Productor | Consumidores | Escenario de origen |
|---|---|---|---|---|---|
| 1 | `patient.registered` | v1 | Registro | Auditoría | HU01 — registro exitoso y exención |
| 2 | `vitals.captured` | v1 | Evaluación | Auditoría | HU02 — ingreso de signos vitales |
| 3 | `symptoms.reported` | v1 | Evaluación | Auditoría | HU02 — ingreso de síntomas |
| 4 | `triage.requested` | v1 | Evaluación | Auditoría | HU03 — el caso se envía al motor de IA |
| 5 | `triage.completed` | v1 | Evaluación | Auditoría | HU03 — sugerencia ESI con explicación |
| 6 | `triage.confirmed` | v1 | Evaluación | Auditoría · Sala de espera | HU03 — la enfermera confirma la categoría |
| 7 | `patient.attended` | v1 | Tablero | Auditoría · Sala de espera | HU04 — el médico atiende al paciente |
| 8 | `consent.rejected` | v1 | Registro | Auditoría | HU01 — consentimiento rechazado |
| 9 | `rut.rejected` | v1 | Registro | Auditoría | HU01 — RUT con dígito verificador inválido |
| 10 | `vitals.critical_detected` | v1 | Evaluación | Auditoría · Sala de espera | HU02 — signos vitales en límite crítico |
| 11 | `triage.derived_to_manual` | v1 | Evaluación | Auditoría · Sala de espera | HU06 y HU03 — la IA falla, demora o responde algo ininterpretable |
| 12 | `triage.category_overridden` | v1 | Evaluación | Auditoría | HU03 — la enfermera cambia la categoría sugerida |
| 13 | `audit.access_denied` | v1 | Auditoría | Auditoría | HU05 — acceso sin permisos |

Los eventos 1 a 7 son los del ciclo de vida del paciente que dio la sesión; del 8 al 13 son los
caminos de error y de excepción, que salen de los escenarios Gherkin.

Los consumidores son los dos grupos del ADR 0004: **Auditoría**, que escribe cada evento en la
base append-only, y **Sala de espera**, que actualiza la vista de lectura.

## Fichas

### patient.registered · v1

Se emite cuando se registra un paciente con su RUT validado y su consentimiento otorgado, o con
la exención por emergencia vital.

| Campo | Tipo | Descripción |
|---|---|---|
| pacienteId | uuid | Paciente registrado (es el `aggregate_id`) |
| consentimiento | enum | otorgado · exencion_emergencia_vital |

- **Productor:** módulo Registro
- **Consumidores:** Auditoría (deja constancia del consentimiento o de la exención)

### vitals.captured · v1

Se emite cuando la enfermera registra los signos vitales de un encuentro.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro al que pertenecen (es el `aggregate_id`) |
| signosVitalesId | uuid | Registro de signos vitales creado |
| medidoEn | date-time | Momento de la medición |

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría (registra los datos ingresados)

### symptoms.reported · v1

Se emite cuando se completa el formulario de síntomas de un encuentro.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro (es el `aggregate_id`) |
| cantidadSintomas | integer | Cuántos síntomas se reportaron |

El texto de los síntomas no viaja en el evento: es texto libre y podría contener datos
personales. Los consumidores lo consultan por `encuentroId`.

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría

### triage.requested · v1

Se emite cuando el caso se envía al motor de IA.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro evaluado (es el `aggregate_id`) |
| evaluacionId | uuid | Evaluación iniciada |

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría

### triage.completed · v1

Se emite cuando el motor de IA entrega la categoría ESI y su justificación a tiempo.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro evaluado (es el `aggregate_id`) |
| evaluacionId | uuid | Evaluación completada |
| categoriaEsi | integer | Categoría sugerida, de 1 a 5 |
| justificacion | object | `resumen` y `factores`, tal como los entregó la IA |
| duracionMs | integer | Cuánto tardó el motor |

La justificación va completa porque el modelo no es determinista: la auditoría guarda la
respuesta exacta que vio la enfermera.

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría (registra la recomendación de la IA)

### triage.confirmed · v1

Se emite cuando se fija la categoría final del encuentro: la enfermera acepta la sugerencia, la
modifica, o la asigna a mano tras una derivación.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro (es el `aggregate_id`) |
| categoriaEsi | integer | Categoría final, de 1 a 5 |
| origen | enum | confirmada_sugerencia_ia · modificada_por_enfermera · asignada_triage_manual |
| confirmadaPor | string | Referencia opaca al profesional que confirmó. Nunca su nombre ni su RUT |

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría (registra la decisión final) · Sala de espera (ubica o reordena al
  paciente en la lista)

### patient.attended · v1

Se emite cuando el médico atiende al paciente.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro atendido (es el `aggregate_id`) |

- **Productor:** módulo Tablero
- **Consumidores:** Auditoría · Sala de espera (saca al paciente de la lista de espera)

### consent.rejected · v1

Se emite cuando un paciente consciente rechaza el consentimiento informado y el registro se
bloquea.

| Campo | Tipo | Descripción |
|---|---|---|
| intentoId | uuid | Identifica el intento rechazado (es el `aggregate_id`). Lo genera el servidor |

No hay paciente ni encuentro: el registro no se creó. El evento no lleva ningún dato de la
persona.

- **Productor:** módulo Registro
- **Consumidores:** Auditoría (el intento queda registrado con la PII enmascarada)

### rut.rejected · v1

Se emite cuando un registro se rechaza porque el dígito verificador del RUT no corresponde al
número.

| Campo | Tipo | Descripción |
|---|---|---|
| intentoId | uuid | Identifica el intento rechazado (es el `aggregate_id`). Lo genera el servidor |
| motivo | enum | digito_verificador_invalido |

El RUT ingresado no viaja en el evento, ni siquiera enmascarado.

- **Productor:** módulo Registro
- **Consumidores:** Auditoría

### vitals.critical_detected · v1

Se emite cuando un signo vital queda en un límite crítico, por ejemplo una saturación de oxígeno
de 85 %. El proceso de categorización continúa.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro (es el `aggregate_id`) |
| signo | enum | presion_arterial · frecuencia_cardiaca · frecuencia_respiratoria · temperatura · saturacion_oxigeno |
| nivel | enum | advertencia · critico |
| umbralAplicado | string | Umbral vigente al momento de la alerta |

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría (registra qué alerta vio la enfermera) · Sala de espera (muestra la
  alerta)

### triage.derived_to_manual · v1

Se emite cuando el caso se deriva a triage manual porque la IA no respondió a tiempo, está caída
o devolvió una respuesta que no se puede interpretar.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro evaluado (es el `aggregate_id`) |
| evaluacionId | uuid | Evaluación derivada |
| motivo | enum | timeout · servicio_no_disponible · respuesta_invalida |
| duracionMs | integer | Cuánto se esperó |

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría (registra la decisión) · Sala de espera (marca el caso como manual)

### triage.category_overridden · v1

Se emite cuando la enfermera confirma una categoría distinta de la que sugirió la IA. Siempre
acompaña a un `triage.confirmed`: este evento deja el motivo del cambio, y el otro, el estado
final.

| Campo | Tipo | Descripción |
|---|---|---|
| encuentroId | uuid | Encuentro (es el `aggregate_id`) |
| evaluacionId | uuid | Evaluación cuya sugerencia se cambió |
| categoriaSugerida | integer | Categoría que propuso la IA |
| categoriaFinal | integer | Categoría que fijó la enfermera |
| justificacionCambio | string | Motivo clínico, obligatorio. Texto libre: no debe incluir nombre ni RUT |
| confirmadaPor | string | Referencia opaca al profesional |

- **Productor:** módulo Evaluación
- **Consumidores:** Auditoría (registra la sobreescritura y su motivo). Sala de espera no lo
  consume: se actualiza con `triage.confirmed`.

### audit.access_denied · v1

Se emite cuando alguien sin el permiso `auditoria:read` intenta consultar el historial de
decisiones.

| Campo | Tipo | Descripción |
|---|---|---|
| intentoId | uuid | Identifica el intento (es el `aggregate_id`). Lo genera el servidor |
| operacion | string | Operación del contrato a la que se intentó acceder |
| scopeRequerido | string | Permiso que faltaba |
| usuarioRef | string | Referencia opaca al usuario autenticado. Nunca su nombre ni su RUT |

- **Productor:** módulo Auditoría
- **Consumidores:** Auditoría (lo registra en el log de seguridad)

## Qué se prueba

La regla *at-least-once* se puede verificar. Para cada consumidor:

- **Idempotencia:** entregar dos veces el mismo `evento_id` produce un solo efecto. En Auditoría
  hay un solo registro; en Sala de espera, una sola entrada.
- **Sin datos personales:** ningún `payload` contiene RUT ni nombre.
- **Sobre completo:** todo evento trae `evento_id`, `tipo`, `version`, `aggregate_id`,
  `trace_id` y `creado_en`.
- **Nombre y versión conocidos:** un consumidor rechaza o aparta un evento de un `tipo` o una
  `version` que no está en este catálogo.
