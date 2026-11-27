# ADR 0007 — Cadena de suministro: firma de imágenes y SLSA

## Estado

Propuesto — 26/11/2026

Pasa a *Aceptado* cuando el equipo apruebe el Pull Request correspondiente.

**Sobre el número:** la sesión 10 llama a este documento "ADR 0006", pero ese número ya
corresponde a GitOps (#79), por la misma corrida que explica el
[ADR 0005](0005-plataforma-k8s.md).

## Autores

Fernando Ureta (Tech Lead · AI/Data Lead).

## Contexto

El pipeline de la sesión 09 revisa **lo que entra** a la imagen: el código (Semgrep), los
secretos (Gitleaks), las dependencias (Trivy) y su inventario (SBOM). Nada prueba todavía **de
dónde salió la imagen** que corre en el clúster.

Hoy la imagen se referencia por digest en los manifiestos. El digest garantiza que la imagen no
cambió, pero no dice quién la construyó. Cualquiera con permiso de escritura en GHCR, por
ejemplo con un token filtrado, puede subir una imagen y proponer su digest. Quien revisa el
Pull Request en el repositorio GitOps ve un hash y no tiene cómo saber su origen. Es la amenaza
T3 del [threat model](../threat-model.md), que dejó la firma de imágenes para esta sesión.

Tres ataques reales muestran dónde se rompe la cadena:

| Ataque | Qué pasó | Qué exige |
|---|---|---|
| **SolarWinds** (2020) | Los atacantes entraron al sistema de build de Orion. La actualización maliciosa salió **firmada con el certificado legítimo** de la empresa, y unos 18.000 clientes la descargaron | Una firma sola no basta: hay que saber **qué build** la produjo y desde qué código |
| **XZ Utils** (2024) | Un mantenedor que se ganó la confianza del proyecto durante dos años insertó una puerta trasera. La pieza que la activaba estaba solo en los paquetes publicados, **no en el repositorio** | Lo publicado tiene que poder rastrearse hasta el código revisado |
| **tj-actions/changed-files** (2025) | El atacante movió las etiquetas de versión de una acción de GitHub a un commit malicioso, que imprimió en los logs los secretos de miles de pipelines | Una etiqueta se puede mover; las acciones se fijan por SHA |

Las restricciones que filtran la decisión:

| Restricción | Qué le exige a la cadena de suministro |
|---|---|
| Datos de salud (Ley 19.628 y 21.719) | Poder demostrar qué software procesó los datos |
| Auditoría inmutable por 5 años | Que la prueba se pueda verificar años después |
| Cuatro estudiantes, un semestre | No sumar llaves que guardar ni rotar |
| Proveedor cloud no elegido (ADR 0003) | Estándares abiertos, que funcionen en cualquier registro y clúster |
| Repositorio público | La identidad de quien firma puede ser pública |

## Decisión

### 1. Firma *keyless* con Cosign

El workflow `publish-image.yml` firma la imagen con **Cosign**, de Sigstore, apenas la publica
en GHCR. Se firma el **digest**, nunca la etiqueta.

No hay llave privada:

1. GitHub Actions entrega al job un **token OIDC** que dice "soy el workflow
   `publish-image.yml` del repositorio `meditriage`, corriendo en `main`".
2. **Fulcio**, la autoridad de Sigstore, emite con ese token un certificado que dura 10
   minutos.
3. Cosign firma con ese certificado, y la firma queda en el registro, junto a la imagen, y en
   **Rekor**, un log público de transparencia donde nada se borra.

La firma no dice "alguien tenía la llave". Dice **"esto lo construyó este workflow, en esta
rama"**. Se puede verificar después de que el certificado venza, porque Rekor prueba que la
firma se hizo mientras era válido.

**La única identidad aceptada:**

| Campo | Valor |
|---|---|
| Identidad | `https://github.com/constanzavaldiviadiaz-svg/meditriage/.github/workflows/publish-image.yml@refs/heads/main` |
| Emisor | `https://token.actions.githubusercontent.com` |

Una firma hecha desde otra rama, otro workflow o un fork no pasa.

**Formato de la firma.** Cosign 3 guarda la firma, por defecto, en un formato nuevo (*Sigstore
bundle*) que se publica como *referrer* OCI. GHCR no implementa la API de referrers, y Kyverno
no encuentra la firma en ese formato con su configuración normal. Por eso se firma en el
**formato clásico**, con la etiqueta `sha256-<digest>.sig`:

```bash
cosign sign --yes --new-bundle-format=false --use-signing-config=false "$IMAGEN@$DIGEST"
```

Se probó con Cosign 3.1.4 contra un registro local:

- con esas opciones, la firma queda en la etiqueta `.sig`;
- sin ellas, queda en una etiqueta `sha256-<digest>` sin `.sig`, que Kyverno no lee;
- `cosign verify` acepta el formato clásico sin opciones adicionales.

### 2. Provenance SLSA de nivel 2

La acción oficial `actions/attest-build-provenance` genera la **provenance**: un documento, en
el formato SLSA v1, que dice qué commit, qué workflow y qué ejecución produjeron la imagen. La
firma con la misma identidad del punto 1 y la sube a GHCR junto a la imagen.

Con eso, cualquiera puede ir de un digest al commit que lo produjo, y de ahí al Pull Request y
a sus revisores:

```bash
gh attestation verify oci://ghcr.io/constanzavaldiviadiaz-svg/meditriage-api@<digest> \
  --owner constanzavaldiviadiaz-svg
```

**Por qué nivel 2 y no 3:**

| Nivel | Qué garantiza |
|---|---|
| 1 | El build está documentado |
| 2 | El build corre en una plataforma hospedada, que firma la provenance |
| 3 | Además, los pasos del build no pueden alterar la provenance: el build corre aislado |

GitHub documenta que sus *artifact attestations*, por sí solas, cumplen el nivel 2. El nivel 3
exige mover el build a un *reusable workflow* aislado. No se hace ahora porque:

- **La rúbrica de la sesión pide el nivel 2.**
- **El riesgo que cubre el nivel 3 ya está acotado.** Alterar el build exige cambiar
  `publish-image.yml`, y cualquier cambio a `main` requiere dos aprobaciones.
- **Es el siguiente paso natural** si MediTriage llegara a producción real, y no obliga a
  cambiar de herramienta.

### 3. Verificación en dos puntos

**En el pipeline.** Justo después de firmar, `cosign verify` comprueba la firma con la
identidad exacta del punto 1. Si falla, el job falla y la imagen no se promueve al repositorio
GitOps (#113): solo se proponen imágenes verificadas.

**En el clúster.** Una policy de **Kyverno** (`k8s/policies/require-signature.yaml`, #118), en
modo `Enforce`, rechaza cualquier pod del namespace `meditriage` cuya imagen
`ghcr.io/constanzavaldiviadiaz-svg/meditriage-api` no tenga una firma válida de esa identidad.
Exige además que la imagen venga referenciada por digest.

Kyverno verifica la firma, no la provenance. La firma ya basta para saber que la imagen salió
del workflow oficial. La provenance responde otra pregunta, desde qué commit se construyó, y la
consulta quien audita.

### 4. Escaneos que bloquean

Se suman a los de la sesión 09 (Semgrep, Gitleaks y Trivy sobre las dependencias). Corren en
cada Pull Request y son checks obligatorios, así que lo que llega a `main` ya los pasó. El de
contenedor se repite, además, sobre la imagen publicada, justo antes de firmarla (punto 6).

| Escaneo | Herramienta | Sobre qué | Bloquea con | Issue |
|---|---|---|---|---|
| Infraestructura como código | Checkov | `terraform/` y `k8s/` | Cualquier falla | #116 |
| Contenedor | Trivy | La imagen construida en el PR y, en `main`, la publicada | CRITICAL siempre; HIGH si tiene parche | #92 |
| DAST | ZAP, *API scan* | La aplicación levantada como contenedor dentro del pipeline, usando su contrato OpenAPI | Riesgo Medium o superior | #117 |

**Una vulnerabilidad CRITICAL bloquea siempre, tenga o no parche.** Si hay parche, se
actualiza. Si no lo hay, no queda excluida en silencio: el DevSecOps Lead la evalúa con los
criterios del README (si el código vulnerable se alcanza desde internet y si puede afectar
datos de pacientes) y elige uno de tres caminos: cambiar la dependencia o la imagen base,
mitigarla de otra forma, o pedir una excepción con esa evaluación escrita. Una HIGH sin parche
no bloquea, pero queda en el reporte del job. En Trivy son dos pasadas: `--severity CRITICAL`
sin `--ignore-unfixed`, y `--severity HIGH` con `--ignore-unfixed`.

**Excepciones.** Siguen el proceso del README: la propone el DevSecOps Lead, la aprueba la
Product Owner y queda en la descripción del PR. Para que ninguna quede olvidada:

- **Cada excepción tiene un issue**, con la etiqueta `seguridad`, asignado al DevSecOps Lead,
  con la evaluación de riesgo y la **fecha de vencimiento en el título**. Los issues abiertos
  con esa etiqueta son el registro de las excepciones vigentes. El issue se cierra cuando la
  excepción se elimina.
- **El vencimiento no pasa el plazo de corrección del README** para esa severidad: 7 días para
  una crítica, 30 para una alta y 90 para una media. Al vencer, se corrige el hallazgo o se
  vuelve a aprobar la excepción con una evaluación nueva, por el mismo proceso.
- **En Trivy, la excepción vence sola.** Va en `.trivyignore.yaml`, con el motivo en
  `statement` y la fecha en `expired_at`. Pasada esa fecha, Trivy deja de ignorar el hallazgo
  y el pipeline vuelve a bloquear. Por eso se usa este archivo y no el VEX que menciona el
  README: la fecha la hace cumplir la herramienta. Trivy marca este formato como experimental;
  si cambia, se ajusta el archivo.
- **En Checkov y ZAP la excepción no vence sola.** Va en el `skip` comentado del mismo archivo
  (Checkov) o en `.zap/rules.tsv` (ZAP), y el seguimiento lo da su issue, que dice dónde está.

La sesión propone un ADR por cada excepción. Aquí no: un ADR registra una decisión que dura, y
una excepción tiene fecha de vencimiento.

### 5. Acciones fijadas por SHA

Toda acción de GitHub Actions, también las de GitHub, se referencia por el **SHA completo del
commit**, con la versión en un comentario:

```yaml
uses: sigstore/cosign-installer@756fe2d284c7292c4e9b62c8a28f1e5629c59532 # v4.1.3
```

Un SHA no se puede mover. Una etiqueta como `@v4` sí, que es lo que explotó el ataque a
tj-actions. Las acciones que hoy van por etiqueta en `ci.yml` y `publish-image.yml` se fijan al
modificar cada workflow. Cuando no quede ninguna, la dueña del repositorio puede activar la
política de GitHub Actions que exige SHA, y el repositorio deja de aceptar etiquetas.

**Dependabot mantiene los SHA al día.** `.github/dependabot.yml` activa las actualizaciones del
ecosistema `github-actions`, una vez por semana. Dependabot entiende los SHA: propone el commit
nuevo y actualiza el comentario de versión. Cada propuesta llega como Pull Request y pasa por
las mismas reglas que cualquier otro, los checks obligatorios y dos aprobaciones. Nunca se
fusiona sola.

### 6. Orden en `publish-image.yml`

Al fusionar en `main`:

1. Construir y publicar la imagen en GHCR.
2. **Escanear con Trivy la imagen publicada, por su digest**, con los umbrales del punto 4.
3. Generar el SBOM (#93).
4. Firmar la imagen.
5. Verificar la firma.
6. Adjuntar la provenance.
7. Proponer el nuevo digest al repositorio GitOps (#113).

Si cualquier paso falla, los siguientes no corren. **La promoción va al final y depende de todo
lo anterior.** Si queda en otro job, ese job declara `needs:` sobre el de publicación, y no
corre si fallaron el escaneo, la firma, la verificación o la provenance. Una imagen que no pasó
el escaneo queda en GHCR sin firma, y Kyverno no la deja entrar al clúster.

### 7. Retención

La firma y la provenance viven en GHCR junto a la imagen, y la firma además en Rekor, que no
borra. GHCR no elimina versiones por su cuenta. Si algún día se configura una limpieza de
imágenes antiguas, quedan fuera las que llegaron a producción: la auditoría de 5 años tiene que
poder verificar qué software tomó cada decisión.

## Consecuencias

### Positivas

- **Ninguna llave que guardar ni rotar.** La firma no agrega secretos al inventario (#126).
- **Cada imagen se rastrea hasta su origen**: digest → provenance → commit → Pull Request →
  revisores.
- **Una imagen subida a mano a GHCR no entra al clúster**, aunque quien la suba tenga un token
  válido.
- **Lo que se firma es lo que se escaneó.** El escaneo de `main` y la firma usan el mismo
  digest.
- **Cierra la amenaza T3 del threat model**, cuando se fusionen el #115 y el #118.
- **Estándares abiertos.** Sigstore y SLSA funcionan con cualquier registro OCI y cualquier
  Kubernetes, coherente con no haber elegido proveedor (ADR 0003 y 0005).

### Negativas

- **Se depende de la infraestructura pública de Sigstore.** Si Fulcio o Rekor no responden, no
  se puede firmar, y el job de publicación falla hasta que vuelvan. Lo que ya está desplegado
  no se ve afectado.
- **Kyverno falla cerrado.** Si no logra verificar una firma, o si Kyverno mismo está caído,
  rechaza los pods nuevos. Se prefiere no levantar una réplica antes que levantar una sin
  verificar. Los pods que ya corren siguen. En producción, Kyverno corre con tres réplicas
  para no volverse un punto único de falla.
- **El formato clásico de firma va de salida.** Cosign 3 ya marca como obsoleta una de las
  opciones que lo activan, así que puede desaparecer en una versión futura. Como el instalador
  está fijado por SHA, no cambia solo. Cuando Kyverno lea el formato nuevo en GHCR, se migra a
  ese formato.
- **La identidad de quien firma queda en un log público**: el nombre del repositorio y del
  workflow. El repositorio ya es público, así que no se expone nada nuevo. Si pasara a privado,
  `actions/attest-build-provenance` usa la instancia privada de Sigstore de GitHub, pero la
  firma de Cosign habría que revisarla.
- **Renombrar `publish-image.yml` o cambiar la rama cambia la identidad.** El mismo Pull Request
  tiene que actualizar la policy de Kyverno y el paso de verificación.
- **Kyverno solo verifica nuestra imagen.** Las de terceros, como Traefik, Argo CD, Kyverno o
  Falco, no van firmadas por nosotros. Se instalan con Helm, en versiones fijas.
- **Las dependencias transitivas no están fijadas.** `requirements.txt` fija FastAPI y Uvicorn,
  pero no lo que ellas instalan, como Starlette o Pydantic. Dos construcciones del mismo commit
  pueden traer versiones distintas, así que la imagen escaneada en el PR puede no tener el mismo
  contenido que la publicada. Por eso la publicada se vuelve a escanear antes de firmarla (punto
  6). Fijar las transitivas con hashes, por ejemplo con `pip-compile --generate-hashes`, haría
  reproducible el build. Queda como mejora.
- **Un build de `main` puede fallar aunque su PR haya pasado**, si entremedio cambió una
  dependencia transitiva o se publicó una vulnerabilidad nueva. Es lo buscado: no se firma lo
  que no pasó el escaneo. Lo corrige un PR nuevo.
- **Dependabot suma Pull Requests que revisar**, uno por cada acción que se actualiza. Es el
  costo de que ninguna actualización entre sin revisión.

## Alternativas descartadas

### Cosign con un par de llaves propio

La llave privada viviría como secreto en GitHub. Hay que protegerla, rotarla y, si se filtra,
cualquiera puede firmar lo que quiera hasta que se revoque. *Keyless* da la misma verificación
sin ese secreto, y además ata la firma al workflow y la rama, no solo a quien tenga la llave.

### Notation (Notary Project)

El otro estándar de firma de imágenes. Funciona con certificados X.509 propios y un almacén de
confianza, así que vuelve al problema anterior: certificados que emitir, guardar y renovar. Su
ecosistema está más ligado a servicios de firma de un proveedor cloud.

### La provenance escrita a mano y adjuntada con `cosign attest`

Es el ejemplo de la sesión: un paso del workflow escribe `provenance.json` y Cosign lo adjunta.
Se descarta porque el contenido lo escribimos nosotros. Un error lo deja incompleto o falso, y
nadie lo nota. `actions/attest-build-provenance` lo genera a partir de los datos de la
ejecución, en el formato estándar.

### `slsa-github-generator` (nivel 3)

Genera la provenance en un workflow aislado y alcanza el nivel 3. Obliga a reorganizar el
pipeline en jobs separados que se pasan el digest, para un nivel que la sesión no pide.
Explicado en el punto 2.

### OPA Gatekeeper

El otro admission controller de la sesión. Sus políticas se escriben en Rego, un lenguaje más
que aprender, y no verifica firmas por sí solo: necesita un proveedor externo de datos. Kyverno
escribe las políticas en YAML y trae la verificación de Cosign incluida.

### Sigstore policy-controller

Verifica firmas y nada más. Kyverno, además de la firma, puede exigir otras reglas que la
sesión menciona, como límites de recursos o prohibir `hostNetwork`: una herramienta en vez de
dos.

### DAST contra el ambiente de staging

Es lo que propone la sesión: ZAP después de desplegar. Nuestro staging es un clúster kind en
el computador de un integrante (ADR 0005), y GitHub Actions no lo alcanza. Levantar la imagen
como contenedor dentro del pipeline prueba la misma aplicación, en cada Pull Request y antes de
fusionar.

### Quedarse con el digest y la rama protegida

Es lo que hay hoy. Prueba que la imagen no cambió, pero no de dónde salió: no resuelve la
amenaza T3.
