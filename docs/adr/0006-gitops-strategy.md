# ADR 0006 — Estrategia GitOps y despliegue continuo

## Estado

Propuesto — 26/11/2026.

Pasa a *Aceptado* cuando el equipo apruebe el Pull Request correspondiente.

**Sobre el número:** la sesión 08 denomina a este documento ADR 0005, pero ese número ya corresponde a la plataforma Kubernetes definida en la sesión 07.

## Autores

Matías Sepúlveda (DevSecOps Lead).

## Contexto

El [ADR 0005](0005-plataforma-k8s.md) establece Kubernetes como plataforma de despliegue, kind para desarrollo local, Terraform para la infraestructura y Kustomize para la gestión de manifiestos.

Este ADR define cómo se entregan nuevas versiones de MediTriage, cómo se sincronizan los ambientes y qué controles deben cumplirse antes de desplegar en producción.

Las decisiones consideran las siguientes restricciones:

| Restricción | Implicancia para el despliegue |
|---|---|
| Disponibilidad mensual del 99,5 % | Actualizaciones que minimicen las interrupciones del servicio |
| Latencia inferior a 3 segundos | Mantener capacidad suficiente durante las actualizaciones |
| Tratamiento de datos de salud | Control de acceso, trazabilidad y revisión de cambios |
| Cuatro estudiantes, un semestre | Evitar complejidad operativa innecesaria |
| Proveedor cloud no definido | Mantener una estrategia independiente del proveedor |

## Decisión

### 1. GitOps mediante un modelo Pull

Se adopta GitOps mediante un modelo **Pull**, donde un agente dentro del clúster consulta el estado deseado almacenado en Git y lo reconcilia con el estado real de Kubernetes.

Git constituye la fuente de verdad para los manifiestos de la aplicación.

El pipeline de integración continua construye y publica las imágenes, pero no aplica directamente los cambios en Kubernetes. Su responsabilidad termina al proponer la actualización del estado deseado mediante un Pull Request en el repositorio GitOps.

**Por qué Pull:**

- El pipeline no necesita credenciales de acceso directo al clúster.
- Los cambios quedan registrados y pueden revisarse antes de desplegarse.
- Se reduce la divergencia entre los manifiestos versionados y los recursos desplegados.
- Permite recuperar una versión anterior mediante cambios declarativos en Git.

### 2. Argo CD como controlador GitOps

Se utiliza **Argo CD** para sincronizar los manifiestos de Kubernetes con el repositorio GitOps.

Argo CD permite consultar visualmente el estado de sincronización, la salud de los recursos y la revisión de Git desplegada.

La aplicación `meditriage-dev` está configurada en el clúster local kind, utilizando el overlay de desarrollo y la sincronización automática.

Se mantiene la separación de responsabilidades establecida en el ADR 0005:

- Terraform administra la infraestructura y los recursos que preparan el ambiente.
- Kustomize declara los recursos de la aplicación.
- Argo CD reconcilia los manifiestos de la aplicación con el clúster.
- GitHub Actions ejecuta los controles de integración continua, publica imágenes y propone su promoción.

### 3. Separación de repositorios y ambientes

Se utilizan dos repositorios independientes:

| Repositorio | Responsabilidad |
|---|---|
| `meditriage` | Código fuente, pruebas, documentación y pipelines |
| `meditriage-gitops` | Estado deseado de los despliegues |

El repositorio GitOps utiliza la siguiente estructura:

```
meditriage-gitops/
├── base/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── ingress.yaml
│   ├── kustomization.yaml
│   └── service.yaml
└── overlays/
    ├── dev/
    │   └── kustomization.yaml
    └── prod/
        └── kustomization.yaml
```

Los ambientes comparten una base común y declaran sus diferencias mediante overlays.

| Configuración | Desarrollo | Producción |
|---|---|---|
| Réplicas declaradas | 1 | 3 |
| Variable AMBIENTE | desarrollo | produccion |
| Overlay | overlays/dev | overlays/prod |

Las imágenes se referencian mediante digest SHA-256, nunca mediante etiquetas mutables como `latest`.

Actualmente, desarrollo dispone de un digest independiente en su overlay. Producción hereda la imagen declarada en la base. Antes de habilitar la promoción a producción, deberá incorporarse un digest independiente en su overlay para evitar acoplar las versiones de ambos ambientes.

### 4. GitHub Flow como estrategia de ramas

Se mantiene **GitHub Flow**, utilizando ramas de corta duración asociadas a issues y Pull Requests hacia `main`.

El flujo de trabajo es:

1. Crear una rama desde `main` para resolver una issue.
2. Implementar y verificar los cambios.
3. Abrir un Pull Request.
4. Ejecutar los controles automatizados.
5. Obtener las aprobaciones requeridas.
6. Fusionar los cambios en `main`.
7. Eliminar la rama cuando ya no sea necesaria.

La rama `main` del repositorio principal exige actualmente dos aprobaciones, resolución de conversaciones y ejecución satisfactoria de los controles obligatorios.

Las aprobaciones anteriores se invalidan cuando se incorporan nuevos cambios al Pull Request.

Se evita mantener ramas de desarrollo de larga duración. Los ambientes se diferencian mediante overlays de Kustomize y no mediante ramas permanentes por ambiente.

### 5. Rolling Update como estrategia de despliegue

Se adopta **Rolling Update**, estrategia predeterminada de los objetos Deployment de Kubernetes.

Las réplicas de la versión anterior se reemplazan progresivamente por réplicas de la nueva versión.

El Deployment utiliza las siguientes sondas:

- `/ready`: determina si una réplica está preparada para recibir tráfico.
- `/health`: permite detectar contenedores que deben reiniciarse.

La configuración actual utiliza los valores predeterminados de Kubernetes:

| Parámetro | Valor |
|---|---|
| Estrategia | RollingUpdate |
| maxSurge | 25 % |
| maxUnavailable | 25 % |

Con tres réplicas declaradas en producción, estos valores permiten crear una réplica adicional y establecen en cero la indisponibilidad permitida por la estrategia de actualización.

Esto contribuye al objetivo de disponibilidad mensual del 99,5 %, pero no lo garantiza por sí solo. También depende de la capacidad del clúster, el comportamiento de la aplicación, sus dependencias y la observabilidad del servicio.

En caso de una versión defectuosa, se revierte el cambio de digest mediante Git para que Argo CD reconcilie nuevamente el estado deseado.

No se utiliza `kubectl rollout undo` como mecanismo habitual de rollback, porque modificaría el estado del clúster sin actualizar su fuente de verdad.

### 6. Flujo de promoción de imágenes

El flujo objetivo de entrega continua es:

1. Fusionar un Pull Request aprobado en `main` del repositorio principal.
2. Construir y publicar la imagen en GitHub Container Registry (GHCR).
3. Firmar y verificar la imagen mediante Cosign.
4. Generar la attestation de procedencia de construcción.
5. Crear automáticamente un Pull Request en el repositorio GitOps con el nuevo digest del overlay de desarrollo.
6. Revisar y fusionar el Pull Request de promoción.
7. Permitir que Argo CD sincronice el nuevo estado deseado.
8. Verificar la salud de la aplicación y la versión desplegada.

La promoción solo debe ejecutarse si las etapas anteriores finalizan correctamente.

Las credenciales utilizadas para crear el Pull Request entre repositorios se almacenan como un secreto de GitHub Actions (`GITOPS_TOKEN`), con permisos limitados al repositorio GitOps.

La automatización de promoción corresponde al PR #113 y los controles de firma y attestation al PR #139. Al momento de redactar este ADR, su integración y la validación completa del flujo están pendientes.

### 7. Política de revisión para producción

Se establece como política propuesta un mínimo de **dos aprobaciones independientes del autor** para cualquier Pull Request que modifique el estado deseado de producción.

Las revisiones deben cubrir:

- **Revisión técnica:** compatibilidad, disponibilidad y comportamiento esperado de la nueva versión.
- **Revisión de seguridad:** integridad de la imagen, procedencia y cumplimiento de los controles de seguridad.

La promoción a producción debe utilizar el mismo digest previamente validado en desarrollo, sin reconstruir la imagen.

Se mantiene una aprobación humana antes de modificar el estado deseado de producción. Una vez aprobado y fusionado el cambio, Argo CD realiza el despliegue.

Actualmente, el repositorio GitOps exige Pull Requests hacia `main`, pero no requiere aprobaciones ni controles de estado obligatorios.

Antes de habilitar despliegues a producción, deberá configurarse una protección efectiva que impida fusionar cambios de producción sin las dos aprobaciones requeridas y los controles correspondientes. El mecanismo concreto de aplicación deberá ser validado por el equipo.

## Consecuencias

### Positivas

- Los despliegues quedan registrados mediante commits y Pull Requests.
- El pipeline no requiere acceso directo al clúster.
- La separación de repositorios facilita distinguir cambios de código y cambios de despliegue.
- Argo CD permite visualizar el estado de sincronización y salud de los recursos.
- Las referencias por digest permiten identificar exactamente la imagen desplegada.
- Rolling Update reduce la complejidad operativa frente a estrategias de despliegue avanzadas.
- Las aprobaciones de producción reducen el riesgo de desplegar cambios sin revisión.

### Negativas

- Se incorpora Argo CD como componente adicional que debe mantenerse y monitorearse.
- La separación de repositorios requiere gestionar credenciales y permisos entre ellos.
- La promoción mediante Pull Requests introduce un tiempo de espera asociado a las revisiones.
- Rolling Update puede mantener temporalmente dos versiones de la aplicación ejecutándose simultáneamente, lo que exige compatibilidad entre versiones.
- No se dispone de distribución gradual de tráfico ni análisis automatizado de métricas como en un despliegue canary.
- Mientras la aplicación almacene datos en memoria, el reemplazo de réplicas puede perder datos locales. Esta limitación deberá resolverse mediante la persistencia externa definida en los ADR anteriores.
- La protección efectiva de producción y la validación integral del flujo todavía están pendientes.

## Alternativas descartadas

### Despliegue Push desde el pipeline

El pipeline ejecutaría directamente comandos como `kubectl apply` para actualizar Kubernetes.

Se descarta porque requiere entregar credenciales del clúster al sistema de integración continua y no proporciona por sí solo reconciliación continua del estado deseado.

### Flux

Flux es una alternativa válida para implementar GitOps mediante Pull y reconciliación declarativa.

Se elige Argo CD por su interfaz visual integrada, facilidad para inspeccionar la salud de las aplicaciones y utilidad para demostrar los despliegues durante la defensa del proyecto.

No se descarta Flux por limitaciones de seguridad o capacidad, sino por adecuación al contexto y experiencia actual del equipo.

### Trunk-based Development

El desarrollo basado en trunk favorece integraciones frecuentes mediante cambios pequeños y ramas de vida muy corta.

Se mantiene GitHub Flow porque el equipo ya organiza su trabajo mediante issues, ramas y Pull Requests sujetos a revisión.

Ambas estrategias pueden incorporar integración frecuente. No se adopta un cambio formal de flujo porque no aporta una ventaja suficiente para justificar modificar la organización actual del equipo.

### GitFlow

Utiliza ramas permanentes de desarrollo y ramas adicionales para releases y hotfixes.

Se descarta por introducir complejidad innecesaria para un equipo de cuatro integrantes y una aplicación con dos ambientes gestionados mediante Kustomize.

### Blue/Green

Mantiene dos versiones completas de la aplicación y conmuta el tráfico entre ellas.

Permite cambios rápidos de versión, pero requiere capacidad adicional y mecanismos de conmutación. Se descarta por su costo operativo frente a las necesidades actuales del proyecto.

### Canary

Introduce progresivamente una nueva versión para una parte del tráfico, evaluando su comportamiento antes de ampliar el despliegue.

Es una alternativa atractiva para reducir el impacto de versiones defectuosas, pero requiere mecanismos adicionales de distribución de tráfico, observabilidad y criterios de promoción.

Se mantiene como evolución futura mediante Argo Rollouts, sin convertirlo en un requisito de la estrategia inicial.

### Una sola aprobación para producción

Reduce el tiempo de revisión, pero concentra la responsabilidad en una sola persona.

Se descarta en favor de dos aprobaciones independientes, considerando la sensibilidad de los datos tratados por MediTriage y la necesidad de revisar tanto los aspectos técnicos como los de seguridad.
