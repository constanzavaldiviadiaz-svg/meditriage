# FinOps de infraestructura — MediTriage

**Issue:** #130 (S18) · **Fecha:** 27/11/2026 (Chile, UTC−03:00) · **Responsable:** Matías Sepúlveda, DevSecOps Lead.

## Objetivo y alcance

Reducir recursos sobredimensionados en desarrollo, ajustar réplicas según demanda y establecer etiquetas comunes. Este informe es insumo para #131; la palanca de IA corresponde a #124. Los resultados provienen de un ensayo local, no de facturación cloud.

## Tagging

| Etiqueta | Valor |
|---|---|
| `project` | `meditriage` |
| `environment` | `development` / `production` |
| `cost-center` | `meditriage` (identificador propuesto, no código contable oficial) |

Terraform centraliza `local.common_labels` en `main.tf` y las aplica al namespace y Secret de demostración (`secrets.tf`). Su alcance actual es desarrollo y recursos Kubernetes, no etiquetas de un proveedor cloud. Kustomize propaga etiquetas a ConfigMap, Service, Deployment, plantilla de pods, Ingress y HPA sin alterar selectores (`includeSelectors: false`, `includeTemplates: true`). El repositorio principal `k8s/` representa desarrollo; GitOps distingue ambientes mediante overlays.

## Configuración propuesta

| Parámetro | Línea base experimental | Dev | Prod |
|---|---:|---:|---:|
| Réplicas | 3 fijas | 1–3 | 3–6 |
| CPU request/pod | 200m | 100m | 200m |
| CPU limit/pod | 1000m | 500m | 1000m |
| RAM request/pod | 256Mi | 128Mi | 256Mi |
| RAM limit/pod | 512Mi | 256Mi | 512Mi |
| HPA CPU objetivo | — | 70% | 70% |

Palanca 1: reducir requests y limits por pod en desarrollo en 50%. Palanca 2: ajustar réplicas según ambiente y demanda mediante HPA. Ambas se ensayaron conjuntamente; no se midió el efecto aislado de cada cambio. Producción conserva recursos originales; su máximo de seis réplicas es una propuesta sin ensayo operativo.

## Metodología

Clúster `kind-meditriage`, namespace aislado `meditriage-finops-test`, misma imagen en ambas fases: `ghcr.io/constanzavaldiviadiaz-svg/meditriage-api@sha256:5bb8eb9ada9cda3fcbd9a4e13cba365b1d494ecc574109c8253e2f23b9c89907`. Metrics-server Helm chart 3.14.0, aplicación v0.9.0. Línea base desde manifiestos de `origin/main`, adaptando namespace y AMBIENTE a desarrollo, sin Ingress. Tres muestras por condición separadas aproximadamente 30 segundos. Carga ligera: tandas secuenciales de diez GET a `/health` y pausa de un segundo, desde BusyBox 1.37. Se repitió el patrón tras ajustar recursos y réplicas. El HPA se ensayó después, por separado, con ocho bucles concurrentes.

## Resultados

Promedios de la suma de consumo de los pods de la API, excluyendo generador y componentes del clúster. `m` = millicores; `Mi` = MiB. Reducción = (antes − después) / antes × 100, calculada con promedios sin redondear.

| Indicador | Antes | Después | Reducción |
|---|---:|---:|---:|
| CPU reposo | 9m | 3m | 66,67% |
| RAM reposo | 91,33Mi | 30Mi | 67,15% |
| CPU carga | 37,33m | 25m | 33,04% |
| RAM carga | 92,67Mi | 31Mi | 66,55% |

| Recursos configurados totales | Antes (3) | Después (1) | Reducción |
|---|---:|---:|---:|
| CPU request | 600m | 100m | 83,33% |
| CPU limit | 3000m | 500m | 83,33% |
| RAM request | 768Mi | 128Mi | 83,33% |
| RAM limit | 1536Mi | 256Mi | 83,33% |

Los requests representan reservas de planificación; los limits son topes, no reservas. La reducción del 83,33% corresponde a la comparación experimental de tres contra un pod. El entorno Dev activo ya tenía una réplica; a igualdad de réplicas la reducción configurada por pod es 50%. No equivale a ahorro monetario ni garantiza menor costo del nodo. Bajo carga ligera el pod optimizado utilizó 25% de su request de CPU.

## HPA y GitOps

El HPA local mostró `AbleToScale=True`, `ScalingActive=True`, `ScalingLimited=False` en reposo. Con carga concurrente pasó de 1 a 3 réplicas; tras eliminar el generador regresó a 1 con CPU al 3%. Durante la carga intensa permaneció por encima del objetivo incluso con tres réplicas; no se demuestra capacidad suficiente para esa demanda.

[PR GitOps #3 (borrador)](https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops/pull/3): base con HPA, overlays dev/prod, Application declarativa con `ignoreDifferences` para `/spec/replicas` y `RespectIgnoreDifferences=true`. Se elimina la cantidad fija de réplicas. Antes de fusionar, coordinar la aplicación del manifiesto `argocd/meditriage-dev.yaml` (fuera del overlay), revisar transición de propiedad de réplicas y verificar sincronización, salud y HPA en el entorno activo. No aplicar los manifiestos locales directamente sobre recursos gestionados por Argo CD. Ambos overlays y la Application pasaron dry-run server-side; no se realizó sincronización real.

## Evidencias y validación

- [Mediciones antes](evidencias/01-mediciones-antes.md).
- [Mediciones después](evidencias/02-mediciones-despues.md).
- [Escalado HPA](evidencias/03-escalado-hpa.md).
- [Validaciones](evidencias/04-validaciones.md).

Las salidas textuales son transcripciones de la sesión, no logs originales exportados. Se adjuntan las capturas disponibles de la fase optimizada y HPA.

## Limitaciones y pendientes

- Ensayo breve de `/health`, sin datos clínicos, sin medición de latencia, throughput exacto, errores HTTP agregados ni throttling/OOM. No se confirmó ausencia de mensajes ERROR durante las cargas.
- No se aisló el efecto individual de requests/limits y réplicas; las muestras de metrics-server son instantáneas agregadas, no un estudio estadístico de capacidad.
- Almacenamiento actual en memoria por réplica: no habilitar uso clínico multirréplica sin persistencia compartida y pruebas de consistencia. Producción no desplegada.
- Terraform validado sin apply; no se verificó estado remoto ni facturación. `--kubelet-insecure-tls` solo para Kind.
- PR principal, CI, revisión y merge pendientes al redactar. Eliminar namespace de pruebas al finalizar y verificar entorno activo; no se acredita limpieza aún.

## Criterios del issue #130

- Etiquetas en Terraform y `k8s/`: incorporadas y validadas localmente.
- Mediciones antes/después documentadas como insumo de #131: incluidas en este informe y anexos.
- Aceptación final sujeta a revisión y merge de los cambios; no se declara cerrado el issue.
