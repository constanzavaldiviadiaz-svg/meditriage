#!/usr/bin/env bash
# Prueba la policy require-image-signature en el clúster local (#118).
#
# Necesita el clúster kind con Kyverno instalado y la policy aplicada
# (cluster-local/README.md). Usa --dry-run=server: Kubernetes pasa cada pod por la admisión,
# incluido Kyverno, pero no crea nada.
#
#   bash k8s/policies/probar-policy.sh
set -euo pipefail

CONTEXTO="${CONTEXTO:-kind-meditriage}"
IMAGEN=ghcr.io/constanzavaldiviadiaz-svg/meditriage-api
# Publicada desde main el 27/11 (9ae4623) y firmada por publish-image.yml.
FIRMADA="$IMAGEN@sha256:967ad724ed7b9402f38bbca4705ee4051d8f049f1d6e23f37f7bfa45db22cf77"
# Publicada el 20/11, antes de que el pipeline firmara (#139).
SIN_FIRMA="$IMAGEN@sha256:5bb8eb9ada9cda3fcbd9a4e13cba365b1d494ecc574109c8253e2f23b9c89907"
TERCEROS="python:3.11-slim"

fallas=0

intentar() {  # nombre, imagen, resultado esperado (entra | rechazada), descripción
  local salida
  if salida=$(kubectl --context "$CONTEXTO" run "$1" -n meditriage --image="$2" \
      --dry-run=server -o name 2>&1); then
    resultado=entra
  else
    resultado=rechazada
  fi
  if [ "$resultado" = "$3" ]; then
    echo "   ok: $4 -> $resultado"
  else
    echo "   FALLA: $4 -> $resultado (se esperaba: $3)"
    echo "$salida" | sed 's/^/      /'
    fallas=$((fallas + 1))
  fi
  if [ "$resultado" = rechazada ]; then
    echo "$salida" | grep -o 'Policy require-image-signature failed: [^(]*' | sed 's/^/      /' || true
  fi
}

echo "== Admisión en el namespace meditriage"
intentar prueba-firmada "$FIRMADA" entra "imagen firmada por el pipeline"
intentar prueba-sin-firma "$SIN_FIRMA" rechazada "nuestra imagen, pero sin firma"
intentar prueba-terceros "$TERCEROS" rechazada "imagen de terceros"

if [ "$fallas" -gt 0 ]; then
  echo
  echo "$fallas prueba(s) fallaron."
  exit 1
fi
echo
echo "Todas las pruebas pasaron."
