# Backlog — MediTriage

Historias extraídas del [Impact Map](impact-map.md). Cada una traza hasta el objetivo:
**reducir el tiempo de priorización del triage de 25 minutos a menos de 3 minutos.**

Cada historia tiene sus criterios de aceptación en el archivo `.feature` del mismo número.

La trazabilidad de cada historia hasta el objetivo está en la tabla del
[Impact Map](impact-map.md#trazabilidad-del-objetivo-a-la-historia).

---

## HU01 — Registrar al paciente con consentimiento informado

**Como** enfermera de triage,
**quiero** registrar al paciente validando su RUT y dejando constancia de su consentimiento
informado,
**para** iniciar su atención de forma legal sin abrir un trámite paralelo en papel.

**Prioridad:** Must
**Justificación:** es la entrada de todo el flujo y además una exigencia legal. La Ley 21.719
no permite procesar información de salud sin consentimiento: sin esta historia el sistema no
puede operar legalmente.

---

## HU02 — Capturar síntomas y signos vitales

**Como** enfermera de triage,
**quiero** registrar los síntomas y los signos vitales del paciente en un formulario validado,
**para** que el sistema disponga de la información sin que yo la transcriba dos veces.

**Prioridad:** Must
**Justificación:** el motor de IA no puede sugerir nada sin estos datos. Se separa de HU01
porque son dos momentos distintos de la atención —la admisión y la evaluación clínica— y
juntarlas hacía la historia demasiado grande para estimarla.

---

## HU03 — Obtener una sugerencia de categoría ESI con su justificación

**Como** enfermera de triage,
**quiero** recibir una sugerencia de categoría ESI (1 a 5) acompañada de la explicación de los
factores que la determinaron,
**para** validar o descartar la priorización en menos de 30 segundos, en lugar de construir la
evaluación completa.

**Prioridad:** Must
**Justificación:** es el núcleo del producto y la única historia que produce directamente el
ahorro de tiempo del objetivo.

La sugerencia y su explicación van juntas porque el enunciado las define como una sola pieza:
el motor de IA sugiere la categoría ESI y explica el porqué. Además no funcionan por
separado: sin justificación, la enfermera —que es la responsable clínica de la decisión—
tendría que evaluar igual desde cero, y el ahorro desaparecería.

> **Riesgo conocido:** es la historia más grande del backlog y la más difícil de estimar,
> porque depende de un modelo que aún no existe. Es candidata a partirse durante la
> planificación del sprint.

---

## HU04 — Ver el tablero de pacientes priorizados

**Como** médico jefe de turno,
**quiero** ver a los pacientes de la sala ordenados por categoría ESI y actualizados cuando
alguien se reevalúa,
**para** decidir a quién atender primero sin reordenar la lista manualmente.

**Prioridad:** Should
**Justificación:** mejora la coordinación del turno completo, pero la priorización individual
de cada paciente ya funciona sin él. La entrega sigue siendo utilizable si llega después.

---

## HU05 — Auditar las recomendaciones realizadas

**Como** auditor clínico,
**quiero** consultar el historial inmutable de decisiones con su justificación y su fecha,
**para** verificar que las decisiones de IA cumplieron la normativa vigente.

**Prioridad:** Should
**Justificación:** el enunciado exige que cada decisión quede registrada e inmutable por 5
años, y ese registro debe existir desde la primera versión. Pero la **pantalla de consulta**
del auditor puede llegar después: mientras los datos se guarden correctamente, la auditoría
es posible aunque la interfaz no esté lista.

> **Nota:** el registro de cada decisión no es negociable y está incluido como criterio de
> aceptación de HU03. Lo priorizado como *Should* aquí es la pantalla de consulta.

---

## HU06 — Derivar a triage manual cuando el sistema no responde

**Como** enfermera de triage,
**quiero** que el caso pase automáticamente a triage manual cuando el motor de IA falle o
demore más de 3 segundos,
**para** seguir atendiendo sin quedarme esperando una respuesta que no llega.

**Prioridad:** Must
**Justificación:** el enunciado fija la latencia máxima en 3 segundos. En urgencias, un
sistema que se cuelga sin alternativa es peor que no tener sistema: bloquea a la persona que
debe decidir. Es la historia que hace que MediTriage sea clínicamente seguro de usar.

---

## Priorización MoSCoW — resumen

| Historia | Prioridad | Razón en una línea |
|---|---|---|
| HU01 Registro con consentimiento | **Must** | Entrada del flujo y exigencia legal |
| HU02 Síntomas y signos vitales | **Must** | Sin datos el motor no puede sugerir nada |
| HU03 Sugerencia ESI con justificación | **Must** | Núcleo del producto y del objetivo |
| HU06 Derivación a triage manual | **Must** | Seguridad clínica ante fallo |
| HU04 Tablero priorizado | **Should** | Mejora la coordinación, no bloquea |
| HU05 Consulta de auditoría | **Should** | El registro es Must; la pantalla puede esperar |

### Fuera de alcance de esta entrega

Decisiones explícitas de no construir, para acotar el alcance:

- **Integración con la ficha clínica del centro de salud.** Requiere convenios y acceso a
  sistemas externos que el equipo no tiene.
- **Aplicación para el paciente.** El paciente es afectado por el sistema, pero no es usuario
  del MVP: el triage lo opera personal clínico.
- **Reentrenamiento del modelo con los datos capturados.** Implica MLOps y consideraciones de
  datos sensibles que exceden esta entrega.

---

---

## Checklist INVEST

Cada historia se revisó contra las seis condiciones. Se documentan también las que **no**
cumplen: una historia con una debilidad conocida y una decisión asociada es más útil que una
lista donde todo aparece perfecto.

| Historia | I | N | V | E | S | T |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| HU01 Registro con consentimiento | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HU02 Síntomas y signos vitales | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| HU03 Sugerencia ESI con justificación | ⚠️ | ✅ | ✅ | ❌ | ❌ | ✅ |
| HU04 Tablero priorizado | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HU05 Auditoría de recomendaciones | ⚠️ | ✅ | ✅ | ⚠️ | ❌ | ✅ |
| HU06 Derivación a triage manual | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ✅ |

✅ cumple · ⚠️ cumple con reservas · ❌ no cumple

### Lo que no cumple, y qué decidimos

**Independent — es la letra más débil de todo el backlog.**
Existe una cadena natural: no se pueden tomar signos vitales de un paciente sin registrar, ni
sugerir una categoría ESI sin datos clínicos. Los propios escenarios lo reflejan: `hu02`
empieza con *"Given un paciente previamente registrado"*.

*Decisión:* se acepta. En INVEST, "Independent" apunta a evitar acoplamientos arbitrarios que
obliguen a entregar varias historias juntas, no a negar un orden lógico del dominio. Cada
historia se puede desarrollar y demostrar por separado usando datos de prueba.

**HU03 — no es Estimable ni Small.**
Concentra el motor de IA completo. No se puede estimar su esfuerzo sin saber qué modelo se
usará ni con qué datos, y no cabe en dos o tres días.

*Decisión:* no se parte todavía. Dividirla hoy sería inventar una separación sin base
técnica: el stack no está decidido y la arquitectura se define en la S03. Queda marcada como
candidata a partirse en la planificación del sprint, una vez tomada esa decisión.

**HU05 — no es Small, y su estimación es dudosa.**
Mezcla dos cosas de tamaño muy distinto: el registro inmutable con retención de 5 años, que
es infraestructura, y la pantalla donde el auditor consulta.

*Decisión:* se parte cuando se defina el almacenamiento, en la S06. El registro inmutable es
Must y ya está como criterio de aceptación de HU03; lo priorizado aquí como Should es la
pantalla de consulta.

**HU06 — Estimable con reservas.**
Depende del mismo motor de IA no definido de HU03, aunque su alcance sí es pequeño.

*Decisión:* se acepta. El comportamiento a construir —cortar la espera a los 3 segundos y
derivar— es claro aunque el motor todavía no exista.

**HU02 — Valuable con reservas.**
Capturar síntomas sin que nadie los evalúe aporta poco por sí solo; su valor se realiza junto
con HU03.

*Decisión:* se mantiene separada. Elimina la transcripción manual duplicada, que es un
beneficio propio, y unirla a HU03 haría esa historia todavía más grande.

### Lo que sí cumple sin reservas

**Testable es la letra más fuerte: 6 de 6.** Las seis historias tienen tres escenarios Gherkin
cada una —caso feliz, borde y error— en `docs/scenarios/`. Son 18 criterios verificables.

**Negotiable también, 6 de 6.** Ninguna historia está redactada como especificación cerrada:
todas describen una capacidad y un beneficio, dejando abierto el cómo.

## Discovery

**Técnica aplicada:** Assumption Mapping (mapeo de supuestos).

**Por qué esta técnica y no una entrevista.** El equipo no tiene acceso a un centro de
atención primaria ni a personal de triage en ejercicio, así que no se realizaron entrevistas
a usuarios reales. Antes que documentar una entrevista que no ocurrió, se aplicó Assumption
Mapping, cuyo propósito es exactamente este: hacer explícitos los supuestos que sostienen el
backlog, ordenarlos por riesgo y evidencia, y definir qué hay que validar primero.

**Fuentes utilizadas:** el contexto de negocio y las restricciones de ingeniería de la
iniciativa entregada por el docente.

### Supuestos identificados

| # | Supuesto | Riesgo | ¿Hay evidencia? | Historia afectada |
|---|---|---|---|---|
| S1 | La enfermera aceptará validar una sugerencia de IA en vez de evaluar por su cuenta | **Alto** | No | HU03 |
| S2 | Una justificación generada por el modelo será comprensible para personal clínico sin formación técnica | **Alto** | No | HU03 |
| S3 | El consentimiento informado puede obtenerse antes del triage sin retrasar la atención de urgencia | **Alto** | No | HU01 |
| S4 | Los signos vitales están disponibles al momento del triage, no después | Medio | No | HU02 |
| S5 | El proceso manual actual toma cerca de 25 minutos | Medio | Sí, del contexto de la iniciativa | Objetivo |
| S6 | 3 segundos de respuesta es suficiente para no interrumpir el flujo de atención | Bajo | Sí, del enunciado | HU06 |

### Qué validar primero

Los supuestos de **riesgo alto y sin evidencia** son los que pueden invalidar el producto
completo: **S1, S2 y S3**.

S3 es el más delicado. El escenario de registro de un paciente inconsciente en
`hu01.feature` propone una salida —la exención por emergencia vital— pero esa salida necesita
un respaldo normativo que el equipo todavía no ha verificado.

**Próximo paso propuesto:** validar S1 y S2 con una entrevista breve a una persona con
formación clínica, aunque no sea del centro de salud objetivo.
