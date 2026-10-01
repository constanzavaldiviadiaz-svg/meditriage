# Trazabilidad historias ↔ contenedores (C4 nivel 2)

**Responsable:** Matías Casa (QA Lead)
**Depende de:** issue #31 (C4 nivel 2) · [`docs/c4/l2-container.puml`](../c4/l2-container.puml)
**Fuentes cruzadas:** [`backlog.md`](../backlog.md) · [`docs/scenarios/*.feature`](../scenarios/) · [ADR 0002](../adr/0002-estilo-arquitectonico.md) · [`atributos-calidad.md`](atributos-calidad.md)

## Qué es

Verificación de cobertura, en las dos direcciones, entre el backlog y la arquitectura:

- cada historia debe tener al menos un contenedor que la implemente;
- cada contenedor debe servir a al menos una historia.

Es la misma lógica de la regla de oro del Impact Map, un nivel más abajo.

**Criterio de "implementa":** un contenedor implementa una historia si es necesario para cumplir alguno de sus escenarios Gherkin. Se usan los escenarios y no solo el texto de la historia, porque varios criterios de aceptación (por ejemplo, "queda registrado en el audit log") arrastran contenedores que la historia no menciona.

## Contenedores considerados

| Id | Contenedor | Tecnología | Rol |
|---|---|---|---|
| C1 | Aplicación web | FastAPI + Jinja2 (monolito modular) | Interfaz y módulos Registro, Evaluación, Tablero y Auditoría |
| C2 | Base de datos clínica | PostgreSQL | Pacientes, consentimientos, signos vitales, evaluaciones |
| C3 | Cola de auditoría | Redis | Desacopla el registro de la decisión de la respuesta al usuario |
| C4 | Worker de auditoría | Python | Consume la cola y persiste cada decisión |
| C5 | Almacén de auditoría | PostgreSQL (append-only) | Registro inmutable, retención de 5 años |

El **Servicio de IA** y el **Registro Civil** son sistemas externos: no son contenedores y no se cuentan en la cobertura, pero se anotan porque la historia depende de ellos.

## Tabla historia → contenedor

| Historia | Prioridad | Contenedores que la implementan | Externos |
|---|---|---|---|
| HU01 Registro con consentimiento | Must | C1 (módulo Registro) · C2 · C3 · C4 · C5 | Registro Civil |
| HU02 Síntomas y signos vitales | Must | C1 (módulo Evaluación) · C2 | — |
| HU03 Sugerencia ESI con justificación | Must | C1 (módulo Evaluación) · C2 · C3 · C4 · C5 | Servicio de IA |
| HU04 Tablero de pacientes priorizados | Should | C1 (módulo Tablero) · C2 | — |
| HU05 Auditoría de recomendaciones | Should | C1 (módulo Auditoría) · C5 (lectura) · C3 · C4 (escritura) | — |
| HU06 Derivación a triage manual | Must | C1 (módulo Evaluación) · C3 · C4 · C5 | Servicio de IA |

Por qué C3, C4 y C5 aparecen en HU01, HU03 y HU06: sus escenarios exigen "queda registrado en el audit log" (HU01 esc. 1 y 2; HU03 esc. 1 y 2; HU06 esc. 1 y 3). HU02 y HU04 no tienen escenarios de auditoría.

## Tabla inversa contenedor → historia

| Contenedor | HU01 | HU02 | HU03 | HU04 | HU05 | HU06 | Nº historias |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| C1 Aplicación web | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | 6 |
| C2 Base de datos clínica | ✔ | ✔ | ✔ | ✔ | | | 4 |
| C3 Cola de auditoría | ✔ | | ✔ | | ✔ | ✔ | 4 |
| C4 Worker de auditoría | ✔ | | ✔ | | ✔ | ✔ | 4 |
| C5 Almacén de auditoría | ✔ | | ✔ | | ✔ | ✔ | 4 |

## Huecos

### A. Historia sin contenedor

**Ninguna historia queda sin contenedor.** Las seis tienen al menos uno.

Sin embargo, al bajar a los escenarios aparecen **capacidades exigidas que ningún contenedor del diagrama tiene como dueño explícito**:

| # | Capacidad | Dónde se exige | Qué falta |
|---|---|---|---|
| A1 | **Alerta al equipo de plataforma** cuando el servicio de IA está caído | HU06 esc. 3 · atributo Observabilidad (monitoreo, logging estructurado, health checks) | No hay ningún componente de monitoreo/alertas en el diagrama. Es el hueco más relevante: un criterio de aceptación Must no tiene dónde ejecutarse. |
| A2 | **Autenticación y roles** (enfermera, médico, auditor) y **log de seguridad** de accesos denegados | HU05 esc. 3 | No aparece quién autentica ni dónde se guarda el log de seguridad (que además es distinto del audit log de decisiones). |
| A3 | **Canal en tiempo real** (WebSocket) del tablero | HU04 esc. 2 y 3 | La relación médico → C1 está dibujada solo como HTTPS. No es un contenedor nuevo, pero el diagrama no refleja el protocolo. |
| A4 | **Mecanismo de "firma digital de inmutabilidad"** | HU05 esc. 1 | C5 es "append-only", pero nada indica cómo se firma o verifica la integridad. |

Propuesta (la decide el Tech Lead): A1 y A2 se resuelven, o bien agregando un contenedor/sistema (monitoreo y proveedor de identidad), o bien declarando explícitamente que son responsabilidad transversal de C1 y de la infraestructura. Lo que no conviene es dejarlo implícito, porque HU06 depende de A1.

### B. Contenedor sin historia

**Ningún contenedor queda huérfano**: los cinco sirven a al menos cuatro historias (ver tabla inversa). No sobra nada.

Pero hay una **trazabilidad indirecta** que conviene dejar a la vista:

- **C3, C4 y C5 no tienen una historia cuyo propósito principal sea el registro inmutable.** Hoy se justifican por los criterios de aceptación de HU01, HU03 y HU06, y por la mitad de escritura de HU05.
- El [backlog](../backlog.md) ya reconoce que HU05 mezcla dos cosas: el registro inmutable (Must, infraestructura) y la pantalla de consulta (Should), y que se parte en la S06.
- **Riesgo:** HU05 está marcada como *Should*. Si alguien recorta HU05 por prioridad, podría recortar también C5 sin notar que el registro es Must. Es el mismo patrón que hizo aparecer HU06: un componente que el diseño exige sin una historia que lo respalde.

Propuesta (la decide la PO): al partir HU05, dar al registro inmutable su propia historia Must, para que C3, C4 y C5 queden trazados a una historia directa.

## Testabilidad de la arquitectura

**Veredicto general:** la arquitectura es testeable contenedor por contenedor, **siempre que las dependencias queden detrás de interfaces** que se puedan reemplazar por dobles de prueba. Los puntos que solo se pueden probar "todos juntos" están concentrados en la cadena de auditoría y en el módulo Evaluación.

### Por contenedor

| Contenedor | ¿Se prueba aislado? | Cómo | Riesgo |
|---|---|---|---|
| C1 Aplicación web | Sí, con condiciones | Pruebas por módulo con dobles para IA, Registro Civil, Redis y BD | El ADR 0002 ya advierte que el monolito "exige disciplina de módulos": si Registro, Evaluación, Tablero y Auditoría se importan entre sí, solo se podrá probar la app completa. **Evaluación concentra HU02, HU03 y HU06 y cuatro dependencias**: es la mayor superficie de prueba. |
| C2 Base de datos clínica | Sí | PostgreSQL efímero en las pruebas (constraints, migraciones) | El cifrado en reposo no se verifica en pruebas funcionales: requiere revisar configuración de infraestructura. |
| C3 Cola de auditoría | Parcial | Se prueba el **contrato del evento** (esquema), no Redis en sí | No hay escenario para "Redis caído al momento de decidir". Ver hallazgo T3. |
| C4 Worker de auditoría | Sí | Cola falsa + BD de prueba. Casos: reintento duplicado (idempotencia), evento malformado | — |
| C5 Almacén de auditoría | Sí | Probar que `UPDATE` y `DELETE` fallan con el rol de la aplicación | La retención de 5 años no es verificable en el tiempo: se verifica como política/configuración. |
| Servicio de IA (externo) | Solo con doble | Servidor falso con latencia, caída y respuesta malformada configurables | Es no determinista y de latencia no controlable: **no se puede probar HU06 contra el servicio real**. Contra el real, solo pruebas de humo acotadas (costo por request, ADR 0002). |
| Registro Civil (externo) | Solo con doble | Servidor falso | Ver hallazgo T4. |

### Hallazgos de acoplamiento

**T1 — La verificación del audit log obliga a levantar C1 + C3 + C4 + C5 juntos.**
Los escenarios de HU01, HU03 y HU06 terminan en "queda registrado en el audit log". Como la escritura es asíncrona (decisión del ADR 0002), una prueba de extremo a extremo tiene que esperar a que el worker procese, y eso produce pruebas inestables. *Recomendación:* partir la verificación en dos pruebas independientes: (a) C1 publica el evento correcto en la cola; (b) C4 persiste en C5 un evento dado. El extremo a extremo completo queda como una sola prueba de humo.

**T2 — Los plazos de HU06 necesitan un reloj y un timeout inyectables.**
Los escenarios fijan 3 s y 2,8 s. Si el timeout está escrito fijo dentro del código, la prueba tiene que esperar 3 segundos reales y depende de la máquina. *Recomendación:* el timeout y el reloj como parámetros, y el servicio de IA falso con latencia configurable.

**T3 — Doble escritura sin escenario: BD clínica + cola.**
Si C1 guarda la decisión en C2 y falla la publicación en C3, la decisión existe pero no queda en el audit log, lo que viola la métrica de Observabilidad (100 % de las decisiones registradas). Ningún escenario define este caso. *Recomendación:* agregar un escenario (a cargo del QA Lead) y que el Tech Lead defina el comportamiento (por ejemplo, patrón outbox, o bloquear la decisión si no se pudo encolar).

**T4 — Registro Civil sin escenario de caída.**
C1 depende de él para HU01, pero ningún escenario cubre qué pasa si no responde. Además, el escenario de RUT inválido de HU01 verifica el dígito verificador, que se puede validar localmente sin llamar a nadie. *Recomendación:* decidir si la validación del RUT es local o remota; si es remota, falta el escenario de caída.

**T5 — El tablero cruza dos módulos y un canal en tiempo real.**
HU04 esc. 2 ("la enfermera reevalúa y el tablero se actualiza") involucra Evaluación, Tablero y WebSocket. Es probable que se pueda probar por partes (Evaluación guarda; Tablero ordena a partir de datos sembrados), con una sola prueba de integración para el canal.

**T6 — HU05 esc. 2 (50.000 registros) necesita C5 poblado.**
Es una prueba de rendimiento, no funcional: requiere cargar datos de volumen en C5 y debe separarse de las pruebas unitarias.

## Otros hallazgos (fuera del cruce, pero detectados al revisar)

- **HU01 esc. 1 usa un RUT que no pasa la validación.** El escenario de caso feliz ingresa `12.345.678-9`, pero por módulo 11 el dígito verificador de 12.345.678 es **5**. Tal como está, el caso feliz sería rechazado por el mismo sistema que describe. Corrección propuesta: usar `12.345.678-5`.
- **HU04 esc. 3 menciona "servidor WebSocket"**, un detalle técnico en un criterio de aceptación; si la tecnología cambia, el escenario queda obsoleto (se resuelve junto con A3).

## Resumen

| Pregunta | Resultado |
|---|---|
| ¿Historias sin contenedor? | Ninguna a nivel de contenedor. 4 capacidades sin dueño explícito (A1–A4); la más importante es la alerta al equipo de plataforma (HU06). |
| ¿Contenedores sin historia? | Ninguno. C3, C4 y C5 se justifican solo por criterios de aceptación y por la mitad de HU05 (*Should*): riesgo de trazabilidad. |
| ¿Testabilidad? | Buena por contenedor si hay interfaces. Acoplamientos a vigilar: cadena de auditoría (T1), plazos de HU06 (T2) y doble escritura (T3). |
