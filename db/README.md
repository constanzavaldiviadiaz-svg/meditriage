# Bases de datos

MediTriage usa dos bases PostgreSQL (ADR 0004):

| Base | Qué guarda | Quién entra |
|---|---|---|
| `meditriage` | Identidad (RUT, nombre, consentimiento), clínico y la outbox | La API y el worker, con el rol `meditriage_app` |
| `meditriage_auditoria` | El registro de auditoría, append-only | El worker, con `auditoria_escritor` (solo `INSERT`); el auditor, con `auditoria_lector` (solo `SELECT`) |

La estructura está en [`sql/`](sql/). Los mismos scripts crean las bases de las pruebas
(`tests/conftest.py`), así que lo que se prueba es lo que se despliega.

## Cómo llega un evento a la auditoría

```
API ──(una transacción)──▶ paciente + evento en la outbox     base meditriage
                                   │
                    worker de auditoría (k8s/worker-auditoria.yaml)
                                   │
                                   ▼
                     auditoria.registro, encadenado           base meditriage_auditoria
```

Si la base de auditoría no responde, los eventos esperan en la outbox y el worker los
reintenta. Ninguno se pierde.

## Levantar las bases en local

Como en producción (ADR 0005), PostgreSQL corre **fuera del clúster**: en un contenedor de
Docker aparte, conectado a la red de kind para que los pods lo alcancen por su nombre,
`meditriage-postgres`. Primero levanta el clúster ([cluster-local/](../cluster-local/README.md)).

**1. Genera las claves**, en Git Bash. Viven solo en tu terminal: no se escriben en ningún
archivo del repositorio.

```bash
export CLAVE_MEDITRIAGE_APP=$(openssl rand -hex 16)
export CLAVE_AUDITORIA_ESCRITOR=$(openssl rand -hex 16)
export CLAVE_AUDITORIA_LECTOR=$(openssl rand -hex 16)
```

**2. Arranca PostgreSQL**, desde la raíz del repositorio. La primera vez, el contenedor
ejecuta [`00-crear-bases.sh`](00-crear-bases.sh), que crea las dos bases, los roles y sus
claves. Los datos quedan en el volumen `meditriage-pgdata`: sobreviven aunque borres el
contenedor o el clúster.

```bash
MSYS_NO_PATHCONV=1 docker run -d --name meditriage-postgres --network kind \
  -e POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  -e CLAVE_MEDITRIAGE_APP -e CLAVE_AUDITORIA_ESCRITOR -e CLAVE_AUDITORIA_LECTOR \
  -v meditriage-pgdata:/var/lib/postgresql/data \
  -v "$(pwd -W)/db:/docker-entrypoint-initdb.d:ro" \
  postgres:17@sha256:87c8b42f423b45d5247e6aa8fdb2e7762fec164c68a50fe3eb07e7bfcaf4dbcf
```

`MSYS_NO_PATHCONV=1` y `pwd -W` evitan que Git Bash convierta las rutas al estilo Windows.

No se publica ningún puerto en tu computador: los pods llegan a la base por la red de kind, y
para consultarla a mano se usa `docker exec`, como en "Revisar la auditoría".

**3. Crea los Secrets con Terraform**, con las mismas claves. Es el paso 5 de
[cluster-local/](../cluster-local/README.md):

```bash
export TF_VAR_clave_meditriage_app=$CLAVE_MEDITRIAGE_APP
export TF_VAR_clave_auditoria_escritor=$CLAVE_AUDITORIA_ESCRITOR
terraform -chdir=terraform apply
```

Si todavía no tienes acceso a HCP Terraform, crea el namespace y los mismos Secrets a mano:

```bash
kubectl create namespace meditriage
kubectl -n meditriage create secret generic meditriage-bd \
  --from-literal=BASE_DATOS_URL="postgresql://meditriage_app:$CLAVE_MEDITRIAGE_APP@meditriage-postgres:5432/meditriage"
kubectl -n meditriage create secret generic meditriage-auditoria \
  --from-literal=AUDITORIA_URL="postgresql://auditoria_escritor:$CLAVE_AUDITORIA_ESCRITOR@meditriage-postgres:5432/meditriage_auditoria"
```

## Revisar la auditoría

```bash
# Los registros, en orden
docker exec meditriage-postgres psql -U postgres -d meditriage_auditoria \
  -c "SELECT secuencia, tipo, creado_en, left(hash_integridad, 12) FROM auditoria.registro"

# ¿Alguien alteró la cadena? Devuelve vacío si está intacta, o la secuencia del primer
# registro alterado
docker exec meditriage-postgres psql -U postgres -d meditriage_auditoria \
  -c "SELECT auditoria.verificar_cadena()"

# Intentar modificar un registro: la base lo rechaza
docker exec meditriage-postgres psql -U postgres -d meditriage_auditoria \
  -c "UPDATE auditoria.registro SET tipo = 'otro'"
```

## Si perdiste las claves

Las claves de los roles ya están guardadas en el volumen. Genera otras (paso 1) y
asígnalas:

```bash
docker exec -i meditriage-postgres psql -U postgres \
  -v app="$CLAVE_MEDITRIAGE_APP" -v escritor="$CLAVE_AUDITORIA_ESCRITOR" \
  -v lector="$CLAVE_AUDITORIA_LECTOR" <<'SQL'
ALTER ROLE meditriage_app PASSWORD :'app';
ALTER ROLE auditoria_escritor PASSWORD :'escritor';
ALTER ROLE auditoria_lector PASSWORD :'lector';
SQL
```

Después repite el paso 3 y reinicia los pods: `kubectl -n meditriage rollout restart deployment`.

## Empezar de cero

Borra el contenedor **y el volumen**. Se pierden todos los datos, también la auditoría:

```bash
docker rm -f meditriage-postgres
docker volume rm meditriage-pgdata
```

## En la nube

PostgreSQL será un servicio gestionado (ADR 0003 y 0005). Ahí cambian dos cosas:

- Los scripts de `sql/` los aplica un administrador una vez, no el contenedor.
- La conexión se cifra: Terraform recibe `bd_sslmode = "verify-full"` y la dirección del
  servicio en `bd_host`.
