# ADR 0004 — Datos y eventos

## Estado

Propuesto — 09/10/2026

Este ADR **modifica el ADR 0003 en un punto**: la decisión sobre CQRS. El resto del ADR 0003
sigue vigente.

## Autores

Fernando Ureta (Tech Lead · AI/Data Lead). El análisis del broker y las garantías de entrega
corresponde a Matías Sepúlveda (DevSecOps Lead).

## Contexto

La sesión 06 pide elegir el motor de persistencia de cada bounded context, el broker de
eventos, y qué patrones de datos aplicar.

**La propuesta del docente.** La diapositiva 8 de la sesión usa MediTriage como caso y propone
**PostgreSQL + Kafka + OpenSearch + Redis**, con CQRS: escritura contra PostgreSQL y lectura
del tablero desde OpenSearch.

**Los criterios de la misma sesión.** El material establece tres reglas que aplican a esa
propuesta:

- Diapositiva 4: *"Empieza con PostgreSQL. Agrega Redis para cache. Introduce un motor
  especializado solo cuando midas que Postgres no alcanza — no antes."*
- Diapositiva 6: *"No agregues Event Sourcing por moda. Outbox, en cambio, es casi siempre
  útil cuando publicas eventos."*
- Objetivo 03: *"Usar CQRS, Event Sourcing, Outbox y Saga solo cuando el problema los pide."*

**Las decisiones previas.** El [ADR 0002](0002-estilo-arquitectonico.md) eligió monolito
modular para un equipo de cuatro personas. El [ADR 0003](0003-cloud-style.md) delegó toda la
infraestructura en servicios gestionados.

**El volumen real.** Un centro de atención primaria recibe del orden de 100 pacientes al día.
Cada uno genera unos 7 eventos de dominio:

| Magnitud | Valor estimado |
|---|---|
| Eventos por día | ~700 |
| Eventos por minuto, en hora punta | ~8 |
| Registros de auditoría en 5 años | ~1,3 millones |
| Pacientes simultáneos en la sala de espera | entre 10 y 50 |

Este ADR aplica los criterios de la sesión a su propia propuesta.

## Decisión

### 1. Motor de persistencia por bounded context

Los contextos son los definidos en el issue #54.

| Contexto | Motor | Por qué |
|---|---|---|
| **Identidad** | PostgreSQL | El paciente y su consentimiento se graban completos o no se graban: requiere transacciones ACID |
| **Clínico** | PostgreSQL | Es el modelo del [DER](../data/der.png): relacional, con integridad referencial entre encuentro, signos vitales y evaluaciones |
| **Auditoría** | PostgreSQL append-only, en una base separada | Inmutabilidad por permisos, ya decidida en el ADR 0002. Separada para que un error de la aplicación no pueda alterar los registros |
| **Sala de espera** | Redis | Vista de lectura del tablero, actualizada en tiempo real. Ver la sección 4 |

**Una sola tecnología relacional para tres contextos.** Cuatro personas aprenden y operan un
motor, no tres. Y 1,3 millones de registros en cinco años están muy lejos de cualquier límite
de PostgreSQL.

### 2. Broker de eventos

Basado en el análisis del issue #56, de Matías Sepúlveda.

**Se usa Redis Streams, como servicio gestionado.** Redis ya está en la arquitectura (ADR
0002, C4 nivel 2) como cola de auditoría: no se agrega tecnología nueva. A diferencia de Redis
Pub/Sub, un *stream* guarda los mensajes, admite grupos de consumidores y exige una
confirmación (ACK) de cada mensaje procesado. Si un consumidor está caído, los mensajes lo
esperan.

**Dos consumidores, cada uno a su ritmo.** Cada consumidor es un grupo independiente sobre el
mismo stream, con sus propias confirmaciones. Si uno se atrasa, el otro no lo espera.

| Grupo de consumidores | Qué hace con cada evento |
|---|---|
| **auditoria** | Lo escribe en la base de auditoría append-only |
| **sala-de-espera** | Actualiza la vista de lectura en Redis (sección 4) |

**Garantía de entrega: al menos una vez (*at-least-once*).** Ningún evento se pierde, pero
alguno puede llegar dos veces. El recorrido completo:

1. La decisión y su evento se guardan juntos en PostgreSQL, en la misma transacción (Outbox).
2. El relay publica los eventos pendientes en el stream y marca `publicado_en`.
3. Cada consumidor procesa el evento.
4. **Solo después de procesarlo** envía el ACK. Si falla antes, el mensaje queda pendiente y
   se reintenta.

El duplicado aparece cuando el relay publica y falla antes de marcar `publicado_en`: al
reintentar, publica de nuevo. Por eso **los consumidores son idempotentes**: cada evento lleva
su `evento_id` (la clave de la tabla `outbox_evento`), y un evento ya procesado se descarta.
En auditoría, `evento_id` es una restricción `UNIQUE`: la base misma rechaza el duplicado.

**Qué pasa cuando algo falla:**

| Falla | Qué ocurre | Qué se pierde |
|---|---|---|
| **Redis no disponible** | Los eventos esperan en la tabla outbox. El relay reintenta con esperas progresivas y alerta si los pendientes se acumulan. Al volver Redis, publica lo atrasado | Nada |
| **Consumidor de auditoría caído** | Los mensajes sin ACK quedan pendientes y se procesan al volver | Nada |
| **Un mensaje falla una y otra vez** | Tras un número fijo de intentos se aparta a un stream de mensajes fallidos para revisión manual, sin bloquear al resto | Nada: queda apartado, no descartado |
| **Redis pierde datos** (por ejemplo, en una conmutación del servicio gestionado) | Se reconcilia: los eventos de la outbox cuyo `evento_id` no aparece en auditoría se vuelven a publicar. Por eso la outbox **conserva los eventos hasta confirmar que llegaron a auditoría**, no solo hasta publicarlos | Nada |

**Los dos roles de Redis.** Con este ADR, Redis es a la vez la cola de eventos y la vista de la
sala de espera. Se acepta usar **una sola instancia gestionada**, porque una caída de Redis no
compromete ni los datos ni el triage:

- **El flujo de triage no pasa por Redis.** Registrar al paciente, evaluar y confirmar la
  categoría escriben en PostgreSQL. El presupuesto de 3 segundos no depende de Redis.
- **La auditoría no se pierde.** Espera en la outbox, como muestra la tabla anterior.
- **El tablero se degrada, pero no se apaga.** Si la vista no responde, `GET
  /v1/sala-de-espera` consulta directamente PostgreSQL, la fuente de verdad: con 50 pacientes
  es una consulta trivial. Lo que se pierde mientras tanto es la actualización en tiempo real
  por SSE; el tablero debe refrescarse a mano.

Para que un rol no dañe al otro, la instancia se configura **sin expulsión de claves**
(`noeviction`): si la memoria se llenara, Redis rechaza escrituras nuevas en lugar de borrar en
silencio mensajes del stream. Con ~700 eventos al día, el volumen está muy lejos de ese
límite. El stream se recorta periódicamente: **los 5 años de retención viven en la base de
auditoría, no en Redis**.

**Seguridad.** Cifrado en tránsito y en reposo, y acceso a Redis solo desde la aplicación y
sus procesos. Los eventos llevan únicamente lo que los consumidores necesitan, nunca RUT ni
nombre: Outbox define explícitamente ese contenido (sección 3).

**Condición de adopción.** El servicio gestionado que se elija en la nube debe ofrecer
persistencia en disco y una disponibilidad compatible con el 99,5% mensual. Si no la ofrece,
aplica el disparador hacia RabbitMQ.

### 3. Patrones de datos

**Ya decidido en el ADR 0003, se confirma:**

| Patrón | Decisión |
|---|---|
| **Outbox** | Adoptado |
| **Saga** | Descartado: no hay transacciones distribuidas en un monolito con una sola base por contexto |

**Cómo se aplica Outbox al modelo de datos.** El ADR 0003 decidió adoptarlo; el DER lo
concreta. Es la tabla `outbox_evento` del contexto clínico. Cuando se registra una decisión,
el evento se inserta en esa tabla **en la misma transacción** que la evaluación o la categoría
final: o se guardan ambos o ninguno. Un proceso relay lee la tabla, publica al broker y marca
`publicado_en`. Si la publicación falla, el evento sigue en la tabla y se reintenta.

Además de evitar la pérdida de eventos, Outbox permite **decidir exactamente qué viaja en cada
evento**. Eso importa en un sistema con datos de salud: ningún identificador del paciente sale
del contexto que lo posee.

**CQRS — se adopta en versión liviana, solo para la sala de espera.** Esto modifica el ADR
0003, que lo había descartado. Ver la sección 4.

**Nuevos en esta sesión:**

**Event Sourcing — descartado.** El docente plantea usarlo solo si se necesita auditoría
inmutable, replay o time-travel, y MediTriage sí necesita auditoría inmutable. Pero hay que
distinguir dos requisitos que se parecen:

- **Registrar** cada decisión para que pueda auditarse
- **Reconstruir** el estado del sistema a partir de esos registros

MediTriage necesita lo primero, no lo segundo. Event Sourcing convierte el log de eventos en
la fuente de verdad del estado: para saber en qué situación está un encuentro, habría que
reproducir todos sus eventos desde el inicio. La tabla de auditoría append-only cumple el
requisito legal sin pagar ese costo. **Se necesita auditar decisiones, no reconstruir
estados.**

**Change Data Capture — descartado.** Resuelve el mismo problema que Outbox, por otra vía: lee
el registro interno de cambios de la base de datos y publica cada cambio. Se descarta por tres
razones:

1. Outbox ya resuelve el problema
2. Exige operar una herramienta adicional, como Debezium, contra lo decidido en el ADR 0003
3. **Publica los cambios tal como están en las tablas**, y las tablas contienen datos de salud.
   Con Outbox el contenido de cada evento es explícito; con CDC, controlarlo es mucho más
   difícil

### 4. La vista de la sala de espera: CQRS liviano

El ADR 0003 descartó CQRS porque el volumen no lo justificaba. **El volumen sigue sin
justificarlo**: PostgreSQL resuelve sin esfuerzo una consulta sobre 50 pacientes.

La razón para adoptarlo ahora es otra. HU04 exige que el tablero del médico jefe se actualice
**en tiempo real**, y el contrato OpenAPI ya define un canal SSE para eso. Esta sesión
introduce además los eventos de dominio. Con ambas piezas, mantener una vista de la sala de
espera alimentada por eventos es la forma natural de servir ese canal, y coincide con lo que
propone la diapositiva 8. Redis ya está en la arquitectura: el patrón no agrega
infraestructura.

| Lado | Dónde | Qué hace |
|---|---|---|
| **Escritura** | PostgreSQL, contexto clínico | Fuente de verdad. Aquí se registran encuentros, evaluaciones y categorías |
| **Eventos** | Tabla outbox → broker | Cada cambio relevante publica un evento: ingreso, cambio de categoría, atención |
| **Proyección** | Un consumidor | Recibe esos eventos y actualiza la vista en Redis |
| **Lectura** | Redis | `GET /v1/sala-de-espera` y el canal SSE leen de aquí |

**PostgreSQL sigue siendo la fuente de verdad.** Si la vista en Redis se pierde o se
corrompe, se reconstruye desde PostgreSQL. La vista es desechable; los datos no.

El contrato OpenAPI no cambia: de dónde lee el servidor es un detalle de implementación que
la API no expone.

## Consecuencias

### Positivas

- **Coherente con los ADR 0002 y 0003.** Ninguna pieza nueva que operar.
- **Una sola tecnología relacional** para tres contextos.
- **CQRS sin infraestructura nueva**, porque Redis ya estaba.
- **Sigue los criterios de la propia sesión**: PostgreSQL primero, Outbox siempre, y Event
  Sourcing solo si el problema lo pide.
- **Outbox protege también los datos sensibles**, no solo la entrega.

### Negativas

- **Consistencia eventual en el tablero.** La vista puede ir unos milisegundos detrás de
  PostgreSQL. Es aceptable para un tablero; no lo sería para la decisión clínica, que sigue
  leyendo de la fuente de verdad.
- **Redis concentra dos roles.** Si cae, afecta a la cola y a la vista a la vez. No se pierden
  datos ni se detiene el triage, pero el tablero pierde el tiempo real hasta que vuelva
  (sección 2).
- **Los consumidores deben ser idempotentes.** Es el precio de la entrega *at-least-once*: todo
  consumidor nuevo tiene que descartar eventos repetidos por `evento_id`.
- **Redis es más débil que un broker dedicado ante pérdida de datos.** Se compensa con la
  reconciliación contra la outbox, que obliga a conservar los eventos más tiempo.
- **No hay replay del log de eventos.** Si algún día se necesita reconstruir estados pasados,
  no será posible con este diseño.
- **La búsqueda de texto es básica.** PostgreSQL busca por texto, pero con menos capacidad que
  un motor de búsqueda dedicado.
- **Una migración futura tendría costo.** Si el volumen creciera mucho, cambiar de motor
  después cuesta más que haberlo elegido antes. Se mitiga con los disparadores escritos más
  abajo.

## Alternativas descartadas

### La propuesta completa de la diapositiva 8

PostgreSQL + Kafka + OpenSearch + Redis. Se adopta de ella lo que el problema pide —CQRS para
la sala de espera, con Redis— y se descartan Kafka y OpenSearch con el criterio de la
diapositiva 4 de la misma sesión: no introducir un motor especializado hasta medir que
PostgreSQL no alcanza. Con ~700 eventos al día y 50 pacientes en la sala, no hay medición que
lo justifique. Operar ambos contradiría además los ADR 0002 y 0003.

### Redis Pub/Sub como broker

No guarda los mensajes: si el consumidor de auditoría no está conectado en ese momento, el
evento se pierde. Inaceptable para un registro que la ley exige completo.

### RabbitMQ como broker

Una opción válida para mensajería confiable, pero es una tecnología más que el equipo tendría
que aprender, integrar y operar, cuando Redis ya está en la arquitectura y alcanza para el
volumen. Queda como disparador.

### Una base documental

Como MongoDB. El dominio es relacional —un encuentro tiene signos vitales, síntomas y
evaluaciones vinculadas— y el registro con consentimiento requiere transacciones.

### Mantener CQRS descartado, como en el ADR 0003

Era una opción válida: el volumen no lo exige. Se cambió porque la actualización en tiempo real
de HU04 y los eventos de esta sesión hacen natural la vista separada, a costo casi nulo.

### Event Sourcing y Change Data Capture

Desarrollados en la sección 3.

## Disparadores para migrar

Qué tendría que ocurrir para revisar este ADR:

| Migrar a… | Cuando… |
|---|---|
| **RabbitMQ** | El servicio gestionado de Redis no ofrezca persistencia verificable, o la reconciliación contra la outbox empiece a encontrar eventos perdidos con frecuencia |
| **Kafka** | Varios consumidores con velocidades muy distintas obliguen a retener más eventos de los razonables en memoria, o se necesite replay del log |
| **OpenSearch** | El auditor necesite buscar por el contenido de las justificaciones, o la analítica histórica compita con el presupuesto de 3 segundos |
| **Event Sourcing** | Haya que reconstruir el estado de un encuentro en un momento pasado, no solo auditar sus decisiones |
| **Réplica de lectura** | Las consultas de auditoría sobre cinco años de historia empiecen a competir con la carga operacional |

Un ADR no se edita: si la decisión cambia, este se marca como *Reemplazado* y se escribe uno
nuevo.
