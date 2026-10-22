# MediTriage — Triage clínico asistido por IA

Sistema que utiliza inteligencia artificial para ayudar a ordenar y priorizar pacientes según
sus síntomas y signos vitales, en la sala de espera de centros de atención primaria.

## Objetivo

Reducir el tiempo de priorización del triage de 25 minutos a menos de 3 minutos, entregando a
la enfermera una sugerencia de categoría ESI (1 a 5) acompañada de su justificación.

## Equipo

| Integrante | Rol |
|---|---|
| Constanza Valdivia | Product Owner |
| Fernando Ureta | Tech Lead · AI/Data Lead |
| Matías Sepúlveda | DevSecOps Lead |
| Matías Casa | QA Lead |

## Documentación

**Acuerdos del equipo**

* [CHARTER](CHARTER.md) — misión, roles, valores, política de uso de IA y Definition of Done
* [CONTRIBUTING](CONTRIBUTING.md) — cómo se contribuye: ramas, commits y Pull Requests

**Requisitos y producto**

* [Impact Map](docs/impact-map.md) — objetivo, actores, impactos, entregables y trazabilidad
* [Backlog](docs/backlog.md) — historias de usuario, priorización MoSCoW y checklist INVEST
* [Escenarios Gherkin](docs/scenarios/) — criterios de aceptación, un archivo por historia

**Arquitectura**

* [ADR 0001 — Elección de iniciativa](docs/adr/0001-eleccion-iniciativa.md)
* [ADR 0002 — Elección del estilo arquitectónico](docs/adr/0002-estilo-arquitectonico.md)
* [Diagramas C4](docs/c4/) — contexto (nivel 1) y contenedores (nivel 2)
* [Atributos de calidad](docs/arch/atributos-calidad.md) — los 3 NFRs prioritarios

## Cómo correr la aplicación

Requiere Python 3.11.

```bash
python -m venv .venv
.venv/Scripts/activate            # en Windows; en Linux o macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

python -m src.main                # la API queda en http://localhost:8080
pytest --cov=src                  # pruebas con cobertura
ruff check .                      # lint
```

Con la aplicación corriendo, la documentación interactiva está en http://localhost:8080/docs.

## Flujo de trabajo

Las convenciones de ramas, commits y Pull Requests están en [CONTRIBUTING.md](CONTRIBUTING.md).

La rama `main` requiere Pull Request y aprobación de otro integrante antes de integrar
cambios.
