# Estrategia de pruebas, trazabilidad y calidad — MediTriage

## 1. Regla de cobertura del 70 %
El pipeline de integración continua (`.github/workflows/ci.yml`) ejecuta `pytest --cov=src --cov-fail-under=70`, bloqueando cualquier Pull Request cuya cobertura de líneas sobre `src/` caiga por debajo del 70 %.

## 2. Trazabilidad entre Historias de Usuario, Gherkin y Pruebas

| Historia | Descripción resumida | Escenario Gherkin | Operación OpenAPI | Estado y cobertura de pruebas |
| :--- | :--- | :--- | :--- | :--- |
| **HU01** | Registro de paciente con validación de RUT y consentimiento | `docs/scenarios/hu01.feature` | `POST /v1/pacientes` (`registrarPaciente`) | **Implementado:** `tests/test_pacientes.py`, `tests/test_rut.py` y contract test en CI con Schemathesis. |
| **HU02** | Apertura de encuentro y registro de signos vitales | `docs/scenarios/hu02.feature` | `POST /v1/encuentros`, `PUT /v1/encuentros/{id}/datos-clinicos` | **Pendiente de implementación (Issue #122):** pruebas de contrato e integración se activarán al fusionar #121 y #122. |
| **HU03** | Evaluación asistida por IA y confirmación de categoría ESI | `docs/scenarios/hu03.feature` | `POST /v1/encuentros/{id}/evaluaciones`, `PUT /v1/encuentros/{id}/categoria-final` | **Pendiente de implementación (Issues #122 y #123).** |
| **HU04** | Visualización de sala de espera ordenada por prioridad ESI | `docs/scenarios/hu04.feature` | `GET /v1/sala-de-espera` | **Pendiente de implementación (Issue #122).** |
| **HU05** | Consulta de auditoría inmutable de decisiones | `docs/scenarios/hu05.feature` | `GET /v1/auditoria/decisiones` | **Pendiente de implementación (Issues #121 y #122).** |
| **HU06** | Derivación automática a triage manual por timeout de IA | `docs/scenarios/hu06.feature` | `POST /v1/encuentros/{id}/evaluaciones` (respuesta `201` derivada) | **Pendiente de implementación (Issue #123).** |
| **NFR** | Observabilidad y salud del servicio (`/health`, `/metrics`) | N/A (Atributos de calidad) | `GET /health` | **Implementado:** `tests/test_observabilidad.py`. |

## 3. Contract Tests en CI (Schemathesis)
- **Herramienta:** Schemathesis ejecutado contra `api/openapi.yaml` en `.github/workflows/ci.yml`.
- **Alcance actual:** Ejecuta pruebas generativas sobre `registrarPaciente` (`POST /v1/pacientes`), validando conformidad de códigos de estado, encabezados `Content-Type`, ausencia de errores `5xx` y estructura JSON según el esquema OpenAPI.
- **Limitaciones declaradas:**
  - Las 8 operaciones restantes del contrato aún no tienen ruta en `src/` (responderían `404`), por lo que se excluyen mediante `--include-operation-id registrarPaciente` hasta que se fusione el Issue #122.
  - La validación de tokens OAuth2 (`401`/`403`) no está implementada en la capa actual de la API, por lo que dichos códigos no se ejercitan en esta fase.

## 4. Demostración de efectividad de pruebas (Mutación en vivo)
Para verificar que las pruebas detectan fallas reales y no son tautológicas, se dispone del script `scripts/demo_mutacion.py`, que inyecta fallas controladas en funciones críticas y verifica que `pytest` falle antes de restaurar el código:
1. `calcular_digito_verificador` (`src/registro/rut.py`): detectado por `tests/test_rut.py`.
2. `enmascarar_rut` (`src/registro/rut.py`): detectado por `tests/test_rut.py` (evita exposición de PII).
3. `obtener_por_idempotencia` (`src/registro/almacen.py`): detectado por `tests/test_pacientes.py` (evita registros duplicados).

## 5. Pruebas de integración con PostgreSQL
- **Estado:** Bloqueado por dependencias externas (**Issue #121** — persistencia PostgreSQL y tabla append-only de auditoría; **Issue #122** — flujo clínico).
- Una vez fusionados ambos issues, se incorporará el servicio `postgres` en el CI y las pruebas de integración sin almacenamiento en memoria.
