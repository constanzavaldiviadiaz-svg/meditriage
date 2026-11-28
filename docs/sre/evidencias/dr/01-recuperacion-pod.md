# Evidencia — Recuperación automática de un pod

**Fecha:** 26/11/2026 (hora de Chile).

**Responsable:** Matías Sepúlveda — DevSecOps Lead.

**Contexto:** kind-meditriage.

**Namespace aislado:** meditriage-dr-test.

## 1. Estado inicial

- Deployment: meditriage-api.
- Pod original: meditriage-api-59fb6ff49f-d5pj9.
- UID: ea6d9bbf-52af-4022-81b5-048e8edb698b.

## 2. Eliminación controlada

```text
pod "meditriage-api-59fb6ff49f-d5pj9" deleted from meditriage-dr-test namespace
```

## 3. Recuperación automática

```text
deployment "meditriage-api" successfully rolled out

Tiempo de recuperacion del Deployment: 1.7298326 segundos

NAME                              READY   STATUS    RESTARTS   AGE
meditriage-api-59fb6ff49f-9ggq5   1/1     Running   0          3s
```

## 4. Verificación HTTP

### GET /health

```text
HTTP/1.1 200 OK
x-trace-id: 85992db53e10

{"estado":"ok"}
```

### GET /ready

```text
HTTP/1.1 200 OK
x-trace-id: 9edb63ac4109

{"estado":"listo","ambiente":"desarrollo"}
```

## 5. Resultados

| Indicador | Resultado |
|---|---|
| RTO propuesto | 120 segundos |
| Recuperación del Deployment | 1,7298326 segundos |
| Reemplazo automático del pod | Exitoso |
| Verificación de /health | HTTP 200 |
| Verificación de /ready | HTTP 200 |
| RTO del servicio HTTP | No medido |
| RPO | No verificable |

## 6. Conclusión

Kubernetes reemplazó automáticamente el pod eliminado y recuperó la disponibilidad del Deployment. Posteriormente, ambos endpoints de salud respondieron correctamente.

La prueba se realizó en un namespace aislado, sin intervenir directamente el Deployment principal gestionado por Argo CD.

Esta validación no demuestra alta disponibilidad, recuperación de datos persistentes ni recuperación completa del clúster.

## 7. Origen de la evidencia

Transcripción parcial de las salidas originales de PowerShell obtenidas durante la ejecución de la prueba local. No se capturaron imágenes durante el procedimiento.

Esta prueba corresponde a la validación preliminar del runbook de la issue #128 y no sustituye el Game Day de la issue #129.