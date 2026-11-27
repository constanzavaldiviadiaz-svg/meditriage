# MediTriage — Runbook de recuperación ante desastres

## 1. Propósito

Establecer procedimientos de diagnóstico, recuperación y verificación ante incidentes que afecten la continuidad operacional de MediTriage.

Este documento implementa las decisiones del ADR 0009 y sirve como guía para el Game Day de la issue #129.

**Responsable:** Matías Sepúlveda (DevSecOps Lead).

**Fecha:** 26/11/2026.

**Estado:** Propuesto.

## 2. Objetivos de recuperación

| Incidente | RTO objetivo | RPO objetivo |
|---|---|---|
| Caída de un pod | 2 minutos | 0 para datos persistidos |
| Caída de IA | Derivación manual en 3 segundos | 0 datos clínicos |
| Pérdida del clúster | 30 minutos | 0 para datos persistidos externamente |
| Falla de PostgreSQL | 60 minutos | 5 minutos |
| Falla de auditoría | 60 minutos | 0 decisiones confirmadas |

Los objetivos deben validarse experimentalmente. No representan garantías de la implementación actual.

## 3. Responsabilidades

| Rol | Responsabilidad |
|---|---|
| DevSecOps Lead | Diagnóstico, infraestructura, recuperación y coordinación técnica. |
| Tech Lead / AI Data Lead | Recuperación de IA, PostgreSQL, Redis y auditoría. |
| QA Lead | Ejecución del Game Day, medición y registro de evidencias. |
| Product Owner | Evaluación del impacto y comunicación del incidente. |

## 4. Requisitos previos

- Docker Desktop operativo.
- Kind, kubectl, Helm y Terraform instalados.
- Acceso autorizado a los repositorios de MediTriage y GitOps.
- Acceso a HCP Terraform cuando corresponda.
- Acceso autorizado al registro de imágenes.
- PowerShell para ejecutar los comandos de este documento.

Las pruebas deben utilizar exclusivamente datos ficticios.

No eliminar el clúster principal ni modificar recursos de producción durante un Game Day sin autorización explícita.

## 5. Diagnóstico inicial

Ejecutar desde la raíz del repositorio:

```powershell
Get-Date -Format o
kubectl config current-context
kubectl get nodes
kubectl get deployments -n meditriage
kubectl get pods -n meditriage
kubectl get services -n meditriage
kubectl get applications -n argocd
kubectl get events -n meditriage --sort-by=.metadata.creationTimestamp
```

El estado esperado es:

- Contexto: kind-meditriage.
- Nodo: Ready.
- Deployment: réplicas disponibles.
- Pods: Running y Ready.
- Argo CD: Synced y Healthy.

Registrar la hora de detección, los componentes afectados y el impacto observado.

## 6. Incidente 1 — Caída de un pod

### Detección

Un pod presenta errores, reinicios continuos o deja de estar disponible.

```powershell
kubectl get pods -n meditriage
kubectl describe deployment meditriage-api -n meditriage
kubectl logs deployment/meditriage-api -n meditriage --tail=100
```

Si el contenedor se ha reiniciado, consultar también los logs de la instancia anterior mediante kubectl logs con la opción --previous.

### Recuperación

Kubernetes debe reconciliar automáticamente el Deployment y reemplazar los pods que fallen.

Para comprobar este comportamiento sin afectar la aplicación principal, crear un Deployment aislado utilizando la misma imagen desplegada.

```powershell
$imagen = kubectl --context kind-meditriage get deployment meditriage-api -n meditriage -o jsonpath='{.spec.template.spec.containers[0].image}'

kubectl --context kind-meditriage create namespace meditriage-dr-test

kubectl --context kind-meditriage create deployment meditriage-api --image=$imagen -n meditriage-dr-test

kubectl --context kind-meditriage rollout status deployment/meditriage-api -n meditriage-dr-test --timeout=120s
```

No continuar si el Deployment de prueba no está disponible.

Identificar el pod y registrar el inicio del incidente:

```powershell
$pod = kubectl --context kind-meditriage get pods -n meditriage-dr-test -l app=meditriage-api -o jsonpath='{.items[0].metadata.name}'

$inicio = Get-Date

kubectl --context kind-meditriage delete pod $pod -n meditriage-dr-test --wait=true

kubectl --context kind-meditriage rollout status deployment/meditriage-api -n meditriage-dr-test --timeout=120s

kubectl --context kind-meditriage get pods -n meditriage-dr-test
```

### Verificación

Comprobar que existe un pod nuevo y que el Deployment recuperó su disponibilidad.

```powershell
kubectl --context kind-meditriage get deployments -n meditriage-dr-test
kubectl --context kind-meditriage get pods -n meditriage-dr-test
```

En una terminal independiente, abrir un port-forward:

```powershell
kubectl --context kind-meditriage port-forward deployment/meditriage-api 8085:8080 -n meditriage-dr-test
```

En la terminal original:

```powershell
curl.exe -f http://localhost:8085/health
curl.exe -f http://localhost:8085/ready
```

Si ambas comprobaciones son exitosas, registrar el tiempo transcurrido:

```powershell
$fin = Get-Date
($fin - $inicio).TotalSeconds
```

El tiempo obtenido incluye la recuperación del pod y la verificación manual de los endpoints.

### Criterio de éxito

- El pod eliminado es reemplazado automáticamente.
- El Deployment recupera su disponibilidad.
- Los endpoints de salud responden correctamente.
- El tiempo observado se compara con el RTO de 120 segundos.

Esta prueba verifica la recuperación de un pod, no la alta disponibilidad ni la recuperación de datos persistentes.

### Limpieza

Detener el port-forward con Ctrl+C.

Después de guardar las evidencias, eliminar exclusivamente el namespace temporal:

```powershell
kubectl --context kind-meditriage delete namespace meditriage-dr-test
```

## 7. Incidente 2 — Pérdida completa del clúster

### Detección

```powershell
kind get clusters
kubectl --context kind-meditriage get nodes
```

Si el clúster existe, comprobar primero Docker Desktop y la conectividad antes de intentar reconstruirlo.

### Recuperación de infraestructura

Este procedimiento se ejecuta únicamente cuando se confirma la pérdida del clúster o en un entorno de recuperación autorizado.

Desde la raíz del repositorio:

```powershell
kind create cluster --config cluster-local/kind.yaml

helm repo add traefik https://traefik.github.io/charts
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo update

helm upgrade --install traefik traefik/traefik --namespace traefik --create-namespace --values cluster-local/traefik.yaml --wait

helm upgrade --install metrics-server metrics-server/metrics-server --namespace kube-system --values cluster-local/metrics-server.yaml --wait
```

Recuperar el namespace y los Secrets mediante Terraform:

```powershell
terraform -chdir=terraform init
terraform -chdir=terraform plan
```

Revisar el plan antes de aplicar:

```powershell
terraform -chdir=terraform apply
```

Si no existe acceso a HCP Terraform, el README del clúster permite crear manualmente el namespace para desarrollo local:

```powershell
kubectl create namespace meditriage
```

Esta alternativa no restaura credenciales ni sustituye la recuperación del estado de Terraform.

### Recuperación mediante GitOps

Restablecer Argo CD:

```powershell
kubectl create namespace argocd

kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.6.2/manifests/install.yaml

kubectl rollout status deployment/argocd-server -n argocd --timeout=300s
```

Restablecer las credenciales autorizadas de acceso al repositorio GitOps y al registro de imágenes, si son necesarias.

Registrar la aplicación declarativa:

```powershell
@'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: meditriage-dev
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops.git
    targetRevision: main
    path: overlays/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: meditriage
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
'@ | kubectl apply -f -
```

Argo CD debe reconciliar los recursos declarados en el repositorio GitOps.

### Verificación

```powershell
kubectl get applications -n argocd
kubectl get pods -n meditriage
kubectl rollout status deployment/meditriage-api -n meditriage --timeout=300s
kubectl get ingress -n meditriage
```

Comprobar los endpoints mediante un port-forward al Service:

```powershell
kubectl port-forward service/meditriage-api 8085:8080 -n meditriage
```

Desde otra terminal:

```powershell
curl.exe -f http://localhost:8085/health
curl.exe -f http://localhost:8085/ready
```

### Criterio de éxito

- Infraestructura base operativa.
- Argo CD en estado Synced y Healthy.
- Deployment disponible.
- Endpoints de salud operativos.
- Tiempo de recuperación comparado con el RTO de 30 minutos.

### Alternativa de emergencia

Si GitOps no está disponible, el README del proyecto contempla el despliegue manual:

```powershell
kubectl apply -k k8s/
```

Esta alternativa requiere autorización y verificación de los manifiestos. No debe utilizarse mientras Argo CD esté reconciliando los mismos recursos.

La recuperación manual debe registrarse como una desviación temporal del estado declarativo.

## 8. Incidente 3 — Falla del servicio de IA

### Detección

- Errores o timeouts del proveedor de IA.
- Aumento de la latencia.
- Fallos consecutivos de las solicitudes de evaluación.

Consultar los logs de la aplicación:

```powershell
kubectl logs deployment/meditriage-api -n meditriage --tail=100
```

Revisar las métricas y los SLOs documentados en slos.md.

### Recuperación

1. Detectar la indisponibilidad de la dependencia.
2. Permitir que el Circuit Breaker abra el circuito.
3. Derivar las evaluaciones al flujo de triage manual.
4. Mantener la decisión clínica bajo responsabilidad de la enfermera.
5. Registrar el motivo de la contingencia en auditoría.
6. Verificar la recuperación del proveedor.
7. Permitir solicitudes controladas en estado semiabierto.
8. Restablecer el flujo normal cuando la dependencia sea estable.

### Criterio de éxito

- La indisponibilidad de IA no bloquea la evaluación manual.
- La derivación ocurre dentro del objetivo de tres segundos.
- Las decisiones quedan registradas en auditoría.
- No se pierden datos clínicos confirmados.

**Limitación:** el Circuit Breaker y el flujo clínico completo requieren implementación y validación. Este procedimiento todavía no constituye una prueba ejecutable de extremo a extremo.

## 9. Contingencia de PostgreSQL, Redis y auditoría

### PostgreSQL

1. Identificar el incidente y detener las escrituras que puedan comprometer la integridad.
2. Seleccionar el último punto de recuperación válido.
3. Restaurar el respaldo mediante el servicio gestionado.
4. Verificar la integridad de los datos en una instancia aislada.
5. Actualizar las referencias de conexión mediante el mecanismo autorizado de gestión de Secrets.
6. Restablecer la aplicación y verificar sus operaciones.
7. Comparar el tiempo y punto de recuperación con los objetivos RTO y RPO.

### Redis

Reconstruir la información de los encuentros abiertos desde PostgreSQL, conforme al ADR 0004.

Redis no debe utilizarse como fuente de verdad de los datos clínicos.

### Auditoría

1. Identificar los registros afectados.
2. Recuperar las copias inmutables autorizadas.
3. Verificar la continuidad de la cadena de hashes.
4. Preservar los registros originales.
5. Documentar cualquier inconsistencia detectada.
6. Mantener la política de retención WORM de cinco años.

Los comandos específicos de restauración dependen del proveedor cloud seleccionado. Actualmente no existen instancias gestionadas ni respaldos verificados que permitan ejecutar estos procedimientos.

## 10. Registro del Game Day

El QA Lead debe registrar los siguientes datos por incidente:

| Campo | Resultado |
|---|---|
| Fecha y responsable | Pendiente |
| Escenario ejecutado | Pendiente |
| Hora de inicio | Pendiente |
| Hora de recuperación | Pendiente |
| Tiempo total observado | Pendiente |
| RTO objetivo | Según escenario |
| RPO observado | Pendiente o no verificable |
| Resultado | Pendiente |
| Evidencias | Pendiente |
| Hallazgos y mejoras | Pendiente |

No declarar un RPO de cero sin comprobar la persistencia y recuperación efectiva de los datos.

Las evidencias deben incluir comandos ejecutados, resultados, capturas y tiempos observados, sin exponer credenciales ni información clínica.

## 11. Cierre del incidente

- Confirmar la recuperación de los componentes afectados.
- Verificar la integridad de los datos cuando corresponda.
- Comprobar el estado de Argo CD.
- Registrar el impacto sobre los SLOs.
- Documentar la causa y las acciones correctivas.
- Comunicar el resultado al equipo.
- Actualizar el runbook cuando se identifiquen mejoras.

## 12. Estado actual y limitaciones

El entorno local dispone de un nodo Kind, una réplica de MediTriage y Argo CD operativo.

La aplicación utiliza almacenamiento en memoria, por lo que el reinicio de un pod puede provocar pérdida de datos de prueba.

La prueba aislada de recuperación de un pod permite validar la reconciliación de Kubernetes sin destruir el entorno principal.

La reconstrucción completa del clúster, la recuperación de PostgreSQL, el Circuit Breaker y los respaldos WORM requieren validaciones adicionales.

Los tiempos de recuperación no se consideran demostrados hasta ejecutar y documentar las pruebas correspondientes.

### Validación preliminar del runbook — 26/11/2026

Se ejecutó una prueba controlada de eliminación de un pod en el namespace aislado `meditriage-dr-test`, utilizando la misma imagen desplegada en el entorno principal.

| Comprobación | Resultado |
|---|---|
| Reconciliación automática de Kubernetes | Exitosa |
| Tiempo de recuperación del Deployment | 1,73 segundos |
| Objetivo de recuperación | 120 segundos |
| Endpoint /health | HTTP 200 |
| Endpoint /ready | HTTP 200 |
| RTO completo del servicio HTTP | No medido |
| RPO | No verificable |

La prueba confirma que Kubernetes reemplaza automáticamente el pod eliminado y que la aplicación responde posteriormente a las comprobaciones de salud.

Esta validación preliminar no sustituye el Game Day de la issue #129 ni demuestra la recuperación completa del clúster.

**Evidencia:** [Registro de recuperación automática del pod](evidencias/dr/01-recuperacion-pod.md).

## 13. Referencias

- [ADR 0009 — Resiliencia y recuperación ante desastres](../adr/0009-resiliencia-dr.md)
- [ADR 0003 — Cloud style](../adr/0003-cloud-style.md)
- [ADR 0004 — Datos y eventos](../adr/0004-datos-y-eventos.md)
- [ADR 0005 — Plataforma Kubernetes](../adr/0005-plataforma-k8s.md)
- [SLOs y observabilidad](slos.md)
- [Configuración del clúster local](../../cluster-local/README.md)
- [Repositorio GitOps](https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops)
- [Issue #128 — Plan de DR](https://github.com/constanzavaldiviadiaz-svg/meditriage/issues/128)
- [Issue #129 — Game Day](https://github.com/constanzavaldiviadiaz-svg/meditriage/issues/129)