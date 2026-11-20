# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repositorio

MediTriage — Triage clínico asistido por IA. Proyecto del ramo **Taller de Ingeniería de
Software** (18 sesiones). No es un repo de producto: es un repo académico donde **cada
sesión de clase aporta un artefacto entregable**, evaluado con rúbrica.

**Sesión vigente: S07 y S08** (contenedores, K8s e IaC · CI/CD y GitOps), que se trabajan en
paralelo. De la S01 a la S06 fueron entregadas. No adelantarse a sesiones que el equipo aún no ha cursado: crear
artefactos de sesiones futuras desordena la cronología del repo y contradice la política de
IA del ramo. Actualizar esta línea al avanzar de sesión.

Estado actual: aplicación FastAPI mínima en `src/` (solo el registro de pacientes, HU01, con
almacenamiento en memoria), `Dockerfile`, manifiestos en `k8s/`, clúster local en
`cluster-local/` y un workflow de GitHub Actions que prueba y publica la imagen en GHCR.

## Idioma

Toda respuesta y todo documento en **español neutro/chileno**. Nunca rioplatense: usar "tú",
"aquí", "mira", "quieres" — no "vos", "acá", "mirá", "querés".

## Contexto de negocio (define los requisitos no funcionales)

Red de centros de atención primaria; priorizar pacientes en sala de espera con IA sobre
síntomas, historia clínica y signos vitales. Restricciones que vienen del enunciado del ramo
y que **no son negociables** al diseñar:

- **Datos sensibles**: normativa chilena Ley 19.628 y Ley 21.719. Cifrado en reposo y
  tránsito obligatorio. PII enmascarada en logs.
- **Explicabilidad**: el modelo debe justificar cada priorización ESI (1–5).
- **Latencia**: respuesta de triage < 3 s desde el envío del formulario.
- **Disponibilidad**: 99.5% mensual.
- **Auditoría**: cada decisión IA registrada e inmutable por 5 años.

Usuarios objetivo: Paciente · Enfermera de triage · Médico jefe de turno · Auditor clínico.

MVP definido por el ramo: registro de paciente con validación de RUT y consentimiento
informado · formulario de síntomas y signos vitales · motor IA que sugiere categoría ESI y
explica el porqué · tablero para personal médico con priorización dinámica · audit log.

## Equipo y límites de rol

- **Constanza Valdivia** (`constanzavaldiviadiaz-svg`) — Product Owner. **Dueña del repo**:
  única con permiso de admin, así que branch protection, settings y colaboradores son suyos.
- **Fernando Ureta** (`fernandoureta`) — Tech Lead + AI/Data Lead. Colaborador.
- **Matías Sepúlveda** (`ByRetro`) — DevSecOps Lead. Colaborador.
- **Matías Casa** (`redskull5`) — QA Lead. Colaborador.

Los límites importan:

- **Producto** (qué se construye, en qué orden, contenido del backlog): decide la PO.
  Proponer, no imponer.
- **Arquitectura, stack y ADRs**: decide el Tech Lead.
- **Pipelines, seguridad y protección de ramas**: decide el DevSecOps Lead.
- **Estrategia de pruebas y criterios de aceptación**: decide el QA Lead.

## Flujo de trabajo con Git

**La fuente canónica es [CONTRIBUTING.md](CONTRIBUTING.md).** Si algo aquí difiere de ese
archivo, manda CONTRIBUTING.md. Resumen para no tener que abrirlo en cada tarea:

- `main` es rama protegida: nadie commitea directo, ni la dueña del repo.
- Un issue = una rama = un PR. Ramas: `tipo/N-descripcion`, con `N` el número del issue.
  Prefijos: `feat/` `fix/` `docs/` `chore/`.
- El cuerpo del PR lleva `Closes #N` **en inglés**: en español GitHub no lo reconoce y el
  issue queda abierto.
- Merge con squash, borrando la rama. Nunca `force-push` a `main`.
- No fusionar el propio PR: la revisión de otro integrante es parte del Definition of Done.

Constanza trabaja desde el **editor web de GitHub**, no clona el repo. Cualquier propuesta de
flujo debe seguir siendo posible desde la web.

## Commits

**No escribir declaraciones de autoría IA en los mensajes de commit.** El ramo exige declarar
toda contribución hecha con IA, pero Fernando evalúa y redacta él esa declaración, porque es
él quien responde por ella ante el profesor. Entregar el mensaje sin esa sección y avisarle.

## Definition of Done (del CHARTER, es vinculante)

Una tarea está terminada cuando: cumple lo solicitado · fue probada · **fue revisada y
aprobada por al menos otro integrante mediante Pull Request** · si toca calidad, seguridad o
arquitectura, revisa además el rol responsable · se hizo el commit · el issue fue
actualizado o cerrado.

La revisión cruzada no es opcional: es la razón por la que existe el flujo de PRs.

## Convenciones de documentación

- `docs/adr/NNNN-titulo.md` — Architecture Decision Records. **Formato desde la S03**:
  **Título · Estado · Contexto · Decisión · Consecuencias · Alternativas descartadas**.
  Estado toma uno de: Propuesto · Aceptado · Reemplazado · Deprecado.
  El ADR 0001 usa el formato anterior de la S01, sin Estado ni Alternativas: **no se corrige**.
  **La numeración del profesor va corrida en uno**: lo que sus diapositivas llaman "ADR 0004"
  (plataforma K8s) es nuestro 0005, y su "ADR 0005" (GitOps) es nuestro 0006.
- `docs/c4/` — diagramas C4. Fuente `.puml` con la librería C4 (`!include <C4/C4_Context>`)
  más el `.png` exportado. Se entregan los niveles 1 y 2; el 3 solo para componentes críticos.
- `docs/arch/` — atributos de calidad y documentación de arquitectura.
- `docs/backlog.md`, `docs/impact-map.md`, `docs/scenarios/*.feature` — requisitos (S02).
- Documentación en español.

**Un ADR nunca se edita.** Si una decisión cambia, el anterior se marca como *Reemplazado* y
se escribe uno nuevo.

Con diagramas grandes, la URL hexadecimal del comando siguiente excede el límite: hay que
codificar con deflate (zlib sin cabecera) y el alfabeto base64 propio de PlantUML, y usar la
URL sin el `~h`.

Para renderizar un `.puml` a PNG sin instalar nada:
`curl -o salida.png "http://www.plantuml.com/plantuml/png/~h$(xxd -p archivo.puml | tr -d '\n')"`

## Decisiones de arquitectura vigentes

Del [ADR 0002](docs/adr/0002-estilo-arquitectonico.md):

- **Monolito modular** en cuatro módulos: Registro, Evaluación, Tablero y Auditoría.
- **El motor de IA es un servicio externo** consumido vía API. No se entrena modelo propio.
- **La escritura del audit log es asíncrona**, para no consumir el presupuesto de 3 segundos.

Consecuencias que condicionan cualquier diseño posterior:

- La latencia depende de un tercero, así que **HU06 (derivación a triage manual) es obligatoria**.
- Al servicio de IA **nunca se le envían RUT ni nombre**, solo datos clínicos despersonalizados.
- Las respuestas no son deterministas: el audit log guarda la respuesta exacta entregada.

Del [ADR 0004](docs/adr/0004-datos-y-eventos.md) (datos y eventos):

- **PostgreSQL** para identidad, clínico y auditoría (esta última append-only, en base
  separada); **Redis** para la vista de la sala de espera y como broker (Redis Streams).
- **Outbox** y **CQRS liviano** adoptados; Saga, Event Sourcing y CDC descartados.
- Entrega *at-least-once*: todo consumidor es idempotente por `evento_id`.

Del [ADR 0005](docs/adr/0005-plataforma-k8s.md) (plataforma):

- **Kubernetes gestionado** en producción, porque no amarra a un proveedor (el ADR 0003 lo
  dejó sin elegir). Las bases de datos quedan **fuera** del clúster, como servicios gestionados.
- **kind** en local, **Terraform** para la infraestructura, **Kustomize** para los manifiestos,
  **Traefik** como Ingress (ingress-nginx está retirado). Helm solo para componentes de terceros.
- **Frontera**: Terraform crea el namespace y los Secrets; los manifiestos no los declaran.
- Imagen **distroless**, no root, Python 3.11, referenciada por digest.

## Roadmap del ramo

Bloque A Fundamentos: S01 introducción · S02 requisitos. Bloque B Diseño y datos: S03
arquitectura y C4 · S04 12-Factor · S05 APIs · S06 datos. Bloque C Nube: S07 contenedores,
K8s, IaC · S08 CI/CD. Bloque D DevSecOps: S09 shift-left · S10 supply chain. Bloque E Calidad
e IA: S11 observabilidad · S12 testing · S13 LLM y RAG · S14 MLOps. Bloque F: S15 FinOps ·
S16 resiliencia · S17 presentación · S18 defensa final.

El ramo es explícitamente multi-stack (Python · Node · Java): la elección de stack es del
equipo y se documentará en un ADR cuando corresponda.
