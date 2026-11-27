# Clúster local de MediTriage

Cómo levantar en tu computador el mismo clúster de Kubernetes que usa el equipo (ADR 0005).

## Qué necesitas

| Herramienta | Para qué | Instalación en Windows |
|---|---|---|
| Docker Desktop | Corre el clúster | https://www.docker.com/products/docker-desktop |
| kind | Crea el clúster dentro de Docker | `winget install Kubernetes.kind` |
| kubectl | Da órdenes al clúster | Viene con Docker Desktop |
| Helm | Instala Traefik y metrics-server | `winget install Helm.Helm` |
| Terraform 1.17 o superior | Crea el namespace y los Secrets | `winget install Hashicorp.Terraform` |

Después de instalar con `winget`, cierra y vuelve a abrir la terminal.

## Levantar el clúster

Desde la raíz del repositorio, con Docker Desktop encendido:

```bash
# 1. Crear el clúster
kind create cluster --config cluster-local/kind.yaml

# 2. Instalar Traefik, el controlador de Ingress
helm repo add traefik https://traefik.github.io/charts
helm install traefik traefik/traefik --namespace traefik --create-namespace \
  --values cluster-local/traefik.yaml --wait

# 3. Instalar metrics-server, que necesita el HPA para medir la CPU
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm install metrics-server metrics-server/metrics-server --namespace kube-system \
  --values cluster-local/metrics-server.yaml --wait

# 4. Crear el namespace y el Secret de ejemplo con Terraform
terraform -chdir=terraform init
terraform -chdir=terraform apply
```

**Sobre el paso 4:** según el ADR 0005, el namespace y los Secrets los crea Terraform; los
manifiestos de `k8s/` no los declaran. `apply` muestra lo que va a crear y pide confirmar
escribiendo `yes`.

El estado de Terraform se guarda en HCP Terraform, así que la primera vez necesitas:

1. Que Matías Sepúlveda te invite a la organización `meditriage-dev-byretro`.
2. Correr `terraform login`, que abre el navegador para generar tu token.

Si todavía no tienes ese acceso, crea el namespace a mano para seguir trabajando:
`kubectl create namespace meditriage`.

## Desplegar MediTriage

```bash
kubectl apply -k k8s/
kubectl -n meditriage rollout status deployment/meditriage-api
```

## Comprobar que funciona

```bash
kubectl get all -n meditriage        # los pods deben estar en Running
curl http://localhost:8088/health    # entra por Traefik, el Ingress
kubectl top pods -n meditriage       # consumo de CPU y memoria (metrics-server)
```

## Cómo llega una solicitud a la aplicación

```
Tu computador          kind (Docker)                       namespace meditriage
localhost:8088  ──▶  puerto 30080 del nodo  ──▶  Traefik  ──▶  Service  ──▶  pods de la app
                     (kind.yaml)                 (Ingress)     (reparte entre las réplicas)
```

## Borrar el clúster

```bash
kind delete cluster --name meditriage
```

Se borra todo, incluidos los pacientes de prueba: mientras la app no tenga base de datos, los
guarda en memoria.
