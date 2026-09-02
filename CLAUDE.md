# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repositorio

MediTriage — Triage clínico asistido por IA. Proyecto del ramo **Taller de Ingeniería de
Software** (18 sesiones). No es un repo de producto: es un repo académico donde **cada
sesión de clase aporta un artefacto entregable**, evaluado con rúbrica.

**Sesión vigente: S02.** La S01 fue entregada y aprobada por el docente. No adelantarse a sesiones que el equipo aún no ha cursado: crear
artefactos de sesiones futuras desordena la cronología del repo y contradice la política de
IA del ramo. Actualizar esta línea al avanzar de sesión.

Estado actual: solo documentación, todavía no existe código.

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
- **Matías Casa** — QA Lead. **Todavía no agregado como colaborador del repositorio.**

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

- `docs/adr/NNNN-titulo.md` — Architecture Decision Records. Formato exigido por la rúbrica:
  **Título · Contexto · Decisión · Consecuencias · Fecha · Autores**. Numeración correlativa.
- Documentación en español.

Las convenciones de los artefactos de cada sesión (backlog, diagramas, pipelines) se agregan
aquí **cuando esa sesión llegue**, no antes.

## Roadmap del ramo

Bloque A Fundamentos: S01 introducción · S02 requisitos. Bloque B Diseño y datos: S03
arquitectura y C4 · S04 12-Factor · S05 APIs · S06 datos. Bloque C Nube: S07 contenedores,
K8s, IaC · S08 CI/CD. Bloque D DevSecOps: S09 shift-left · S10 supply chain. Bloque E Calidad
e IA: S11 observabilidad · S12 testing · S13 LLM y RAG · S14 MLOps. Bloque F: S15 FinOps ·
S16 resiliencia · S17 presentación · S18 defensa final.

El ramo es explícitamente multi-stack (Python · Node · Java): la elección de stack es del
equipo y se documentará en un ADR cuando corresponda.
