#!/usr/bin/env bash
# Prueba las reglas propias de Falco en el clúster local (#118).
#
# Necesita el clúster kind con Falco instalado (cluster-local/README.md). El caso legítimo de
# PostgreSQL solo prueba algo si la base está corriendo en la red de kind: sin ella, la
# conexión falla, no hay nada que alertar y el caso pasa igual.
#
# Primero hace cosas legítimas, que no deben alertar. Después hace disparar cada regla. Al
# final borra el pod de prueba.
#
#   bash falco/probar-reglas.sh
set -euo pipefail

CONTEXTO="${CONTEXTO:-kind-meditriage}"
DIR="$(cd "$(dirname "$0")" && pwd)"
POD=falco-prueba

k() { kubectl --context "$CONTEXTO" "$@"; }

# Ejecuta un comando dentro del pod. El resultado del comando no importa: lo que se prueba
# es si Falco alerta.
ejecutar() { k exec -n meditriage "$POD" -c api -- "$@" >/dev/null 2>&1 || true; }

conectar() {
  ejecutar python3 -c "import socket; socket.create_connection(('$1', $2), 3).close()"
}

# Alertas de Falco sobre el pod de prueba desde un instante dado.
alertas_desde() {
  sleep 5  # Falco escribe la alerta apenas la ve, pero el log tarda un poco en llegar.
  k logs -n falco ds/falco -c falco --since-time="$1" | grep "pod=$POD" || true
}

ahora() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Al salir, el pod se borra sin esperar. Si quedó uno de una corrida anterior, se espera a
# que termine: si no, la prueba toma ese pod a medio borrar y muere en la mitad.
k delete -f "$DIR/pod-de-prueba.yaml" --ignore-not-found --wait=true >/dev/null 2>&1 || true
k apply -f "$DIR/pod-de-prueba.yaml" >/dev/null
trap 'k delete -f "$DIR/pod-de-prueba.yaml" --wait=false >/dev/null 2>&1 || true' EXIT
k wait -n meditriage --for=condition=Ready "pod/$POD" --timeout=180s >/dev/null
sleep 3

fallas=0

echo "== Casos legítimos: no deben alertar"
desde=$(ahora)
ejecutar python3 -c "print('hola')"
conectar meditriage-postgres 5432
conectar api.anthropic.com 443
legitimas=$(alertas_desde "$desde")
if [ -z "$legitimas" ]; then
  echo "   ok: python3, PostgreSQL y el servicio de IA no generan alertas"
else
  echo "   FALLA: hubo alertas en casos legítimos:"
  echo "$legitimas"
  fallas=$((fallas + 1))
fi

echo "== Casos de ataque: cada uno debe alertar"
desde=$(ahora)
ejecutar sh -c true                    # un shell
ejecutar id                            # un programa que no es python3
conectar kubernetes.default.svc 443    # un destino no autorizado: la API de Kubernetes
ataques=$(alertas_desde "$desde")

esperar() {
  if grep -q "$1" <<<"$ataques"; then
    echo "   ok: $2"
  else
    echo "   FALLA: no alertó: $2"
    fallas=$((fallas + 1))
  fi
}
esperar "Shell en un contenedor de MediTriage" "regla 1, shell (sh)"
esperar "Proceso inesperado en un contenedor de MediTriage" "regla 2, proceso inesperado (id)"
esperar "Conexion saliente no autorizada desde MediTriage" "regla 3, conexión a la API de Kubernetes"

echo
echo "== Alertas generadas"
echo "$ataques"

if [ "$fallas" -gt 0 ]; then
  echo
  echo "$fallas prueba(s) fallaron."
  exit 1
fi
echo
echo "Todas las pruebas pasaron."
