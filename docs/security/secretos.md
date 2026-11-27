
# Inventario y política de rotación de secretos

## 1. Propósito

Este documento establece el inventario de secretos y credenciales
de MediTriage, sus mecanismos de almacenamiento, responsables,
frecuencias de rotación y procedimientos de respuesta ante
filtraciones.

- Responsable principal: Matías Sepúlveda (DevSecOps Lead).
- Issue asociada: #126.
- Fecha: 26 de noviembre de 2026.
- Estado de la política: propuesta para revisión del equipo.

## 2. Principios de gestión

- Ningún secreto real debe almacenarse en el repositorio.
- Los secretos deben tener un responsable identificado.
- Se aplica el principio de mínimo privilegio.
- Las credenciales de desarrollo y producción deben ser independientes.
- Terraform es responsable de crear los Secrets de Kubernetes,
  según lo establecido en el ADR 0005.
- Los valores sensibles deben almacenarse fuera del código fuente.
- El estado de Terraform debe permanecer fuera del repositorio.
- No se deben imprimir secretos en logs, pipelines ni evidencias.
- Toda credencial comprometida debe revocarse inmediatamente.
- En producción se exige cifrado en tránsito y en reposo.

## 3. Inventario de secretos

Los nombres de variables correspondientes a servicios pendientes
son referenciales y deberán ajustarse durante su implementación.

| Secreto | Almacenamiento | Quién lo crea | Responsable de rotación | Frecuencia propuesta | Estado |
|---|---|---|---|---|---|
| GITOPS_TOKEN | GitHub Actions Secrets | DevSecOps Lead, mediante PAT de alcance limitado | DevSecOps Lead | 30 días | Existencia confirmada |
| GITHUB_TOKEN | GitHub Actions, generado durante la ejecución | GitHub Actions | GitHub Actions | Automática por job | Automático |
| Token HCP Terraform | Almacén local de credenciales de Terraform o mecanismo seguro de CI | Titular autorizado en HCP | DevSecOps Lead y titular del token | 90 días | Integración HCP configurada; token no verificado |
| Credenciales Kubernetes | Archivo local ~/.kube/config | Administrador del clúster | DevSecOps Lead | 90 días en producción, según mecanismo de autenticación | Mecanismo configurado |
| AI_API_KEY | Variable sensitive de HCP y Secret de Kubernetes | Administrador autorizado del servicio de IA | DevSecOps Lead | 90 días | Planificado |
| Rol `meditriage_app` (`BASE_DATOS_URL`) | Variable sensitive de HCP (`TF_VAR_clave_meditriage_app`) y Secret `meditriage-bd` | Terraform (`terraform/bd.tf`) | DevSecOps Lead | 90 días | Implementado (#142). Lo usan la API y el worker |
| REDIS_PASSWORD | Variable sensitive de HCP y Secret de Kubernetes | Administrador de Redis | DevSecOps Lead | 90 días | Planificado |
| Rol `auditoria_escritor` (`AUDITORIA_URL`), solo `INSERT` | Variable sensitive de HCP (`TF_VAR_clave_auditoria_escritor`) y Secret `meditriage-auditoria` | Terraform (`terraform/bd.tf`) | DevSecOps Lead | 90 días | Implementado (#142). Solo el worker de auditoría |
| Rol `auditoria_lector` (`AUDITORIA_LECTURA_URL`), solo `SELECT` | Variable sensitive de HCP (`TF_VAR_clave_auditoria_lector`) y Secret `meditriage-auditoria-lectura` | Terraform (`terraform/bd.tf`) | DevSecOps Lead | 90 días | Implementado (#122). Solo la API, para consultar decisiones |
| Administrador de PostgreSQL | Fuera del clúster: solo se usa al crear las bases (`db/README.md`) | Quien administra la base | DevSecOps Lead | 90 días | Implementado; no entra al clúster |
| Tokens OAuth2 | Proveedor de identidad y cliente autorizado | Proveedor de identidad | Proveedor de identidad, supervisado por DevSecOps Lead | Según expiración y política de sesión | Diseñado; validación pendiente |
| DEMO_API_KEY | Secret meditriage-example-secret de Kubernetes | Terraform | DevSecOps Lead | No aplica | Confirmado; valor ficticio |

Los intervalos anteriores constituyen una política propuesta.
No representan rotaciones automáticas actualmente implementadas.

## 4. Alcance y permisos

### 4.1. GITOPS_TOKEN

Permite automatizar la promoción de imágenes mediante Pull Requests
en el repositorio GitOps.

Debe limitarse al repositorio de destino y a los permisos
estrictamente necesarios:

- Contents: lectura y escritura.
- Pull requests: lectura y escritura.

No debe disponer de permisos administrativos ni utilizarse
para acceder a otros repositorios.

### 4.2. GITHUB_TOKEN

GitHub Actions genera automáticamente este token temporal.

Los workflows deben utilizar permisos mínimos:

- contents: read para lectura del repositorio.
- packages: write únicamente cuando sea necesario publicar
  imágenes en GHCR.

No requiere rotación manual ni almacenamiento de un valor
permanente en GitHub Secrets.

### 4.3. HCP Terraform

La configuración actual utiliza:

- Organización: meditriage-dev-byretro.
- Workspace: meditriage-dev.
- Backend remoto mediante HCP Terraform.

Las credenciales de acceso deben mantenerse fuera del repositorio.

Las variables que contengan credenciales reales deberán marcarse
como sensitive y gestionarse mediante los mecanismos seguros
de HCP Terraform.

El atributo sensitive evita determinadas exposiciones en la
salida de Terraform, pero no garantiza que el valor quede
excluido del state.

El acceso al state debe restringirse a personal autorizado.

### 4.4. Kubernetes

Terraform utiliza el contexto kind-meditriage mediante
el archivo local ~/.kube/config.

Los Secrets de Kubernetes deben:

- Mantenerse separados por ambiente.
- Ser accesibles únicamente por las identidades autorizadas.
- Ser consumidos únicamente por los componentes que los necesiten.
- Contar con cifrado en reposo en producción.
- Evitar su exposición mediante logs o manifiestos versionados.

La codificación Base64 de Kubernetes no constituye cifrado.

El clúster local contiene actualmente un Secret de demostración.
No se ha validado el cifrado en reposo del clúster local.

### 4.5. Servicios de datos y auditoría

Las credenciales de PostgreSQL, Redis y auditoría deben ser
independientes y aplicar el principio de mínimo privilegio.

La credencial del worker de auditoría debe contar únicamente
con los permisos de INSERT necesarios para registrar eventos,
según el modelo de amenazas y el ADR 0004.

No debe reutilizarse la credencial administrativa de la base
de datos dentro de la aplicación.

### 4.6. Servicio de IA

La API key del servicio de IA debe almacenarse fuera del
repositorio y mantenerse separada por ambiente.

Su utilización debe limitarse al servicio autorizado.
No debe enviarse al frontend ni registrarse en logs.

La implementación definitiva depende del proveedor de IA
seleccionado por el equipo.

### 4.7. OAuth2

Los tokens de acceso deben tener una duración limitada
y utilizar los scopes definidos en el contrato OpenAPI.

La aplicación deberá validar la autenticidad, expiración
y permisos de cada token.

Las sesiones comprometidas deberán invalidarse mediante
los mecanismos disponibles en el proveedor de identidad.

La implementación de estos controles depende de la issue #103.

## 5. Procedimiento de rotación programada

El DevSecOps Lead mantiene la responsabilidad de coordinar
las rotaciones de credenciales.

1. Identificar el secreto próximo a vencer.
2. Generar una credencial nueva con permisos mínimos.
3. Actualizar el almacén seguro correspondiente.
4. Actualizar o reiniciar los componentes consumidores,
   cuando corresponda.
5. Verificar la conectividad y funcionamiento del servicio.
6. Revocar la credencial anterior.
7. Registrar la fecha, responsable y próxima rotación.

Cuando el proveedor permita mantener dos credenciales activas
temporalmente, se utilizará este mecanismo para minimizar
interrupciones durante la rotación.

El registro de rotación nunca debe incluir el valor del secreto.

## 6. Procedimiento ante filtraciones

### 6.1. Respuesta general

Ante una exposición confirmada o sospecha fundada:

1. Notificar inmediatamente al DevSecOps Lead y al Product Owner.
2. Identificar la credencial comprometida y su alcance.
3. Revocar o deshabilitar la credencial comprometida.
4. Generar una credencial nueva con permisos mínimos.
5. Actualizar los almacenes seguros y componentes afectados.
6. Revisar logs de acceso y determinar posibles usos indebidos.
7. Verificar la recuperación de los servicios afectados.
8. Documentar el incidente sin incluir valores sensibles.
9. Ejecutar nuevamente los controles de seguridad.

La eliminación de una credencial del último commit no elimina
su exposición en el historial de Git.

Si existe una filtración en el repositorio, se debe revocar
primero la credencial y coordinar posteriormente la limpieza
del historial con los administradores del repositorio.

### 6.2. Acciones específicas

| Secreto comprometido | Acción inmediata | Verificación posterior |
|---|---|---|
| GITOPS_TOKEN | Revocar PAT y reemplazar GitHub Secret | Revisar commits, PRs y cambios en GitOps |
| GITHUB_TOKEN | Cancelar ejecución afectada y restringir permisos | Revisar workflows, paquetes e imágenes publicadas |
| Token HCP Terraform | Revocar token y emitir uno nuevo | Revisar accesos, ejecuciones y cambios del state |
| Credenciales Kubernetes | Invalidar credencial o retirar autorización; regenerar acceso | Revisar recursos modificados y accesos al clúster |
| AI_API_KEY | Revocar y reemplazar clave en el proveedor | Revisar consumo, solicitudes y accesos |
| PostgreSQL | Deshabilitar o cambiar credencial comprometida | Revisar conexiones y operaciones sobre datos |
| Redis | Revocar o cambiar credencial comprometida | Revisar accesos y operaciones sobre caché |
| Credencial de auditoría | Revocar acceso del worker y emitir nueva credencial | Verificar integridad y continuidad de auditoría |
| Tokens OAuth2 | Invalidar sesiones o tokens cuando sea posible | Revisar operaciones realizadas con la identidad afectada |
| DEMO_API_KEY | Confirmar que continúa siendo un valor ficticio | Verificar que no se haya sustituido por una credencial real |

## 7. Prevención de secretos en el repositorio

MediTriage utiliza Gitleaks como control de detección
de credenciales en el código y en el historial de Git.

El análisis debe ejecutarse en el pipeline de integración
continua y bloquear los cambios cuando detecte secretos.

Adicionalmente:

- No versionar archivos .env con valores reales.
- No versionar archivos terraform.tfstate.
- No versionar credenciales locales de Terraform.
- No versionar archivos kubeconfig.
- No incluir credenciales reales en archivos YAML.
- No compartir secretos mediante issues, PRs o capturas.
- Utilizar exclusivamente valores ficticios en pruebas.

Gitleaks es un control preventivo y de detección.
Un resultado sin hallazgos no garantiza por sí solo
la ausencia absoluta de credenciales expuestas.

## 8. Evidencias de implementación

Validaciones realizadas el 26 de noviembre de 2026.

| Validación | Resultado |
|---|---|
| Listado de GitHub Actions Secrets | GITOPS_TOKEN presente |
| Configuración de HCP Terraform | Organización y workspace definidos |
| Configuración del proveedor Kubernetes | Contexto kind-meditriage definido |
| Secret de demostración en Terraform | Definido |
| Secret de demostración en Kubernetes | Presente, tipo Opaque, una clave |
| Inventario de responsables | Documentado |
| Política de rotación | Propuesta documentada |
| Procedimiento ante filtraciones | Documentado |
| Gitleaks v8.24.3 - Historial completo | 123 commits analizados, 0 filtraciones detectadas |
| Gitleaks v8.24.3 - Cambios preparados | 0 filtraciones detectadas |

Comandos utilizados para verificar la existencia de secretos
sin imprimir sus valores:

    gh secret list
    kubectl get secrets -n meditriage

No se consultaron ni extrajeron los valores de los secretos
reales durante la elaboración de este inventario.

## 9. Limitaciones y trabajo pendiente

- Aprobar formalmente la política de rotación propuesta.
- Implementar las credenciales de los servicios de IA,
  PostgreSQL, Redis y auditoría cuando estén disponibles.
- Configurar variables sensitive en HCP para los servicios
  que requieran credenciales reales.
- Verificar expiración y permisos efectivos de GITOPS_TOKEN.
- Verificar el mecanismo efectivo de autenticación con HCP.
- Implementar la validación de tokens OAuth2 y scopes.
- Configurar cifrado en reposo y TLS en producción.
- Implementar un registro operativo de rotaciones.
- Automatizar la rotación cuando los proveedores lo permitan.

## 10. Referencias

- [ADR 0004 - Datos y eventos](../adr/0004-datos-y-eventos.md)
- [ADR 0005 - Plataforma Kubernetes](../adr/0005-plataforma-k8s.md)
- [Modelo de amenazas](../threat-model.md)
- [Configuración de Secrets](../../terraform/secrets.tf)
- [Configuración HCP Terraform](../../terraform/versions.tf)
- [Proveedor Kubernetes](../../terraform/provider.tf)
- [Pipeline de integración continua](../../.github/workflows/ci.yml)
- [Pipeline de publicación](../../.github/workflows/publish-image.yml)
- [Issue #126](https://github.com/constanzavaldiviadiaz-svg/meditriage/issues/126)
