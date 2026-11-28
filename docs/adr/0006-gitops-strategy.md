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

El repositorio `meditriage-gitops` constituye la única fuente de verdad para los manifiestos de los ambientes administrados por Argo CD.

El directorio `k8s/` del repositorio principal se mantiene exclusivamente como alternativa para desarrollo local, pruebas y despliegues sin Argo CD. No debe utilizarse para modificar directamente recursos administrados por GitOps.

Mientras existan ambas estructuras, cualquier modificación de manifiestos de aplicación en `k8s/` deberá incorporar su cambio equivalente en el repositorio GitOps mediante Pull Requests coordinados.

Esto incluye:

- Configuraciones de seguridad de pods y contenedores.
- NetworkPolicies.
- Sondas de disponibilidad y salud.
- Configuración de recursos y escalado.
- Reglas de Ingress y exposición de endpoints.

Las diferencias intencionales entre ambientes deberán declararse mediante overlays de Kustomize.

Actualmente existe una divergencia en las configuraciones de seguridad y exposición de endpoints entre ambos repositorios. Su corrección deberá coordinarse antes de considerar completa la estrategia GitOps, incluyendo el hardening del Deployment, las restricciones de Ingress y las NetworkPolicies compatibles con PostgreSQL y el worker de auditoría.

El pipeline de integración continua construye y publica las imágenes, pero no aplica directamente los cambios en Kubernetes. Su responsabilidad termina al proponer la actualización del estado deseado mediante un Pull Request en el repositorio GitOps.

**Por qué Pull:**

- El pipeline no necesita credenciales de acceso directo al clúster.
- Los cambios quedan registrados y pueden revisarse antes de desplegarse.
- Se reduce la divergencia entre los manifiestos versionados y los recursos desplegados.
- Permite recuperar una versión anterior mediante cambios declarativos en Git.

### 2. Argo CD como controlador GitOps

Se utiliza **Argo CD** para sincronizar los manifiestos de Kubernetes con el repositorio GitOps.

Argo CD permite consultar visualmente el estado de sincronización, la salud de los recursos y la revisión de Git desplegada.

La aplicación `meditriage-dev` está configurada en el clúster local kind, utilizando el overlay de desarrollo y la rama `main` del repositorio GitOps.

Su definición declarativa se incorpora en:

`argocd/meditriage-dev.yaml`

La configuración establece:

| Parámetro | Valor |
|---|---|
| Revisión objetivo | main |
| Ruta | overlays/dev |
| Namespace de destino | meditriage |
| Sincronización automática | Habilitada |
| Prune | Habilitado |
| SelfHeal | Habilitado |

Prune permite eliminar recursos administrados por la aplicación que hayan sido retirados del estado deseado en Git.

SelfHeal permite corregir automáticamente modificaciones manuales que produzcan divergencias respecto del estado deseado.

La instalación inicial de Argo CD y el registro de su Application constituyen operaciones de bootstrap. Una vez instalado Argo CD y preparado el ambiente, el Application puede registrarse desde el repositorio GitOps mediante:

```bash
kubectl apply -f argocd/meditriage-dev.yaml
```

Los despliegues posteriores de la aplicación no requieren ejecutar nuevamente este comando.

Para permitir la integración futura con Horizontal Pod Autoscaler (HPA), se configura una excepción de reconciliación sobre `/spec/replicas` del Deployment `meditriage-api`, utilizando `ignoreDifferences` y `RespectIgnoreDifferences=true`.

Esta excepción delega el número efectivo de réplicas al mecanismo de escalado y evita que Argo CD revierta sus modificaciones. Mientras HPA no esté integrado, las divergencias manuales sobre ese campo tampoco serán corregidas automáticamente.

La compatibilidad conjunta deberá validarse al integrar los cambios de FinOps (#130).

La definición del Application y sus evidencias se encuentran en el [PR #5 del repositorio GitOps](https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops/pull/5).

La reconciliación automática mediante SelfHeal fue validada localmente el 27/11/2026, modificando una etiqueta del Service y comprobando su restauración automática. El Application recuperó el estado `Synced` y mantuvo el estado `Healthy`.

Prune está habilitado, pero su comportamiento de eliminación automática todavía no ha sido validado funcionalmente.

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

La estructura objetivo del repositorio GitOps es:

```text
meditriage-gitops/
├── argocd/
├── base/
└── overlays/
    ├── dev/
    └── prod/
```

El directorio `argocd/` contiene las definiciones declarativas de las aplicaciones administradas por Argo CD. Su incorporación corresponde al PR #5 del repositorio GitOps.

Los ambientes comparten una base común y declaran sus diferencias mediante overlays.

| Configuración | Desarrollo | Producción |
|---|---|---|
| Réplicas iniciales declaradas | 1 | 3 |
| Variable AMBIENTE | desarrollo | produccion |
| Overlay | overlays/dev | overlays/prod |

La cantidad efectiva de réplicas podrá variar mediante HPA una vez integrada la estrategia de escalado correspondiente a FinOps (#130).

Las imágenes se referencian mediante digest SHA-256, nunca mediante etiquetas mutables como `latest`.

Actualmente, desarrollo dispone de un digest independiente en su overlay. Producción hereda la imagen declarada en la base.

Antes de habilitar la promoción a producción, deberá incorporarse un digest independiente en su overlay para evitar acoplar las versiones de ambos ambientes.

Los ambientes deberán mantener destinos de despliegue independientes. El clúster kind actual corresponde exclusivamente a desarrollo; la infraestructura definitiva de producción todavía no está provisionada.

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

La rama `main` del repositorio principal exige dos aprobaciones, resolución de conversaciones y ejecución satisfactoria de los controles obligatorios configurados.

Las aprobaciones anteriores se invalidan cuando se incorporan nuevos cambios al Pull Request, según las reglas de protección establecidas.

Se evita mantener ramas de desarrollo de larga duración. Los ambientes se diferencian mediante overlays de Kustomize y no mediante ramas permanentes por ambiente.

La misma estrategia de revisión deberá aplicarse al repositorio GitOps, conforme a la política establecida en el punto 7.

### 5. Rolling Update como estrategia de despliegue

Se adopta **Rolling Update**, estrategia predeterminada de los objetos Deployment de Kubernetes.

Las réplicas de la versión anterior se reemplazan progresivamente por réplicas de la nueva versión.

El Deployment de la API utiliza las siguientes sondas:

- `/ready`: determina si una réplica está preparada para recibir tráfico.
- `/health`: permite detectar contenedores que deben reiniciarse.

La configuración actual utiliza los valores predeterminados de Kubernetes:

| Parámetro | Valor |
|---|---|
| Estrategia | RollingUpdate |
| maxSurge | 25 % |
| maxUnavailable | 25 % |

Con tres réplicas declaradas en producción, estos valores permiten crear una réplica adicional y establecen en cero la indisponibilidad permitida por la estrategia de actualización, debido al redondeo aplicado por Kubernetes.

Esto contribuye al objetivo de disponibilidad mensual del 99,5 %, pero no lo garantiza por sí solo. También depende de la capacidad del clúster, el comportamiento de la aplicación, sus dependencias y la observabilidad del servicio.

#### Compatibilidad con PostgreSQL

Durante un Rolling Update pueden coexistir temporalmente dos versiones de la API que utilizan el mismo esquema de PostgreSQL.

Por este motivo, las migraciones de base de datos deberán mantener compatibilidad con ambas versiones mediante una estrategia **expand/contract**:

1. Expandir el esquema incorporando estructuras compatibles con la versión anterior.
2. Desplegar progresivamente la nueva versión de la aplicación.
3. Migrar los datos y verificar el funcionamiento de la nueva versión.
4. Retirar las estructuras obsoletas únicamente cuando ninguna versión activa dependa de ellas y se haya considerado la ventana de rollback.

No deberán ejecutarse cambios destructivos de esquema mientras existan réplicas que dependan de las estructuras anteriores.

#### Compatibilidad con el worker de auditoría

El worker de auditoría deberá soportar la coexistencia temporal de instancias durante las actualizaciones.

La implementación propuesta en el PR #142 contempla el uso de `FOR UPDATE SKIP LOCKED` para coordinar el procesamiento concurrente de registros pendientes en PostgreSQL.

Este mecanismo deberá complementarse con transacciones adecuadas y garantías de idempotencia para evitar el procesamiento duplicado de eventos.

La estrategia objetivo del Deployment del worker permite una réplica adicional durante el Rolling Update (`maxSurge: 1`). Su seguridad operativa deberá validarse mediante pruebas de concurrencia antes de habilitarla en producción.

La integración de PostgreSQL y del worker de auditoría permanece pendiente en el PR #142.

#### Rollback

En caso de una versión defectuosa, se revierte el cambio de digest mediante Git para que Argo CD reconcilie nuevamente el estado deseado.

El rollback de la aplicación no implica automáticamente revertir el esquema de PostgreSQL. La compatibilidad de las migraciones deberá evaluarse antes de recuperar una versión anterior.

No se utiliza `kubectl rollout undo` como mecanismo habitual de rollback, porque modificaría el estado del clúster sin actualizar su fuente de verdad.

### 6. Flujo de promoción de imágenes

Los controles de cadena de suministro se definen en el ADR 0007 — Cadena de suministro: firma de imágenes y SLSA (#114 y #137), actualmente propuesto.

Este ADR establece la coordinación entre dichos controles y el mecanismo de promoción GitOps, sin duplicar sus políticas de seguridad.

El flujo objetivo de entrega continua es:

1. Fusionar un Pull Request aprobado en `main` del repositorio principal.
2. Construir la imagen de contenedor.
3. Ejecutar los controles de seguridad sobre la imagen definitiva y publicarla en GitHub Container Registry (GHCR).
4. Generar el SBOM CycloneDX asociado a la imagen.
5. Firmar y verificar el digest mediante Cosign keyless.
6. Generar y adjuntar la attestation de procedencia de construcción, conforme a SLSA nivel 2.
7. Crear automáticamente un Pull Request en el repositorio GitOps con el nuevo digest del overlay de desarrollo.
8. Revisar y fusionar el Pull Request de promoción.
9. Permitir que Argo CD sincronice el nuevo estado deseado.
10. Verificar la salud de la aplicación y el digest desplegado.

La imagen escaneada deberá corresponder al mismo artefacto inmutable que se publica, firma y promueve. No deberá reconstruirse entre estas etapas.

La promoción solo debe ejecutarse si todos los controles previos finalizan correctamente. El job de promoción deberá declarar su dependencia respecto del job de publicación y sus verificaciones.

La identidad de firma aceptada, los umbrales de vulnerabilidades, las excepciones y las condiciones de verificación se establecen en el ADR 0007.

Adicionalmente, Kyverno deberá verificar en el clúster que la imagen esté referenciada por digest y posea una firma válida de la identidad autorizada.

La verificación de admisión corresponde a la issue #118 y permanece pendiente de integración.

#### Credenciales de promoción

Las credenciales utilizadas para crear Pull Requests entre repositorios se almacenan como un secreto de GitHub Actions denominado `GITOPS_TOKEN`.

Se utiliza un Personal Access Token (PAT) de alcance limitado al repositorio GitOps, con los siguientes permisos requeridos:

- Contents: lectura y escritura.
- Pull requests: lectura y escritura.

El token no deberá disponer de permisos administrativos.

El PAT está asociado a una cuenta personal, por lo que su vencimiento, revocación o pérdida de acceso pueden interrumpir la promoción automática.

Conforme al [inventario y política de rotación de secretos](../security/secretos.md):

| Aspecto | Definición |
|---|---|
| Responsable de rotación | DevSecOps Lead |
| Frecuencia propuesta | Cada 30 días |
| Almacenamiento | GitHub Actions Secrets |
| Fecha de vencimiento efectiva | Pendiente de verificación |
| Próxima rotación | Pendiente de registrar |

El DevSecOps Lead deberá verificar la fecha efectiva de expiración y los permisos del token, registrar la próxima rotación y renovar la credencial antes de su vencimiento.

Como evolución futura, podrá utilizarse una GitHub App con permisos limitados y tokens de instalación temporales para reducir la dependencia de una cuenta personal.

#### Estado de implementación

| Componente | Estado |
|---|---|
| Escaneo de imágenes con Trivy (#92, PR #143) | Integrado |
| Firma, verificación y attestation (PR #139) | Integrado |
| SBOM CycloneDX (#93) | Pendiente |
| Promoción automática a GitOps (PR #113) | Pendiente de integración |
| Admisión mediante Kyverno (#118) | Pendiente |
| Application declarativo de Argo CD (GitOps PR #5) | Implementado y pendiente de integración |
| Validación integral del flujo | Pendiente |

La integración de controles individuales no constituye evidencia de que el flujo completo de promoción y despliegue automático haya sido validado.

### 7. Política de revisión para producción

Se establece como política propuesta un mínimo de **dos aprobaciones independientes del autor** para todos los Pull Requests dirigidos a `main` del repositorio GitOps.

GitHub aplica el número mínimo de aprobaciones mediante reglas de protección de ramas. No permite establecer directamente un número diferente de aprobaciones según la ruta modificada utilizando esta configuración.

Por este motivo, se adopta una regla uniforme para todo el repositorio GitOps, incluyendo cambios de desarrollo, producción y manifiestos compartidos.

Las revisiones de promoción a producción deberán cubrir:

- **Revisión técnica:** compatibilidad, disponibilidad y comportamiento esperado de la nueva versión.
- **Revisión de seguridad:** integridad de la imagen, procedencia y cumplimiento de los controles de seguridad.

La promoción a producción debe utilizar el mismo digest previamente validado en desarrollo, sin reconstruir la imagen.

Se mantiene una aprobación humana antes de modificar el estado deseado de producción. Una vez aprobado y fusionado el cambio, Argo CD realizará el despliegue.

Actualmente, el repositorio GitOps exige Pull Requests hacia `main`, pero no requiere aprobaciones ni controles de estado obligatorios.

Antes de habilitar despliegues a producción, la Product Owner, como administradora del repositorio, deberá configurar un ruleset sobre `main` que contemple:

- Pull Requests obligatorios antes de fusionar.
- Un mínimo de dos aprobaciones.
- Invalidación de aprobaciones anteriores cuando se incorporen nuevos cambios.
- Resolución obligatoria de conversaciones.
- Controles de estado obligatorios, una vez definidos e implementados.
- Restricción de modificaciones directas y bypass no autorizados.

La protección deberá verificarse mediante un Pull Request de prueba antes de habilitar la promoción a producción.

Esta configuración permanece pendiente de implementación.

## Consecuencias

### Positivas

- Los despliegues quedan registrados mediante commits y Pull Requests.
- El pipeline no requiere acceso directo al clúster.
- La separación de repositorios facilita distinguir cambios de código y cambios de despliegue.
- GitOps establece una única fuente de verdad para los ambientes administrados por Argo CD.
- SelfHeal permite corregir divergencias automáticamente.
- Prune permite eliminar recursos retirados del estado deseado.
- Argo CD permite visualizar el estado de sincronización y salud de los recursos.
- Las referencias por digest permiten identificar exactamente la imagen desplegada.
- La integración con el ADR 0007 permite verificar la identidad y procedencia de las imágenes.
- Rolling Update reduce la complejidad operativa frente a estrategias de despliegue avanzadas.
- Las aprobaciones obligatorias reducen el riesgo de desplegar cambios sin revisión.

### Negativas

- Se incorpora Argo CD como componente adicional que debe mantenerse y monitorearse.
- La separación de repositorios requiere gestionar credenciales y permisos entre ellos.
- El PAT de promoción depende de una cuenta personal y requiere rotación.
- La coexistencia de manifiestos locales y GitOps exige coordinar cambios para evitar divergencias.
- Prune puede eliminar recursos administrados cuando se retiran accidentalmente de Git.
- La excepción de reconciliación sobre `spec.replicas` impide que Argo CD corrija divergencias en ese campo.
- La promoción mediante Pull Requests introduce un tiempo de espera asociado a las revisiones, también en desarrollo.
- Rolling Update puede mantener temporalmente dos versiones de la aplicación ejecutándose simultáneamente, lo que exige compatibilidad entre versiones y esquemas de datos.
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

### Mantener dos fuentes de verdad independientes

Permitiría modificar indistintamente los manifiestos del repositorio principal y del repositorio GitOps.

Se descarta porque dificulta determinar el estado deseado, favorece divergencias de seguridad y contradice el principio de reconciliación declarativa.

El repositorio GitOps mantiene la autoridad sobre los despliegues administrados por Argo CD, mientras que los manifiestos locales constituyen una alternativa para ambientes sin dicho controlador.

## Referencias

- [ADR 0005 — Plataforma Kubernetes](0005-plataforma-k8s.md)
- [Inventario y política de rotación de secretos](../security/secretos.md)
- [ADR 0007 — Cadena de suministro, firma de imágenes y SLSA (issue #114)](https://github.com/constanzavaldiviadiaz-svg/meditriage/issues/114)
- [PR #113 — Promoción automática de imágenes](https://github.com/constanzavaldiviadiaz-svg/meditriage/pull/113)
- [PR #139 — Firma y attestation](https://github.com/constanzavaldiviadiaz-svg/meditriage/pull/139)
- [PR #142 — PostgreSQL y auditoría](https://github.com/constanzavaldiviadiaz-svg/meditriage/pull/142)
- [PR #143 — Escaneo de imágenes](https://github.com/constanzavaldiviadiaz-svg/meditriage/pull/143)
- [Repositorio GitOps](https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops)
- [GitOps PR #5 — Application declarativo y reconciliación automática](https://github.com/constanzavaldiviadiaz-svg/meditriage-gitops/pull/5)