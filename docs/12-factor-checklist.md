# Checklist 12-Factor — MediTriage

Auditoría de la arquitectura contra los doce factores. Como todavía no existe código, la
evaluación se hace sobre el diseño definido en el [ADR 0002](adr/0002-estilo-arquitectonico.md),
el [ADR 0003](adr/0003-cloud-style.md) y el [diagrama C4 nivel 2](c4/).

**Varios factores no se cumplen todavía, y es esperable en esta etapa.** Lo que importa es que
cada uno tenga una acción concreta definida: decir "no cumple, y esto hay que hacer" es más
útil que forzar un cumple que no es cierto.

## Resumen

| Estado | Factores | Total |
|---|---|---|
| **Cumple** | 01 Codebase · 04 Backing services · 07 Port binding | 3 |
| **Cumple parcialmente** | 03 Config · 06 Processes · 08 Concurrency · 10 Dev/prod parity | 4 |
| **No cumple** | 02 Dependencies · 05 Build/release/run · 09 Disposability · 11 Logs · 12 Admin processes | 5 |

Los cinco que no cumplen dependen de que exista código o pipeline. Ninguno está bloqueado por
una decisión de arquitectura: están bloqueados por la etapa del proyecto.

---

## 01 · Codebase

> Una base de código en Git por aplicación, muchos despliegues.

**Estado: cumple**

**Situación actual.** Un único repositorio en GitHub con `main` protegida y flujo de Pull
Requests. El monolito modular se despliega como una sola unidad, así que la relación es uno a
uno: un codebase, una aplicación.

**Acción.** Ninguna. La vigilancia está en el otro lado: que los cuatro módulos —Registro,
Evaluación, Tablero y Auditoría— no empiecen a copiarse código entre ellos. El ADR 0002 ya
advierte que el monolito exige disciplina de módulos.

---

## 02 · Dependencies

> Declaradas y aisladas explícitamente.

**Estado: no cumple**

**Situación actual.** No hay código ni archivo de dependencias.

**Acción.**

1. Declarar las dependencias con un gestor que fije versiones exactas (Poetry o `pip-tools`
   con el archivo bloqueado versionado).
2. Trabajar siempre dentro de un entorno virtual aislado.
3. No depender nunca de paquetes instalados en el sistema operativo: si algo no está
   declarado, no existe.

---

## 03 · Config

> La configuración vive en variables de entorno, no en el código.

**Estado: cumple parcialmente**

**Situación actual.** La decisión ya está tomada, falta implementarla. El `.gitignore` del
repositorio excluye `.env` desde la S01, así que la infraestructura para no filtrar
configuración ya existe.

**Acción.**

1. Todo lo que cambia entre ambientes va a variables de entorno: URL de la base de datos, de
   Redis, del servicio de IA, del Registro Civil, y las credenciales de cada uno.
2. Versionar un `.env.example` con los nombres de las variables **sin valores reales**, para
   que cualquiera sepa qué configurar.
3. Ninguna credencial en el repositorio. Esto es especialmente sensible aquí: la clave del
   servicio de IA da acceso a un servicio de pago, y las de la base dan acceso a datos de
   salud.

Este factor es la pieza que hace posible la decisión del ADR 0003 de no atarse a un proveedor:
cambiar de servicio gestionado debe ser cambiar una URL.

---

## 04 · Backing services

> Bases de datos, colas y APIs tratadas como recursos adjuntos.

**Estado: cumple**

**Situación actual.** Es la decisión central del ADR 0003. La base de datos clínica, la cola de
auditoría y el almacén de auditoría se delegan a servicios gestionados, y el servicio de IA ya
es un recurso externo por definición.

El mismo ADR adopta Ports & Adapters: la aplicación se acopla a interfaces, no a servicios
concretos.

**Acción.** Que cada recurso adjunto se alcance **solo** por configuración. Si cambiar de
proveedor obliga a tocar código de negocio, el factor dejó de cumplirse.

---

## 05 · Build, release, run

> Tres etapas estrictamente separadas.

**Estado: no cumple**

**Situación actual.** No existe pipeline. La automatización de la entrega corresponde a la S08.

**Acción.**

1. **Build:** construir una imagen a partir del código, sin configuración dentro.
2. **Release:** combinar esa imagen con la configuración del ambiente. Cada release con su
   identificador.
3. **Run:** ejecutar el release, sin modificarlo.

La regla que se desprende: **nunca editar código en un ambiente desplegado.** Si hay que
corregir algo, se vuelve al paso uno.

---

## 06 · Processes

> Procesos sin estado, que no comparten nada entre sí.

**Estado: cumple parcialmente**

**Situación actual.** El diseño ya separa dos procesos: la aplicación web y el worker de
auditoría. Ninguno necesita saber del otro: se comunican por la cola.

El riesgo está en la aplicación web. Si la sesión de la enfermera se guardara en la memoria del
proceso, levantar una segunda réplica rompería el sistema: el usuario perdería su sesión al
caer en la otra.

**Acción.**

1. El estado de sesión va fuera del proceso, en Redis o en la base de datos.
2. El worker no guarda estado entre un mensaje y el siguiente. Cada evento de auditoría se
   procesa de forma independiente.

---

## 07 · Port binding

> La aplicación publica su propio puerto, sin depender de un servidor externo.

**Estado: cumple**

**Situación actual.** FastAPI se ejecuta sobre su propio servidor (Uvicorn) y publica un
puerto. No necesita un Apache ni un servidor de aplicaciones por delante para funcionar.

**Acción.** Que el puerto se lea de una variable de entorno, no esté fijo en el código.

---

## 08 · Concurrency

> Escalar levantando más procesos, no haciendo más grande uno solo.

**Estado: cumple parcialmente**

**Situación actual.** La aplicación web y el worker ya son procesos separados, así que se
puede escalar cada uno por su lado. El worker es el candidato natural: si el volumen de
decisiones crece, se levantan más consumidores de la cola sin tocar la aplicación.

La limitación viene del monolito y está declarada como consecuencia negativa en el ADR 0002:
dentro de la aplicación web, los cuatro módulos escalan juntos aunque solo uno reciba carga.

**Acción.** Mantener ambos procesos sin estado, que es lo que permite levantar réplicas. Sin
el factor 06 resuelto, este no se puede cumplir.

---

## 09 · Disposability

> Arranque rápido y apagado ordenado.

**Estado: no cumple**

**Situación actual.** No hay código. Pero el diseño ya señala dónde está el riesgo: **el
worker de auditoría**. Si se apaga mientras procesa un evento, ese evento no puede perderse —
la ley exige el 100% de las decisiones registradas durante 5 años.

**Acción.**

1. El worker confirma el mensaje a la cola **solo después** de haber persistido el registro.
   Si se cae antes, el mensaje vuelve a la cola y se reintenta.
2. La aplicación web termina las peticiones en curso antes de cerrar, en lugar de cortarlas.
3. Arranque sin tareas pesadas: el proceso debe estar listo en segundos.

El patrón Outbox del ADR 0003 protege el extremo de la publicación; este factor protege el de
la escritura.

---

## 10 · Dev/prod parity

> Los ambientes de desarrollo y producción, lo más parecidos posible.

**Estado: cumple parcialmente**

*Evaluación aportada por Matías Casa (QA Lead).*

**Situación actual.** El diseño usa los mismos motores en todos los ambientes —PostgreSQL y
Redis— y no contempla bases de reemplazo. Pero todavía no está definido cómo se levanta el
entorno local ni qué se usa en lugar del servicio de IA.

Si la paridad falla, hay dos riesgos concretos:

- **Almacén de auditoría.** Que no se pueda modificar ni borrar depende de permisos de
  PostgreSQL. Con otra base, por ejemplo SQLite, las pruebas pasarían en verde **sin comprobar
  nada de esa inmutabilidad**, que es justo el requisito legal de los 5 años.
- **Servicio de IA.** El real es impredecible, cobra por consulta y no se le puede forzar a
  fallar. Contra él, HU06 no se puede probar.

**El servicio de IA en desarrollo.** Simulado, con modos de fallo configurables, tanto en
desarrollo como en integración continua. Contra el servicio real, solo una prueba de humo
acotada y con datos sintéticos, nunca con datos de pacientes. Una prueba de contrato mantiene
al simulado alineado con el formato real. El código es el mismo en todos los ambientes: solo
cambia la URL, por variable de entorno.

**Entorno local.** Es viable levantar aplicación, worker, PostgreSQL, Redis y el simulado de IA
con un solo comando, usando las mismas versiones mayores que producción.

**Acción.**

1. Nada de SQLite ni Redis en memoria en las pruebas de integración: PostgreSQL y Redis reales,
   en contenedor.
2. Fijar las versiones de PostgreSQL y Redis en un solo lugar.
3. Crear el simulado del servicio de IA y dejar su URL como configuración.
4. Documentar un entorno local de un solo comando. Se concreta en la S07.

---

## 11 · Logs

> Los logs son un flujo de eventos a la salida estándar, no archivos en disco.

**Estado: no cumple**

**Situación actual.** No hay código. Pero este factor está condicionado por dos cosas que ya
decidimos: **Observabilidad** es uno de los tres atributos de calidad priorizados, y el
enunciado exige **PII enmascarada en los logs**.

Hay además un problema propio de nuestra arquitectura. Como la escritura del audit log es
asíncrona, una sola decisión atraviesa tres procesos: la aplicación la toma, la cola la
transporta, el worker la persiste. Sin un identificador común, seguir el rastro de una decisión
concreta es imposible.

**Acción.**

1. Logs estructurados en JSON a la salida estándar. Nunca escribir un archivo dentro del
   contenedor: ahí se pierde al reiniciar.
2. **Enmascarar la PII antes de escribir**, no después. Nunca RUT ni nombre completo en un log.
3. **Un identificador de correlación por petición**, que viaje desde la aplicación hasta el
   worker a través de la cola. Es lo que permite reconstruir qué pasó con una decisión
   específica.
4. La recolección y el almacenamiento de logs son responsabilidad del entorno de ejecución, no
   de la aplicación.

---

## 12 · Admin processes

> Las tareas puntuales se ejecutan en el mismo entorno que la aplicación.

**Estado: no cumple**

**Situación actual.** No hay código ni migraciones todavía. Pero ya se sabe qué tareas van a
existir: migraciones del esquema de base de datos y, eventualmente, reprocesos de la tabla
outbox.

Hay un riesgo específico de este proyecto. El almacén de auditoría es inmutable **por
permisos**: `UPDATE` y `DELETE` están revocados. Una migración mal hecha que los reponga
rompería silenciosamente la garantía legal de los 5 años, sin que nada falle.

**Acción.**

1. Migraciones versionadas en el repositorio y ejecutadas con el mismo código e imagen que la
   aplicación. Nunca a mano por SSH.
2. Toda tarea administrativa corre en el mismo entorno y con la misma configuración que la
   aplicación.
3. **Revisión obligatoria de cualquier migración que toque el almacén de auditoría**, con el
   rol de seguridad involucrado.

---

## Qué se desprende de esta auditoría

**Tres factores dependen de decisiones que ya están tomadas** y solo falta ejecutarlas: la
configuración por variables de entorno (03), los recursos adjuntos (04) y la paridad de
ambientes (10). Están encaminados.

**Dos factores apuntan al mismo punto débil:** procesos sin estado (06) y concurrencia (08). Si
la sesión de la enfermera queda en memoria del proceso, los dos se caen juntos. Es la primera
decisión de implementación que conviene no equivocar.

**Tres factores protegen el audit log desde ángulos distintos:** disposability (09) evita
perder un evento al apagar el worker, logs (11) permite rastrear una decisión a través de los
tres procesos, y admin processes (12) evita que una migración rompa la inmutabilidad. Los tres
sirven al mismo requisito legal.

**Y uno es condición de todos los demás:** build, release, run (05). Sin pipeline no hay forma
de garantizar que lo que se probó es lo que se desplegó. Corresponde a la S08.

---

## Autoría

Auditoría elaborada por Fernando Ureta (Tech Lead) por disponibilidad de tiempo del equipo.

El **factor 10, dev/prod parity**, lo aportó Matías Casa (QA Lead) en el issue #43, y se
incorpora aquí con su contenido.

Las decisiones de arquitectura auditadas provienen del ADR 0002 y el ADR 0003.
