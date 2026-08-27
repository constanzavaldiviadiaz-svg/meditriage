# Impact Map — MediTriage

## Objetivo

**Reducir el tiempo de priorización del triage de 25 minutos a menos de 3 minutos.**

Se mide como el tiempo transcurrido entre que el paciente entrega sus síntomas y signos
vitales, y queda con una categoría ESI asignada y validada por la enfermera de triage.

La cifra de 25 minutos es la línea base del proceso manual actual descrito en el contexto de
negocio de la iniciativa.

## Actores

Dos actores clave, ambos con historias asociadas en el backlog:

| Actor | Por qué es clave |
|---|---|
| **Enfermera de triage** | Es quien ejecuta hoy la priorización manual. Es el actor cuyo cambio de comportamiento produce directamente el ahorro de tiempo del objetivo. |
| **Auditor clínico** | El enunciado exige que cada decisión de IA quede registrada e inmutable por 5 años. Sin este actor, la trazabilidad no tiene destinatario. |

El **paciente** y el **médico jefe de turno** aparecen en el contexto de la iniciativa, pero
no se incluyen como actores de este mapa: en el alcance actual no cambian su comportamiento
ni tienen historias asociadas. Se incorporarán cuando exista una historia que los involucre.

## Impactos

Un impacto es un **cambio de comportamiento en un actor**, no una función del sistema.

### Enfermera de triage

- **Deja de evaluar desde cero**: pasa a validar una sugerencia ESI ya justificada, en unos
  30 segundos, en lugar de construir la evaluación completa.
- **Deja de reordenar la sala de espera manualmente**: la lista de pacientes se reordena sola
  a medida que ingresan casos más graves.
- **Deja de quedarse esperando cuando el sistema falla**: si el motor de IA no responde
  dentro de 3 segundos, el caso se enruta a triage manual y ella sigue trabajando.

### Auditor clínico

- **Deja de solicitar datos a terceros**: consulta por su cuenta el historial de
  recomendaciones y su justificación.

## Entregables

Cada entregable apunta a un impacto concreto. Si un entregable no puede trazarse hasta un
impacto, se elimina.

| Entregable | Impacto al que sirve | Historia |
|---|---|---|
| Formulario de síntomas y signos vitales, con validación de RUT | Habilita que la enfermera deje de evaluar desde cero | HU01 |
| Motor de sugerencia de categoría ESI (1–5) | La enfermera valida en vez de evaluar | HU02 |
| Justificación explicable de cada sugerencia | Sin justificación la enfermera no puede validar: volvería a evaluar desde cero | HU03 |
| Tablero de pacientes ordenados por prioridad | La enfermera deja de reordenar la sala manualmente | HU04 |
| Audit log consultable de cada recomendación | El auditor deja de pedir datos a terceros | HU05 |
| Derivación automática a triage manual ante fallo o demora | La enfermera no queda bloqueada cuando el sistema falla | *sin historia* |

## Trazabilidad: del objetivo a la historia

| Historia | Entregable | Impacto | Contribución al objetivo |
|---|---|---|---|
| HU01 Registrar información del paciente | Formulario validado | Captura estructurada en lugar de anotación libre | Elimina la transcripción manual previa |
| HU02 Obtener prioridad | Motor de sugerencia ESI | Validar en 30 s en vez de evaluar desde cero | Es el ahorro principal: de 25 min a menos de 3 |
| HU03 Ver explicación | Justificación explicable | Permite validar rápido y con confianza | Sin esto, HU02 no reduce el tiempo real |
| HU04 Ver pacientes priorizados | Tablero priorizado | No reordenar la sala a mano | Reduce el tiempo entre pacientes |
| HU05 Revisar historial | Audit log | El auditor se autoatiende | No reduce el tiempo, pero es requisito legal del MVP |

## Observaciones para el equipo

1. **HU05 no debería estar priorizada como "Won't".** El MVP del enunciado incluye
   trazabilidad y audit log de cada recomendación, y la restricción de ingeniería exige que
   cada decisión quede registrada e inmutable por 5 años. Marcarla fuera de alcance
   contradice el enunciado.

2. **HU03 debería ser "Must", no "Should".** La explicabilidad es una restricción de
   ingeniería obligatoria del enunciado, y además es la que hace que HU02 sirva de algo: sin
   justificación, la enfermera vuelve a evaluar desde cero y el ahorro de tiempo desaparece.

3. **Falta una historia para la derivación a triage manual.** Es el único entregable de este
   mapa sin historia asociada, y responde a una restricción explícita del enunciado: la
   respuesta debe llegar en menos de 3 segundos. Aplicando la regla de oro, o se crea la
   historia o se elimina el entregable.

4. **HU02 no cumple INVEST.** "Obtener el nivel de prioridad" es el motor de IA completo en
   una sola historia: no es pequeña ni estimable sin un modelo definido. Debería partirse.
