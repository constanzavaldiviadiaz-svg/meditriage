# Backlog — MediTriage

Historias extraídas del [Impact Map](impact-map.md). Cada una traza hasta el objetivo:
**reducir el tiempo de priorización del triage de 25 minutos a menos de 3 minutos.**

---

## HU01 — Registrar al paciente y capturar sus datos clínicos

**Como** enfermera de triage,
**quiero** registrar al paciente validando su RUT y su consentimiento informado, y capturar
sus síntomas y signos vitales,
**para** que el sistema pueda evaluarlo de inmediato sin que yo transcriba los datos dos veces.

**Prioridad:** Must
**Justificación:** es la entrada de todo el flujo. Sin datos capturados no existe ninguna
otra funcionalidad. Además el consentimiento informado es exigencia legal (Ley 21.719): sin
él no se puede procesar información de salud, así que no es postergable.

---

## HU02 — Obtener una sugerencia de categoría ESI

**Como** enfermera de triage,
**quiero** obtener una sugerencia de categoría ESI (1 a 5) a partir de los síntomas y signos
vitales registrados,
**para** priorizar al paciente en menos de 3 minutos en lugar de los 25 que toma hoy.

**Prioridad:** Must
**Justificación:** es el núcleo del producto y la única historia que produce directamente el
ahorro de tiempo del objetivo. Sin ella, MediTriage no se distingue de una ficha en papel.

---

## HU03 — Ver la justificación de la sugerencia

**Como** enfermera de triage,
**quiero** ver por qué el sistema asignó esa categoría ESI,
**para** validar o descartar la sugerencia en menos de 30 segundos, sin rehacer la evaluación.

**Prioridad:** Must
**Justificación:** dos razones. Primero, la explicabilidad es una restricción de ingeniería
obligatoria del enunciado, al mismo nivel que el cifrado o la latencia. Segundo, y más
importante: sin justificación la enfermera —que es la responsable clínica de la decisión—
tendría que evaluar igual desde cero, y el ahorro de tiempo de HU02 desaparecería. HU03 es
lo que hace que HU02 cumpla el objetivo.

---

## HU04 — Ver el tablero de pacientes priorizados

**Como** médico jefe de turno,
**quiero** ver a los pacientes de la sala de espera ordenados por su categoría ESI y
actualizados a medida que ingresan casos nuevos,
**para** decidir a quién atender primero sin reordenar la lista manualmente.

**Prioridad:** Should
**Justificación:** el tablero mejora la coordinación del turno completo, pero la priorización
individual de cada paciente ya funciona sin él (HU02 y HU03). Es importante, no bloqueante:
la entrega sigue siendo utilizable si llega después.

---

## HU05 — Auditar las recomendaciones realizadas

**Como** auditor clínico,
**quiero** consultar el historial de recomendaciones con su justificación y su fecha,
**para** verificar que las decisiones de IA cumplieron la normativa vigente.

**Prioridad:** Should
**Justificación:** el enunciado exige que cada decisión quede registrada e inmutable por 5
años, y ese registro debe existir desde la primera versión. Pero la **pantalla de consulta**
del auditor puede llegar después del registro mismo: mientras los datos se guarden
correctamente, la auditoría es posible aunque la interfaz no esté lista.

> Nota: el registro de cada decisión no es negociable y está incluido como criterio de
> aceptación de HU02 y HU03. Lo priorizado como *Should* aquí es la pantalla de consulta.

---

## HU06 — Derivar a triage manual cuando el sistema no responde

**Como** enfermera de triage,
**quiero** que el caso se derive automáticamente a triage manual cuando el motor de IA falle
o demore más de 3 segundos,
**para** seguir atendiendo sin quedarme esperando una respuesta que no llega.

**Prioridad:** Must
**Justificación:** el enunciado fija la latencia máxima en 3 segundos. En un contexto de
urgencia, un sistema que se cuelga sin alternativa es peor que no tener sistema: bloquea a
la persona que debe decidir. Es la historia que hace que MediTriage sea clínicamente seguro
de usar.

---

## Priorización MoSCoW — resumen

| Historia | Prioridad | Razón en una línea |
|---|---|---|
| HU01 Registrar paciente | **Must** | Entrada del flujo + exigencia legal |
| HU02 Sugerencia ESI | **Must** | Núcleo del producto y del objetivo |
| HU03 Justificación | **Must** | Sin ella, HU02 no ahorra tiempo |
| HU06 Derivación a triage manual | **Must** | Seguridad clínica ante fallo |
| HU04 Tablero priorizado | **Should** | Mejora la coordinación, no bloquea |
| HU05 Consulta de auditoría | **Should** | El registro es Must; la pantalla puede esperar |

### Fuera de alcance de esta entrega (Won't)

Decisiones explícitas de **no** construir, para acotar el alcance:

- **Integración con la ficha clínica del centro de salud.** Requiere convenios y acceso a
  sistemas externos que el equipo no tiene.
- **Aplicación para el paciente.** El paciente es afectado por el sistema, pero no es usuario
  del MVP: el triage lo opera personal clínico.
- **Reentrenamiento del modelo con los datos capturados.** Implica MLOps y consideraciones
  de datos sensibles que exceden esta entrega.

---

## Discovery

**Técnica aplicada:** Assumption Mapping (mapeo de supuestos).

**Por qué esta técnica y no una entrevista.** El equipo no tiene acceso a un centro de
atención primaria ni a personal de triage en ejercicio, así que no se realizaron entrevistas
a usuarios reales. Antes que documentar una entrevista que no ocurrió, se aplicó Assumption
Mapping, cuyo propósito es exactamente este: **hacer explícitos los supuestos que sostienen
el backlog, ordenarlos por riesgo y evidencia, y definir qué hay que validar primero.**

**Fuentes utilizadas:** el contexto de negocio y las restricciones de ingeniería de la
iniciativa entregada por el docente.

### Supuestos identificados

| # | Supuesto | Riesgo | ¿Hay evidencia? | Historia afectada |
|---|---|---|---|---|
| S1 | La enfermera aceptará validar una sugerencia de IA en vez de evaluar por su cuenta | **Alto** | No | HU02, HU03 |
| S2 | Una justificación generada por el modelo será comprensible para personal clínico sin formación técnica | **Alto** | No | HU03 |
| S3 | El consentimiento informado puede obtenerse antes del triage sin retrasar la atención de urgencia | **Alto** | No | HU01 |
| S4 | Los signos vitales están disponibles al momento del triage, no después | Medio | No | HU01, HU02 |
| S5 | El proceso manual actual toma cerca de 25 minutos | Medio | Sí, del contexto de la iniciativa | Objetivo |
| S6 | 3 segundos de respuesta es suficiente para no interrumpir el flujo de atención | Bajo | Sí, del enunciado | HU06 |

### Qué validar primero

Los supuestos de **riesgo alto y sin evidencia** son los que pueden invalidar el producto
completo: **S1, S2 y S3**.

S3 es el más delicado y merece atención temprana: si en una urgencia grave no es viable
solicitar consentimiento antes de atender, HU01 tal como está redactada no funciona en el
mundo real y habría que replantear el flujo.

**Próximo paso propuesto:** validar S1 y S2 con una entrevista breve a una persona con
formación clínica, aunque no sea del centro de salud objetivo.
