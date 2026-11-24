#!/usr/bin/env bash
# Prueba cada regla de .semgrep/ contra sus casos en tests/semgrep/.
#
# Las pruebas viven aquí y no junto a las reglas porque Semgrep no busca casos de prueba
# dentro de carpetas ocultas como .semgrep/. Por la misma razón, y porque "semgrep --test"
# acepta una sola configuración, las reglas se prueban de a una.
#
# Uso, desde la raíz del repositorio:   bash tests/semgrep/probar-reglas.sh
set -euo pipefail

for regla in .semgrep/*.yaml; do
  nombre=$(basename "$regla" .yaml)
  echo "== $nombre"
  semgrep --test --metrics=off --config "$regla" "tests/semgrep/$nombre.py"
done
