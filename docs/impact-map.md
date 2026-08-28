# Impact Map — MediTriage

## Objetivo

**Reducir el tiempo de priorización del triage de 25 minutos a menos de 3 minutos.**

Se mide como el tiempo transcurrido entre que el paciente entrega sus síntomas y signos
vitales, y queda con una categoría ESI asignada y validada por la enfermera de triage.

La cifra de 25 minutos es la línea base del proceso manual actual descrito en el contexto de
negocio de la iniciativa. No proviene de una medición hecha por el equipo.

## Actores

Tres actores, todos con historias asociadas en el [backlog](backlog.md):

| Actor | Por qué es clave | Historias |
|---|---|---|
| **Enfermera de triage** | Ejecuta hoy la priorización manual. Es el actor cuyo cambio de comportamiento produce directamente el ahorro de tiempo del objetivo. | HU01, HU02, HU03, HU06 |
| **Médico jefe de turno** | Gestiona la sala de espera completa. Su decisión de a quién atender primero depende de que la priorización esté visible y actualizada. | HU04 |
| **Auditor clínico** | El enunciado exige que cada decisión de IA quede registrada e inmutable por 5 años. Sin este actor, la trazabilidad no tiene destinatario. | HU05 |

El **paciente** aparece en el contexto de la iniciativa, pero no se incluye como actor de
este mapa: en el alcance actual no cambia su comportamiento —entrega sus síntomas igual que
antes— ni opera el sistema. Se incorporará cuando exista una historia que lo involucre
directamente.

## Impactos

Un impacto es un **cambio de comportamiento en un actor**, no una función del sistema.

### Enfermera de triage

- **Deja de evaluar desde cero**: pasa a validar una sugerencia ESI ya justificada, en unos
  30 segundos, en lugar de construir la evaluación completa.
- **Deja de quedarse esperando cuando el sistema falla**: si el motor de IA no responde
  dentro de 3 segundos, el caso se enruta a triage manual y ella sigue trabajando.

### Médico jefe de turno

- **Deja de reordenar la sala de espera manualmente**: la lista se reordena sola a medida que
  ingresan casos más graves o se reevalúa a un paciente.

### Auditor clínico

- **Deja de solicitar datos a terceros**: consulta por su cuenta el historial de
  recomendaciones y su justificación.

## Entregables

Cada entregable apunta a un impacto concreto. Si un entregable no puede trazarse hasta un
impacto, se elimina.

| Entregable | Impacto al que sirve | Historia |
|---|---|---|
| Registro del paciente con validación de RUT y consentimiento informado | Permite iniciar la atención de forma legal, sin trámite paralelo | HU01 |
| Formulario de síntomas y captura de signos vitales | Habilita que la enfermera deje de evaluar desde cero | HU02 |
| Motor de sugerencia de categoría ESI (1–5) con su justificación explicable | La enfermera valida en vez de evaluar. Sin justificación volvería a evaluar desde cero | HU03 |
| Tablero de pacientes ordenados por categoría ESI, con actualización dinámica | El médico jefe deja de reordenar la sala manualmente | HU04 |
| Audit log consultable e inmutable de cada recomendación | El auditor deja de pedir datos a terceros | HU05 |
| Derivación automática a triage manual ante fallo o demora mayor a 3 segundos | La enfermera no queda bloqueada cuando el sistema falla | HU06 |

## Trazabilidad: del objetivo a la historia

| Historia | Entregable | Impacto | Contribución al objetivo |
|---|---|---|---|
| **HU01** Registrar al paciente con consentimiento informado | Registro con validación de RUT y consentimiento | Permite iniciar la atención sin trámite paralelo en papel | Elimina la admisión manual previa |
| **HU02** Capturar síntomas y signos vitales | Formulario validado de síntomas y signos vitales | Captura estructurada en lugar de anotación libre | Elimina la transcripción manual de los datos clínicos |
| **HU03** Obtener una sugerencia de categoría ESI con su justificación | Motor de sugerencia ESI con explicación | Validar en 30 s en vez de evaluar desde cero | Es el ahorro principal: de 25 min a menos de 3 |
| **HU04** Ver el tablero de pacientes priorizados | Tablero dinámico | El médico jefe no reordena la sala a mano | Reduce el tiempo muerto entre pacientes |
| **HU05** Auditar las recomendaciones realizadas | Audit log consultable | El auditor se autoatiende | No reduce el tiempo, pero es requisito legal del MVP |
| **HU06** Derivar a triage manual cuando el sistema no responde | Derivación automática ante fallo o demora | La enfermera no queda bloqueada | Protege el objetivo: sin esto, un fallo devuelve el proceso a los 25 minutos |

## Supuestos pendientes de validación

El [Discovery](backlog.md#discovery) identificó seis supuestos mediante Assumption Mapping.
Los tres de riesgo alto y sin evidencia afectan directamente a este mapa:

- **S1** — que la enfermera acepte validar una sugerencia de IA en vez de evaluar por su
  cuenta. Si no ocurre, el impacto principal no se produce y el objetivo no se alcanza.
- **S2** — que la justificación generada sea comprensible para personal clínico sin formación
  técnica.
- **S3** — que el consentimiento informado pueda obtenerse antes de atender una urgencia
  grave.

Mientras no se validen, el ahorro de 25 a 3 minutos es una hipótesis, no una proyección.
