# Trazabilidad historias ↔ contenedores (C4 nivel 2)
## Qué es

Verificación de cobertura en las dos direcciones: cada historia del backlog debe tener al menos un contenedor que la implemente, y cada contenedor debe servir a al menos una historia. Es la misma lógica de la regla de oro del Impact Map, un nivel más abajo.

Un contenedor "implementa" una historia si es necesario para cumplir alguno de sus escenarios en `docs/scenarios/`. Se usan los escenarios porque varios criterios de aceptación (por ejemplo, "queda registrado en el audit log") involucran contenedores que el texto de la historia no menciona.

## Contenedores

| Id | Contenedor | Rol |
|---|---|---|
| C1 | Aplicación web (monolito modular) | Interfaz y módulos Registro, Evaluación, Tablero y Auditoría |
| C2 | Base de datos clínica | Pacientes, consentimientos, signos vitales, evaluaciones |
| C3 | Cola de auditoría (Redis) | Desacopla el registro de la decisión de la respuesta al usuario |
| C4 | Worker de auditoría | Consume la cola y persiste cada decisión |
| C5 | Almacén de auditoría | Registro inmutable, retención de 5 años |

El Servicio de IA y el Registro Civil son sistemas externos: no cuentan como contenedores.

## Tabla historia → contenedor

| Historia | Contenedores que la implementan |
|---|---|
| HU01 Registro con consentimiento | C1 (Registro) · C2 · C3 · C4 · C5 · Registro Civil (ext.) |
| HU02 Síntomas y signos vitales | C1 (Evaluación) · C2 |
| HU03 Sugerencia ESI con justificación | C1 (Evaluación) · C2 · C3 · C4 · C5 · Servicio de IA (ext.) |
| HU04 Tablero de pacientes priorizados | C1 (Tablero) · C2 |
| HU05 Auditoría de recomendaciones | C1 (Auditoría) · C5 (lectura) · C3 · C4 (escritura) |
| HU06 Derivación a triage manual | C1 (Evaluación) · C3 · C4 · C5 · Servicio de IA (ext.) |

C3, C4 y C5 aparecen en HU01, HU03 y HU06 porque sus escenarios exigen registrar en el audit log.

## Tabla contenedor → historia

| Contenedor | Historias que lo usan |
|---|---|
| C1 Aplicación web | HU01 · HU02 · HU03 · HU04 · HU05 · HU06 |
| C2 Base de datos clínica | HU01 · HU02 · HU03 · HU04 |
| C3 Cola de auditoría | HU01 · HU03 · HU05 · HU06 |
| C4 Worker de auditoría | HU01 · HU03 · HU05 · HU06 |
| C5 Almacén de auditoría | HU01 · HU03 · HU05 · HU06 |

## Huecos

### Historia sin contenedor

Ninguna: las seis historias tienen al menos un contenedor.

Sí hay dos capacidades exigidas por los escenarios que el diagrama no asigna a ningún contenedor:

- **Alerta al equipo de plataforma** cuando el servicio de IA está caído (HU06, escenario 3). El diagrama no incluye ningún componente de monitoreo o alertas, aunque el atributo de calidad Observabilidad lo requiere.
- **Autenticación y roles, y log de seguridad** de accesos denegados (HU05, escenario 3). El diagrama no muestra dónde se resuelve.

Se dejan señaladas para que el Tech Lead evalúe si corresponde representarlas en el diagrama o declararlas como responsabilidad transversal.

### Contenedor sin historia

Ninguno: todos sirven a al menos cuatro historias.

Observación: C3, C4 y C5 no tienen una historia cuyo propósito principal sea el registro inmutable. Hoy se justifican por los criterios de aceptación de HU01, HU03 y HU06 y por la mitad de escritura de HU05, que está priorizada como *Should*. El backlog ya anticipa partir HU05 en la S06; se deja anotado para que, cuando eso ocurra, la PO considere si el registro inmutable necesita su propia historia.

## Testabilidad de la arquitectura

La arquitectura se puede probar contenedor por contenedor, siempre que las dependencias (servicio de IA, Registro Civil, Redis, bases de datos) queden detrás de interfaces que puedan reemplazarse por dobles de prueba.

| Contenedor | ¿Se prueba por separado? | Observación |
|---|---|---|
| C1 Aplicación web | Sí, si los módulos respetan sus fronteras | El ADR 0002 ya advierte que el monolito exige disciplina de módulos. Evaluación concentra HU02, HU03 y HU06, por lo que es la mayor superficie de prueba. |
| C2 Base de datos clínica | Sí | PostgreSQL efímero en las pruebas. |
| C3 Cola de auditoría | Parcial | Se prueba el contrato del evento, no Redis. |
| C4 Worker de auditoría | Sí | Con cola y base de datos de prueba. |
| C5 Almacén de auditoría | Sí | Se verifica que `UPDATE` y `DELETE` sean rechazados. |
| Servicio de IA (ext.) | Solo con un doble | Es no determinista y de latencia no controlable; HU06 no se puede probar contra el servicio real. |

Puntos donde las pruebas quedan acopladas:

- **Audit log:** los escenarios de HU01, HU03 y HU06 terminan en "queda registrado en el audit log". Como la escritura es asíncrona, verificarlo de extremo a extremo obliga a levantar C1, C3, C4 y C5 juntos y esperar al worker, lo que vuelve las pruebas inestables. Conviene verificar por separado que C1 publica el evento y que C4 lo persiste.
- **Plazos de HU06:** los escenarios fijan 3 s y 2,8 s. Para probarlos sin esperas reales, el timeout y el servicio de IA deben ser configurables en las pruebas.
- **Doble escritura:** si C1 guarda la decisión en C2 y falla la publicación en C3, la decisión no llega al audit log. Ningún escenario define este caso, y afecta la métrica de Observabilidad (100 % de las decisiones registradas).

## Resumen

| Pregunta | Resultado |
|---|---|
| ¿Historias sin contenedor? | Ninguna. Dos capacidades sin dueño explícito: alerta a plataforma y autenticación/log de seguridad. |
| ¿Contenedores sin historia? | Ninguno. C3, C4 y C5 dependen de criterios de aceptación y de HU05 (*Should*). |
| ¿Testabilidad? | Buena por contenedor con interfaces. Acoplamientos: cadena de auditoría, plazos de HU06 y doble escritura. 
