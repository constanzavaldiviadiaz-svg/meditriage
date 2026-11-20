# ADR 0005 — Plataforma de despliegue: Kubernetes e infraestructura como código

## Estado

Propuesto — 22/10/2026

Pasa a *Aceptado* cuando el equipo apruebe el Pull Request correspondiente.

**Sobre el número:** la sesión 07 llama a este documento "ADR 0004", pero ese número ya
corresponde a [datos y eventos](0004-datos-y-eventos.md).

## Autores

Fernando Ureta (Tech Lead · AI/Data Lead).

## Contexto

Hasta ahora la arquitectura dijo **qué** se despliega, pero no **dónde ni cómo**:

- El [ADR 0002](0002-estilo-arquitectonico.md) eligió un **monolito modular**.
- El [ADR 0003](0003-cloud-style.md) delegó la base de datos, la cola y la auditoría en
  **servicios gestionados**, y decidió que la aplicación web, la única pieza que diferencia al
  producto, **se construye y se opera como contenedor**. Dejó **el proveedor cloud sin
  elegir**, a propósito.
- El [ADR 0004](0004-datos-y-eventos.md) fijó PostgreSQL y Redis como motores.

La sesión 07 plantea desplegar en Kubernetes y describir la infraestructura como código. Este
ADR evalúa si eso calza con MediTriage y decide las piezas concretas.

Las restricciones que filtran la decisión:

| Restricción | Qué le exige a la plataforma |
|---|---|
| Disponibilidad de 99,5% mensual | Más de una réplica, y reemplazo automático de la que falle |
| Latencia menor a 3 segundos | Agregar réplicas cuando sube la carga, sin intervención manual |
| Datos de salud (Ley 19.628 y 21.719) | Secretos cifrados, imágenes sin herramientas sobrantes |
| Proveedor cloud no elegido (ADR 0003) | Que la decisión no amarre a un proveedor |
| Cuatro estudiantes, un semestre | Que el equipo pueda operar lo que elige |

## Decisión

### 1. Kubernetes gestionado como plataforma de producción

La aplicación se despliega en **Kubernetes**, en el servicio gestionado del proveedor que se
elija (EKS en AWS, AKS en Azure o GKE en Google Cloud). "Gestionado" sigue la política del
ADR 0003: el proveedor opera el plano de control del clúster; el equipo solo declara qué
quiere correr.

**Por qué Kubernetes:**

1. **No amarra a un proveedor.** Los tres grandes ofrecen Kubernetes gestionado, y los mismos
   manifiestos sirven en cualquiera. Es lo que permite mantener abierta la elección de
   proveedor que dejó el ADR 0003.
2. **Resuelve la disponibilidad sin código propio.** Si una réplica deja de responder a su
   sonda `/health`, Kubernetes la reemplaza sola. Si no está lista (`/ready`), no le envía
   pacientes.
3. **Escala solo.** El HPA agrega réplicas cuando sube la carga, que es lo que protege el
   presupuesto de 3 segundos en hora punta.
4. **Habilita GitOps**, la forma de desplegar que define la sesión 08.

**Qué corre dentro del clúster y qué no:**

| Pieza | Dónde |
|---|---|
| Aplicación web | **Dentro del clúster**, como Deployment |
| Worker de eventos (ADR 0004) | Dentro del clúster, cuando exista su código |
| PostgreSQL, Redis, almacén de auditoría | **Fuera del clúster**, como servicios gestionados (ADR 0003 y 0004) |

El clúster solo corre lo que no guarda estado. Los datos viven en servicios donde el
proveedor responde por los respaldos y la replicación. Así, perder el clúster completo no
pierde ningún dato.

### 2. kind para desarrollo y pruebas

Cada integrante levanta un clúster local con **kind** (*Kubernetes in Docker*).

- **Corre sobre Docker**, que el equipo ya usa para construir la imagen. No requiere máquinas
  virtuales.
- **Es Kubernetes estándar**, sin modificaciones: lo que funciona en kind funciona en un
  clúster gestionado.
- **Corre también dentro de GitHub Actions**, así que el pipeline de la sesión 08 puede probar
  los manifiestos contra el mismo tipo de clúster que se usa en local.

### 3. Terraform para la infraestructura

La infraestructura se describe en **Terraform**.

- **Funciona con todos los proveedores**, coherente con no haber elegido uno.
- **Es declarativo**: el archivo describe el resultado, no los pasos. Se lee y se revisa en un
  Pull Request sin saber programar, lo que importa en un equipo donde no todos programan.
- **Es la herramienta con más documentación y ejemplos**, y la que usa el material del ramo.

**Reglas del state** (el archivo donde Terraform anota qué creó):

- **Backend remoto con bloqueo**: dos personas no pueden aplicar cambios al mismo tiempo. Se
  usa HCP Terraform en su plan gratuito.
- **Un state por ambiente** (desarrollo, producción), como indica la sesión.
- **El state nunca se sube al repositorio**: puede contener secretos.

### 4. La frontera entre Terraform y los manifiestos

Dos herramientas declaran cosas en el mismo clúster. Para que no se pisen, cada una tiene su
territorio:

| Terraform declara | Los manifiestos (Kustomize) declaran |
|---|---|
| Lo que cambia poco y prepara el terreno | Lo que cambia en cada versión de la aplicación |
| El namespace `meditriage`, los Secrets y, en la nube, el clúster y los servicios gestionados | Deployment, Service, Ingress, ConfigMap, HPA |

**Regla:** un objeto lo declara una sola herramienta. Por ejemplo, el namespace lo crea
Terraform, así que los manifiestos lo usan pero no lo crean.

### 5. Kustomize para los manifiestos

Los manifiestos se organizan con **Kustomize**.

- **Son archivos YAML normales**, sin un lenguaje de plantillas encima. Cualquiera del equipo
  puede leerlos y editarlos, también desde el editor web de GitHub.
- **Viene incluido en `kubectl`** (`kubectl apply -k`), sin instalar nada más.
- **Resuelve justo lo que necesitamos**: una base común y pequeñas diferencias por ambiente
  (*overlays*), que es la estructura que pide el repositorio GitOps de la sesión 08.

**Helm** se usa solo para **instalar componentes de terceros** que se distribuyen así, como
Argo CD o metrics-server. No para nuestra aplicación.

### 6. El Ingress

Se usa el objeto estándar **Ingress** de Kubernetes. El controlador que lo implementa depende
del ambiente:

- **En la nube**, el del proveedor elegido.
- **En kind**, **Traefik**. No se usa ingress-nginx, el más común en los tutoriales: la
  comunidad de Kubernetes anunció su retiro en noviembre de 2025 y, desde marzo de 2026, no
  recibe correcciones de seguridad. Para un sistema con datos de salud, eso lo descarta.

El sucesor recomendado de Ingress es **Gateway API**. Hoy se usa Ingress porque es el estándar
que pide la sesión y lo soportan todos los proveedores; migrar a Gateway API es una revisión
futura de este ADR.

### 7. La imagen

Ya implementada en el Dockerfile (#68), y se registra aquí por ser parte de la plataforma:

- **Base distroless**: sin shell ni gestor de paquetes. Menos superficie de ataque y menos
  vulnerabilidades heredadas.
- **Usuario no root.**
- **Imágenes base fijadas por digest**, y la nuestra referenciada por digest en los
  manifiestos, nunca por `:latest`.

## Consecuencias

### Positivas

- **El proveedor cloud sigue abierto.** Kubernetes, Terraform y Kustomize funcionan igual en
  los tres.
- **La disponibilidad y el escalamiento no requieren código propio**: los resuelven las sondas
  y el HPA.
- **Los datos no dependen del clúster.** Viven en servicios gestionados.
- **Todo queda versionado y revisable en Pull Requests**: la imagen, los manifiestos y la
  infraestructura.
- **El mismo tipo de clúster en local y en el pipeline**, gracias a kind.

### Negativas

- **Kubernetes es complejo para un monolito.** Para una sola aplicación, un servicio de
  contenedores más simple bastaría. Se acepta el costo por la portabilidad, y se reduce
  usando el plano de control gestionado.
- **Tres herramientas que aprender**: Kubernetes, Terraform y Kustomize. Se mitiga dividiendo
  el trabajo por rol y documentando cada pieza en el repositorio.
- **Los Secrets de Kubernetes no están cifrados por defecto**, solo codificados. En la nube se
  exige el cifrado en reposo que ofrecen los servicios gestionados, y la gestión de secretos se
  revisa en la sesión 09.
- **Transitorio: varias réplicas sin base de datos.** Mientras la aplicación guarde los
  pacientes en memoria (#67), cada réplica tiene sus propios datos, y la idempotencia y la
  detección de duplicados solo funcionan dentro de una misma réplica. Se resuelve al conectar
  PostgreSQL. Hasta entonces, las pruebas de escalamiento miden carga, no consistencia.
- **El HPA escala por CPU, no por latencia.** Escalar por latencia requiere métricas propias,
  que llegan con la observabilidad de la sesión 11.

## Alternativas descartadas

### Un servicio de contenedores sin Kubernetes

Como Cloud Run, Azure Container Apps o ECS Fargate. Es **la alternativa más fuerte**: más
simple de operar, y suficiente para un monolito. Se descarta porque **cada uno existe en un
solo proveedor**: elegirlo es elegir proveedor, lo que el ADR 0003 dejó abierto a propósito.
Si el equipo eligiera proveedor y no necesitara portabilidad, habría que revisar este ADR.

### Operar Kubernetes nosotros

Instalar y mantener el plano de control en máquinas propias. Contradice el ADR 0003: es
infraestructura que no diferencia al producto.

### Correr PostgreSQL y Redis dentro del clúster

Posible, pero obliga al equipo a responder por respaldos, replicación y recuperación de
datos de salud. Contradice el ADR 0003 y el 0004.

### minikube y k3d para desarrollo

- **minikube** suele levantar una máquina virtual: más pesado y más lento de arrancar que kind.
- **k3d** corre **k3s**, una distribución de Kubernetes simplificada que reemplaza algunos
  componentes del estándar. Lo que funciona en k3s no siempre funciona igual en un clúster
  gestionado.

### Pulumi

Infraestructura en un lenguaje de programación real, incluido Python, el que usa el equipo.
Es la alternativa más atractiva frente a Terraform. Se descarta porque **mezcla la
infraestructura con lógica de programa**: un Pull Request de infraestructura pasa a requerir
saber programar para revisarlo. Además tiene menos ejemplos y documentación.

### CloudFormation

Funciona **solo en AWS**. Elegirlo es elegir proveedor.

### Helm para la aplicación

Las plantillas de Helm sirven para distribuir un mismo paquete a muchos usuarios con
configuraciones muy distintas. MediTriage es una aplicación con dos ambientes: Kustomize lo
resuelve con YAML normal, sin aprender un lenguaje de plantillas.
