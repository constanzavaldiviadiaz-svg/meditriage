# Prueba de escalamiento horizontal (HPA) — Issue #70

## 1. Configuración y justificación
- **Mínimo de réplicas (`minReplicas: 3`):** El SLO de disponibilidad es del 99,5 %, por lo que mantener una sola réplica introduce punto único de falla ante reinicios o caídas. Tres réplicas aseguran alta disponibilidad base.
- **Máximo de réplicas (`maxReplicas: 6`):** Duplica la capacidad base sin saturar los recursos del nodo local (`kind`).
- **Umbral objetivo (`averageUtilization: 70`):** Escala cuando el consumo promedio supera el 70 % de los `200m` de CPU solicitados por pod en `k8s/deployment.yaml`.

## 2. Procedimiento de prueba
1. Clúster local levantado con `kind`, `traefik` y `metrics-server`.
2. Umbral ajustado temporalmente en local a `20 %` para forzar el escalamiento durante la ventana de prueba.
3. Generación de carga sintética con `k6` contra `http://localhost:8088/health` (hasta 60 usuarios virtuales durante 2 minutos).

## 3. Resultados observados
| Métrica | Valor observado |
| :--- | :--- |
| Réplicas iniciales | 3 |
| Réplicas máximas alcanzadas | _(completar)_ |
| Tiempo en iniciar escalamiento | _(completar)_ |
| Uso máximo de CPU por pod | _(completar)_ |

## 4. Limitaciones detectadas
- Mientras el almacenamiento permanezca en memoria (`src/registro/almacen.py`), cada réplica mantiene su propio estado local. La consistencia entre réplicas depende de la integración con PostgreSQL (Issue #121).
