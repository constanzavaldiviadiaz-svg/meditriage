# ADR 0002 — Elección del estilo arquitectónico

## Estado

Propuesto — 25/09/2026

Pasa a *Aceptado* cuando el equipo apruebe el Pull Request correspondiente.

## Autores

Fernando Ureta (Tech Lead · AI/Data Lead)

## Contexto

MediTriage debe entregar una categoría ESI en **menos de 3 segundos**, con **99.5%** de
disponibilidad mensual, **justificando cada decisión**, y conservando un **audit log
inmutable por 5 años** bajo las leyes 19.628 y 21.719.

El equipo son **cuatro estudiantes**, ninguno con experiencia previa operando sistemas
distribuidos. El enunciado de la sesión lo plantea explícitamente con la Ley de Conway:
*"elige el estilo que tu equipo pueda operar"*.

El flujo principal del producto es **sincrónico**: la enfermera de triage ingresa los datos
del paciente y espera la sugerencia en pantalla para validarla.

## Decisión

**Monolito modular**, organizado en cuatro módulos con fronteras explícitas:

| Módulo | Responsabilidad | Historias |
|---|---|---|
| Registro | Admisión del paciente, validación de RUT, consentimiento informado | HU01 |
| Evaluación | Captura clínica, llamada al motor de IA, derivación a triage manual | HU02, HU03, HU06 |
| Tablero | Priorización dinámica de la sala de espera | HU04 |
| Auditoría | Registro inmutable y consulta del historial de decisiones | HU05 |

Dos definiciones acompañan la decisión:

1. **El motor de IA es un servicio externo**, consumido vía API. No se entrena un modelo
   propio.
2. **La escritura del audit log es asíncrona**, para no consumir presupuesto de los 3
   segundos en una operación que el usuario no necesita esperar.

## Consecuencias

### Positivas

- **Operable por cuatro personas.** Un solo despliegue, sin orquestación de servicios ni red
  entre componentes como punto de falla.
- **Transacciones ACID naturales** en el registro del paciente y su consentimiento, que es
  donde la consistencia importa legalmente.
- **La explicabilidad viene incluida.** El enunciado exige que el modelo justifique cada
  priorización; un servicio de IA devuelve esa justificación en lenguaje natural sin trabajo
  adicional de interpretabilidad.
- **Es la ruta pragmática** que recomienda el docente: empezar simple y extraer módulos
  cuando duela, descubriendo los límites del dominio sin distribución prematura.

### Negativas

- **Escalabilidad acoplada.** Todo escala junto, aunque solo el módulo de Evaluación reciba
  carga.
- **Exige disciplina de módulos.** Si el monolito no es realmente modular, extraer después
  resulta doloroso.
- **Los 3 segundos pasan a depender de un tercero.** La latencia ya no está bajo nuestro
  control: por eso **HU06 deja de ser deseable y pasa a ser obligatoria**.
- **Los datos clínicos salen del sistema.** Obliga a despersonalizar antes de cada llamada:
  al servicio externo se envían síntomas y signos vitales, **nunca RUT ni nombre**. Es
  requisito de la Ley 19.628.
- **Las respuestas no son deterministas.** La misma entrada puede producir textos distintos,
  así que el audit log debe guardar la respuesta exacta entregada; no se puede confiar en
  reproducirla más tarde.
- **Costo por request**, que habrá que dimensionar al llegar a FinOps (S15).

## Alternativas descartadas

### Microservicios desde el día 0

Complejidad operacional excesiva para cuatro estudiantes sin experiencia previa en operación.
Introduce la red como punto único de falla y consistencia eventual en un dominio donde el
registro del paciente requiere garantías transaccionales. Ley de Conway: el equipo no puede
operar lo que no sabe operar.

### Serverless puro

Los *cold starts* son incompatibles con el límite de 3 segundos, que ya está comprometido por
la llamada al servicio de IA. Además, el modelo de costos por uso se justifica con carga
irregular, y el triage en una sala de urgencias tiene carga sostenida durante el horario de
atención.

### Event-driven completo

El triage es sincrónico por naturaleza: la enfermera espera la respuesta en pantalla para
validarla. El desacoplamiento no aporta valor al flujo principal y dificulta rastrear el
recorrido de una decisión, justo lo contrario de lo que exige la auditoría del proyecto.

Se conserva event-driven **solo** para la escritura del audit log, donde sí aplica: nadie
espera a que ese registro termine.

### Modelo de IA propio

El equipo no tiene datos de entrenamiento ni forma legal de obtenerlos: historiales clínicos
reales están protegidos por las mismas leyes que el proyecto debe cumplir. Además, la
explicabilidad exigiría implementar interpretabilidad por separado, que es un proyecto en sí
mismo.

### Motor de reglas ESI puro, sin IA

Técnicamente viable: el ESI es un protocolo con un algoritmo de decisión definido, lo que
daría un sistema determinista, rápido y sin sacar datos del perímetro — resolviendo de una
vez los tres problemas más difíciles de esta decisión.

Se descarta porque el enunciado de la iniciativa pide explícitamente un motor de IA que
sugiera y explique. **Queda registrado como plan de contingencia**: si la latencia del
servicio externo resulta inviable frente al límite de 3 segundos, esta es la alternativa a
evaluar antes que relajar el requisito.

## Revisión futura

Esta decisión se revisará si ocurre alguno de estos disparadores:

- El servicio externo de IA supera sistemáticamente los 3 segundos.
- El módulo de Auditoría requiere escalar o aislarse por volumen de retención.
- El equipo crece o se incorpora experiencia en operación de sistemas distribuidos.

Un ADR no se edita: si la decisión cambia, este se marca como *Reemplazado* y se escribe uno
nuevo.
