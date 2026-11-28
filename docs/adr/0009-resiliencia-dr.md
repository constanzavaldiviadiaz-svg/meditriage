# ADR 0009 — Resiliencia y recuperación ante desastres

## Estado

Propuesto — 26/11/2026

Pasa a *Aceptado* cuando el equipo apruebe el Pull Request correspondiente.

## Autores

Matías Sepúlveda (DevSecOps Lead).

## Contexto

MediTriage es un sistema de apoyo a la priorización clínica cuya continuidad operacional resulta fundamental para la atención de pacientes.

Las decisiones arquitectónicas anteriores establecen las bases de su recuperación:

- El ADR 0002 define un monolito modular.
- El ADR 0003 establece el uso de servicios gestionados y el patrón Circuit Breaker.
- El ADR 0004 define PostgreSQL, Redis y mecanismos de auditoría inmutable.
- El ADR 0005 establece Kubernetes e infraestructura como código.
- La issue #127 define los SLOs y mecanismos de observabilidad.

La arquitectura debe responder ante fallos parciales y desastres completos sin comprometer la integridad de los datos clínicos ni delegar decisiones clínicas exclusivamente en la inteligencia artificial.

## Decisión

### 1. Objetivos de recuperación

Se establecen dos indicadores:

- **RTO (Recovery Time Objective):** tiempo objetivo máximo para recuperar una capacidad afectada.
- **RPO (Recovery Point Objective):** pérdida máxima de datos tolerable, expresada como intervalo temporal.

| Escenario | RTO propuesto | RPO propuesto |
|---|---|---|
| Caída de una réplica | 2 minutos | 0 para datos persistidos |
| Indisponibilidad de IA | Triage manual en máximo 3 segundos | 0 datos clínicos |
| Pérdida del clúster | 30 minutos | 0 para datos persistidos externamente |
| Falla de PostgreSQL | 60 minutos | 5 minutos |
| Falla del almacén de auditoría | 60 minutos | 0 decisiones confirmadas |

Estos valores corresponden a objetivos de diseño, no a resultados medidos ni garantías contractuales. Su cumplimiento debe verificarse mediante pruebas de recuperación.

El SLO de disponibilidad del 99,5 % mensual establece un presupuesto de error de 216 minutos para un mes de 30 días. Los incidentes que afecten la disponibilidad consumen dicho presupuesto.

### 2. Degradación controlada ante fallos de IA

Se utiliza el patrón Circuit Breaker definido en el ADR 0003.

El circuito contempla tres estados:

- **Cerrado:** las solicitudes se envían normalmente al servicio de IA.
- **Abierto:** se evita llamar al servicio indisponible y se deriva al flujo de triage manual.
- **Semiabierto:** se realizan solicitudes controladas para comprobar la recuperación del servicio.

La indisponibilidad de la IA no debe impedir la evaluación clínica manual. La enfermera mantiene la responsabilidad sobre la categoría final del paciente.

Las decisiones manuales deben quedar registradas en el sistema de auditoría, indicando el motivo de la contingencia.

### 3. Recuperación de la plataforma Kubernetes

Kubernetes reemplaza automáticamente los pods que fallen mediante la reconciliación del estado deseado.

Las sondas de salud y disponibilidad permiten detectar instancias defectuosas y evitar que reciban tráfico.

Ante la pérdida completa del clúster, la recuperación contempla:

1. Reconstruir la infraestructura base.
2. Restaurar los componentes de plataforma y configuración.
3. Recuperar los Secrets desde sus fuentes autorizadas.
4. Restablecer Argo CD.
5. Reconciliar el estado deseado desde el repositorio GitOps.
6. Verificar la disponibilidad de la aplicación y sus dependencias.

GitOps permite reconstruir los recursos declarativos, pero no sustituye los respaldos de datos persistentes ni de credenciales.

La recuperación de Argo CD utilizará el manifiesto declarativo `argocd/meditriage-dev.yaml` del repositorio GitOps, conforme a la estrategia propuesta en el ADR 0006. Su incorporación a main está pendiente de la integración del PR #5 de GitOps.

La reconciliación automática mediante SelfHeal fue validada en el clúster local. Esta evidencia no constituye una prueba de recuperación completa del clúster ni permite confirmar el cumplimiento del RTO establecido para dicho escenario.

### 4. Recuperación de PostgreSQL y Redis

PostgreSQL constituye la fuente de verdad de los datos clínicos.

Se propone utilizar las capacidades de respaldo automatizado y recuperación a un punto en el tiempo (PITR) del futuro servicio gestionado.

La restauración debe realizarse inicialmente sobre una instancia aislada, verificando su integridad antes de redirigir las conexiones de la aplicación.

Redis no constituye la fuente de verdad de los encuentros clínicos. Ante su pérdida, la información necesaria para reconstruir la sala de espera debe recuperarse desde PostgreSQL, conforme al ADR 0004.

### 5. Protección y recuperación de auditoría

Se mantienen las cuatro capas de protección definidas en el ADR 0004:

- Permisos de escritura restringidos a INSERT.
- Protección contra modificaciones y eliminaciones.
- Cadena de hashes para verificar la integridad.
- Respaldos inmutables mediante almacenamiento WORM durante cinco años.

La recuperación debe preservar los registros originales y verificar la continuidad de la cadena de integridad.

El objetivo de RPO cero para decisiones confirmadas requiere mecanismos durables de persistencia y confirmación, cuya implementación y validación permanecen pendientes.

### 6. Procedimientos operacionales y Game Day

Los procedimientos de diagnóstico, recuperación y verificación se documentan en el [runbook de recuperación](../sre/runbook.md).

El DevSecOps Lead mantiene el runbook y coordina la recuperación de infraestructura.

El Tech Lead participa en la recuperación de las dependencias de IA y datos.

El QA Lead ejecuta el Game Day correspondiente a la issue #129, registra los tiempos observados y verifica los resultados.

La Product Owner participa en la evaluación del impacto operacional y la comunicación de incidentes.

## Consecuencias

### Positivas

- Recuperación reproducible de infraestructura mediante código y GitOps.
- Menor dependencia del servicio externo de IA.
- Objetivos de recuperación explícitos y medibles.
- Protección de la integridad y trazabilidad de las decisiones clínicas.
- Procedimientos operacionales disponibles para todo el equipo.

### Negativas

- Costos adicionales asociados a respaldos, almacenamiento inmutable y servicios gestionados.
- Necesidad de realizar pruebas periódicas de restauración.
- Dependencia de la disponibilidad de los repositorios, registros de imágenes y servicios externos.
- Mayor complejidad operacional para mantener credenciales y configuraciones recuperables.

## Alternativas consideradas

| Alternativa | Motivo de descarte |
|---|---|
| Recuperación completamente manual | Mayor tiempo de recuperación y riesgo de errores humanos. |
| Respaldos sin protección contra modificaciones | No garantiza la integridad requerida para la auditoría. |
| Bloquear el triage cuando falla la IA | Compromete la continuidad operacional. |
| Replicación multirregión activa-activa | Complejidad y costos desproporcionados para el alcance actual del proyecto. |

## Estado de implementación y limitaciones

Al 26/11/2026, el entorno local dispone de:

- Clúster Kind operativo.
- Deployment de MediTriage con una réplica disponible.
- Argo CD con la aplicación meditriage-dev en estado Synced y Healthy.

La aplicación todavía utiliza almacenamiento en memoria. Por lo tanto, el reinicio de un pod puede provocar pérdida de datos de prueba.

Los objetivos de recuperación de PostgreSQL, Redis, auditoría WORM y Circuit Breaker corresponden a capacidades arquitectónicas pendientes de implementación o validación.

La recuperación completa del clúster y el cumplimiento de los RTO y RPO no se consideran demostrados hasta contar con evidencia de las pruebas correspondientes.

## Cuándo revisar esta decisión

- Cuando se seleccione el proveedor cloud.
- Cuando se incorporen PostgreSQL, Redis y el almacén de auditoría.
- Cuando se implemente el Circuit Breaker.
- Después de cada Game Day o incidente relevante.
- Cuando los tiempos observados superen los objetivos establecidos.

## Referencias

- [ADR 0002 — Estilo arquitectónico](0002-estilo-arquitectonico.md)
- [ADR 0003 — Cloud style](0003-cloud-style.md)
- [ADR 0004 — Datos y eventos](0004-datos-y-eventos.md)
- [ADR 0005 — Plataforma Kubernetes](0005-plataforma-k8s.md)
- [SLOs y observabilidad](../sre/slos.md)
- [Issue #128 — Plan de DR](https://github.com/constanzavaldiviadiaz-svg/meditriage/issues/128)
- [Issue #129 — Game Day](https://github.com/constanzavaldiviadiaz-svg/meditriage/issues/129)