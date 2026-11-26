#!/bin/bash
# Crea las dos bases de MediTriage en el contenedor local de PostgreSQL.
#
# Lo ejecuta la imagen oficial de postgres, que corre los scripts de
# /docker-entrypoint-initdb.d la primera vez que arranca, cuando el volumen de datos está
# vacío. Las instrucciones están en db/README.md.
#
# Las claves de los roles llegan como variables de entorno del contenedor: no se escriben en
# ningún archivo del repositorio.
set -euo pipefail

: "${CLAVE_MEDITRIAGE_APP:?falta la variable CLAVE_MEDITRIAGE_APP}"
: "${CLAVE_AUDITORIA_ESCRITOR:?falta la variable CLAVE_AUDITORIA_ESCRITOR}"
: "${CLAVE_AUDITORIA_LECTOR:?falta la variable CLAVE_AUDITORIA_LECTOR}"

SQL=/docker-entrypoint-initdb.d/sql
psql=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER")

"${psql[@]}" --dbname postgres \
  -c "CREATE DATABASE meditriage" \
  -c "CREATE DATABASE meditriage_auditoria"

"${psql[@]}" --dbname meditriage -f "$SQL/meditriage.sql"
"${psql[@]}" --dbname meditriage_auditoria -f "$SQL/auditoria.sql"

"${psql[@]}" --dbname postgres \
  -v app="$CLAVE_MEDITRIAGE_APP" \
  -v escritor="$CLAVE_AUDITORIA_ESCRITOR" \
  -v lector="$CLAVE_AUDITORIA_LECTOR" <<'SQL'
ALTER ROLE meditriage_app PASSWORD :'app';
ALTER ROLE auditoria_escritor PASSWORD :'escritor';
ALTER ROLE auditoria_lector PASSWORD :'lector';
SQL
