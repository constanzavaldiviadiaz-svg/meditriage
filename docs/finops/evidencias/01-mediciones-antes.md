# Evidencia 01 — Línea base

Transcripción de salidas compartidas el 27/11/2026, hora local Chile. Namespace `meditriage-finops-test`.

## Preparación

```powershell
kubectl --context kind-meditriage create namespace meditriage-finops-test
git archive --format=zip --output="$env:TEMP\meditriage-finops-baseline.zip" origin/main k8s/
Expand-Archive -Path "$env:TEMP\meditriage-finops-baseline.zip" -DestinationPath "$env:TEMP\meditriage-finops-baseline" -Force
$ruta = "$env:TEMP\meditriage-finops-baseline\k8s"
Get-ChildItem $ruta -Filter *.yaml | ForEach-Object {
    (Get-Content $_.FullName -Raw) -replace 'namespace: meditriage\b', 'namespace: meditriage-finops-test' -replace 'AMBIENTE: produccion', 'AMBIENTE: desarrollo' | Set-Content $_.FullName -Encoding utf8
}
kubectl --context kind-meditriage apply -f "$ruta\configmap.yaml" -f "$ruta\service.yaml" -f "$ruta\deployment.yaml" -n meditriage-finops-test
kubectl --context kind-meditriage rollout status deployment/meditriage-api -n meditriage-finops-test --timeout=120s
```

Salida: `deployment "meditriage-api" successfully rolled out`. Tres pods Running 1/1, cero reinicios. Requests 200m/256Mi y limits 1 CPU/512Mi por pod.

## Reposo

Comando de muestreo: `kubectl --context kind-meditriage top pods -n meditriage-finops-test`, tres veces con pausa de 30 s.

```text
00:32:06
meditriage-api-66b99568fd-dsggc   3m   30Mi
meditriage-api-66b99568fd-pccc7   3m   30Mi
meditriage-api-66b99568fd-x5mkh   3m   31Mi
00:32:36
meditriage-api-66b99568fd-dsggc   3m   31Mi
meditriage-api-66b99568fd-pccc7   3m   30Mi
meditriage-api-66b99568fd-x5mkh   3m   30Mi
00:33:06
meditriage-api-66b99568fd-dsggc   3m   31Mi
meditriage-api-66b99568fd-pccc7   3m   30Mi
meditriage-api-66b99568fd-x5mkh   3m   31Mi
```

## Carga ligera

```powershell
kubectl --context kind-meditriage run finops-load --image=busybox:1.37 --restart=Never -n meditriage-finops-test --command -- sleep 3600
kubectl --context kind-meditriage wait --for=condition=Ready pod/finops-load -n meditriage-finops-test --timeout=120s
kubectl --context kind-meditriage exec -n meditriage-finops-test finops-load -- wget -qO- http://meditriage-api:8080/health
kubectl --context kind-meditriage exec -n meditriage-finops-test finops-load -- sh -c 'while true; do for i in 1 2 3 4 5 6 7 8 9 10; do wget -qO /dev/null http://meditriage-api:8080/health || echo ERROR; done; sleep 1; done'
```

El usuario confirmó respuesta `estado ok` de la comprobación inicial. En otra terminal se midió con `kubectl --context kind-meditriage top pods -n meditriage-finops-test -l app=meditriage`.

```text
00:37:16
meditriage-api-66b99568fd-dsggc   15m   30Mi
meditriage-api-66b99568fd-pccc7   13m   30Mi
meditriage-api-66b99568fd-x5mkh   16m   32Mi
00:37:47
meditriage-api-66b99568fd-dsggc   11m   31Mi
meditriage-api-66b99568fd-pccc7   13m   31Mi
meditriage-api-66b99568fd-x5mkh   11m   31Mi
00:38:17
meditriage-api-66b99568fd-dsggc   10m   31Mi
meditriage-api-66b99568fd-pccc7   12m   31Mi
meditriage-api-66b99568fd-x5mkh   11m   31Mi
```

Totales por muestra: reposo 9m/91Mi, 9m/91Mi, 9m/92Mi; carga 44m/92Mi, 35m/93Mi, 33m/93Mi. No se dispone de captura original de esta fase ni conteo de errores.
