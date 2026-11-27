# Evidencia 04 — Validaciones de infraestructura

Transcripción resumida de la sesión del 27/11/2026. No son logs originales exportados.

## Metrics-server

Inicialmente `kubectl top` devolvió `error: Metrics API not available` y el APIService no existía. Instalación local:

```powershell
helm upgrade --install metrics-server metrics-server/metrics-server --namespace kube-system --values cluster-local/metrics-server.yaml --kube-context kind-meditriage --wait --timeout 5m
```

Salida: `STATUS: deployed`, `REVISION: 1`, chart 3.14.0, app 0.9.0. Configuración TLS insegura exclusiva de Kind. Después `kubectl top` reportó el pod activo de MediTriage con 3m/50Mi y nodo con 314m/2069Mi (2% CPU, 26% RAM). Esta muestra del entorno activo no forma parte de la comparación aislada.

## Kubernetes y GitOps

Comandos ejecutados desde cada repositorio:

```powershell
# Repositorio principal
kubectl kustomize k8s/
kubectl --context kind-meditriage apply -k k8s/ --dry-run=server
# Repositorio GitOps
kubectl kustomize overlays/dev/
kubectl kustomize overlays/prod/
kubectl --context kind-meditriage apply -k overlays/dev/ --dry-run=server
kubectl --context kind-meditriage apply -k overlays/prod/ --dry-run=server
```

Los tres dry-run finales devolvieron:

```text
configmap/meditriage-config configured (server dry run)
service/meditriage-api configured (server dry run)
deployment.apps/meditriage-api configured (server dry run)
horizontalpodautoscaler.autoscaling/meditriage-api created (server dry run)
ingress.networking.k8s.io/meditriage-api configured (server dry run)
```

Render de overlays: etiquetas correctas en cinco recursos y plantilla de pods, selectores intactos, digest conservado, sin réplicas fijas, HPA 1–3 en dev y 3–6 en prod. El render inicial de `k8s/` detectó AMBIENTE inconsistente; se corrigió a desarrollo antes del dry-run final.

## Argo CD

`kubectl --context kind-meditriage get application meditriage-dev -n argocd -o yaml` mostró Synced/Healthy, targetRevision HEAD, overlays/dev, auto-sync habilitado, prune y selfHeal desactivados. Se creó Application declarativa en GitOps con exclusión de `/spec/replicas` y `RespectIgnoreDifferences=true`.

```powershell
kubectl --context kind-meditriage apply -f argocd/meditriage-dev.yaml --dry-run=server
```

Salida: `application.argoproj.io/meditriage-dev configured (server dry run)`. Advertencia por ausencia de anotación last-applied-configuration en la Application existente. No se ejecutó apply real.

## Terraform

Procedimiento indicado: `terraform fmt`, `terraform init -backend=false`, `terraform validate` desde `terraform/`. Resultado final comunicado por el usuario:

```text
Success! The configuration is valid.
```

No se dispone de salida completa de fmt/init ni se ejecutó apply.

## Control de versiones

GitOps: `git diff --cached --check` sin errores; seis archivos, 95 inserciones y 10 eliminaciones. [PR #3](https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops/pull/3) creado como borrador. CI, merge, aplicación efectiva de Argo CD y pruebas productivas no acreditados. PR principal pendiente al redactar.
