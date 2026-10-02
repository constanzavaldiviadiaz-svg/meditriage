# ADR 0003 — Decisión cloud y servicios gestionados

## Estado

Propuesto — 02/10/2026

Pasa a *Aceptado* cuando el equipo apruebe el Pull Request correspondiente.

## Autores

Fernando Ureta (Tech Lead · AI/Data Lead), con los criterios de producto aportados por
Constanza Valdivia (Product Owner).

## Contexto

El [ADR 0002](0002-estilo-arquitectonico.md) eligió **monolito modular** con el motor de IA
como servicio externo. Esta sesión exige revisar esa decisión **con evidencia**, contrastarla
contra los criterios de diseño cloud-native, y definir qué se delega al proveedor y qué se
opera.

Las restricciones no han cambiado y siguen siendo el filtro de toda decisión:

| Restricción | Valor |
|---|---|
| Latencia de respuesta del triage | menos de 3 segundos |
| Disponibilidad | 99.5% mensual |
| Retención del audit log | 5 años, inmutable |
| Datos de salud | Ley 19.628 y Ley 21.719 |

El equipo son cuatro estudiantes, con un semestre y sin experiencia previa operando sistemas
distribuidos.

## Decisión

### 1. Se confirma el monolito modular

El ADR 0002 se mantiene. Contrastado contra los criterios de esta sesión, los cuatro apuntan
en la misma dirección:

| Criterio para monolito modular | ¿Se cumple? |
|---|---|
| Equipo menor a 15 personas | Sí, somos cuatro |
| Dominio aún se descubre | Sí: tres supuestos del Discovery siguen sin validar |
| Presupuesto operacional limitado | Sí |
| Transacciones ACID naturales | Sí: el registro del paciente y su consentimiento deben grabarse completos o no grabarse |

Aplica además la regla de Sam Newman que cita la sesión: *"si no puedes construir bien un
monolito modular, no vas a poder con microservicios"*. El equipo todavía no ha escrito código;
sostener que puede operar servicios distribuidos no tendría respaldo.

### 2. Todos los servicios de infraestructura se delegan al proveedor

Evaluación por componente, según el framework de la sesión. Los criterios de diferenciación
de producto los aportó la Product Owner en el issue #44.

| Componente | ¿Diferencia al producto? | Decisión |
|---|---|---|
| Base de datos clínica | No. Es necesaria, pero el usuario no percibe quién la opera | Servicio gestionado |
| Cola de auditoría | No. Organiza trabajo interno | Servicio gestionado |
| Almacén de auditoría | No directamente, aunque es obligatorio por normativa | Servicio gestionado, con inmutabilidad verificable |
| Aplicación web | **Sí.** Es el producto | Se construye y se opera como contenedor |

Lo único que el equipo construye es aquello que diferencia a MediTriage: la captura clínica,
la evaluación asistida por IA, el tablero y la consulta de auditoría.

**El proveedor cloud concreto no se decide en este ADR.** La decisión aquí es de política
—gestionado sobre autogestionado— y las tres piezas tienen equivalente maduro en AWS, Azure y
GCP. La elección del proveedor se tomará al llegar a infraestructura (S07), cuando se conozcan
las condiciones de acceso reales.

Para que esa elección no sea una trampa, se adopta la recomendación de la sesión: **la
aplicación se acopla a interfaces, no a servicios concretos** (Ports & Adapters). Cambiar de
proveedor debe ser doloroso, no imposible.

### 3. Condiciones que ningún proveedor puede incumplir

Los compromisos de producto, con sus cifras. Un servicio gestionado que no los alcance queda
descartado aunque sea más barato o más cómodo:

- Disponibilidad igual o superior a **99.5% mensual**
- Latencia compatible con el presupuesto de **3 segundos** de extremo a extremo
- Cifrado en reposo y en tránsito
- Retención de **5 años** con escritura inmutable para el audit log
- Tratamiento de datos conforme a la **Ley 19.628 y la Ley 21.719**, incluida la posibilidad
  de fijar la región donde residen los datos

### 4. Patrones cloud-native que se adoptan

De los siete que presenta la sesión, se adoptan dos. Ambos ya estaban decididos como
comportamiento: lo que aporta la sesión es el nombre y la forma estándar de implementarlos.

**Circuit Breaker.** Es el comportamiento de HU06. Cuando el servicio de IA falla o supera los
3 segundos, el caso se deriva a triage manual. El patrón añade algo que HU06 no contemplaba:
tras varios fallos consecutivos el circuito se abre y **se deja de llamar al servicio**, en
vez de gastar 3 segundos en cada paciente para obtener el mismo fallo. Estados: cerrado,
abierto y semiabierto.

**Outbox.** Resuelve un problema que detectó el QA Lead al construir la trazabilidad: si la
aplicación guarda la decisión en la base clínica y falla la publicación en la cola, la
decisión **nunca llega al audit log**. Ningún escenario cubría ese caso y contradice
directamente la métrica de Observabilidad, que exige el 100% de las decisiones registradas.

El patrón lo resuelve escribiendo el evento en una tabla *outbox* dentro de la misma
transacción que guarda la decisión. Un proceso relay la lee y publica a la cola. Si la
publicación falla, el evento sigue en la tabla y se reintenta: no se pierde.

### 5. Autenticación y observabilidad son responsabilidades transversales

La trazabilidad detectó dos capacidades que los escenarios exigen y que el C4 nivel 2 no
asigna a ningún contenedor: la **alerta al equipo de plataforma** cuando el servicio de IA
está caído (`hu06.feature`), y la **autenticación con roles y el log de accesos denegados**
(`hu05.feature`).

**No se incorporan como contenedores al diagrama.** En C4, un contenedor es algo que se
despliega y ejecuta por separado; la autenticación y la observabilidad son *cross-cutting
concerns* que atraviesan todos los componentes. Dibujarlos como cajas ensucia el nivel 2 sin
aportar información.

Se declaran aquí como responsabilidades transversales de la aplicación web, y se detallarán
cuando corresponda: la autenticación al definir las APIs (S05) y la observabilidad en su
sesión propia (S11).

## Consecuencias

### Positivas

- **El equipo no opera infraestructura.** Con cuatro personas y un semestre, cada hora que no
  se va en mantener una base de datos se va en el producto.
- **Las cifras de los compromisos se vuelven criterio de descarte.** Un proveedor que ofrezca
  99% de disponibilidad queda fuera sin discusión, porque el compromiso es 99.5%.
- **Outbox cierra un hueco real** que ya estaba en el sistema y que nadie había visto hasta la
  revisión de trazabilidad.
- **Circuit Breaker reduce el costo del fallo.** Hoy cada paciente pagaría 3 segundos de
  espera mientras el servicio esté caído; con el circuito abierto, ninguno.

### Negativas

- **Dependencia del proveedor.** Delegar tres piezas significa que su caída es nuestra caída,
  y su acuerdo de nivel de servicio pasa a ser el techo del nuestro. Mitigación parcial:
  acoplarse a interfaces, no a servicios concretos.
- **El costo de operar no se cuantificó.** El framework de la sesión sugiere comparar si el
  servicio gestionado cuesta más de tres veces el autogestionado. El equipo no tiene datos de
  costo real, así que la decisión se tomó por el criterio de diferenciación de producto. Se
  revisará en FinOps (S15).
- **Outbox agrega una tabla y un proceso relay** al diseño. Es complejidad que no estaba en el
  C4 nivel 2 y que habrá que incorporar.
- **El proveedor queda sin decidir**, lo que posterga la verificación concreta de que algún
  servicio cumple las cifras comprometidas.

## Alternativas descartadas

### Reemplazar el monolito por microservicios

Los criterios de la sesión apuntan en contra en los cuatro ejes evaluados. El costo
—observabilidad distribuida, orquestación, consistencia eventual, la red como punto único de
falla— no tiene quién lo pague en un equipo de cuatro estudiantes. Se revisará si el equipo
crece o si algún módulo necesita escalar por separado.

### Operar los servicios nosotros

Ninguno de los tres diferencia al producto, y los tres tienen equivalentes gestionados
maduros. Operarlos significaría gastar el tiempo del equipo en respaldos, parches y
recuperación ante fallos, sin que el usuario perciba diferencia alguna.

### Elegir el proveedor cloud en este ADR

Se evaluó fijarlo ahora para poder verificar las cifras comprometidas. Se descarta porque el
equipo todavía no conoce las condiciones de acceso reales, y una decisión tomada sin ese dato
tendría que rehacerse. La política de usar servicios gestionados no depende de cuál sea el
proveedor.

### Los otros cinco patrones de la sesión

| Patrón | Por qué no aplica |
|---|---|
| **API Gateway** | Centraliza autenticación y enrutamiento entre múltiples servicios. Con un solo despliegue no hay nada que centralizar |
| **Saga** | Resuelve transacciones distribuidas. En un monolito las transacciones son locales y ACID |
| **CQRS** | Separa los modelos de lectura y escritura cuando sus requisitos divergen. El volumen y la complejidad actuales no lo justifican. Podría reconsiderarse si el tablero de HU04 compite con la escritura |
| **Bulkhead** | Aísla pools de recursos por dependencia. Con una sola dependencia externa crítica, el Circuit Breaker ya cubre el riesgo |
| **Sidecar** | Delega preocupaciones transversales a un contenedor auxiliar. Pertenece a arquitecturas con service mesh, que requieren varios servicios |

### Dibujar la autenticación y la observabilidad como contenedores

Se descarta por la definición misma de contenedor en C4: algo que se despliega por separado.
Ambas son transversales. Representarlas como cajas daría una imagen falsa de la arquitectura.

## Revisión futura

Este ADR se revisará si ocurre alguno de estos disparadores:

- El equipo crece o incorpora experiencia operando sistemas distribuidos.
- Algún módulo necesita escalar de forma independiente del resto.
- El costo de los servicios gestionados se vuelve material frente al de operarlos (S15).
- Se decide el proveedor cloud y alguna de las cifras comprometidas resulta inalcanzable.

Un ADR no se edita: si la decisión cambia, este se marca como *Reemplazado* y se escribe uno
nuevo.
