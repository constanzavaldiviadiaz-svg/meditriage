# Política de versionado de la API

Cómo evoluciona el contrato de [`api/openapi.yaml`](../../api/openapi.yaml) sin romper a quien
lo consume.

## La regla base

**Nunca romper un contrato publicado.** Una API se puede ampliar; lo que ya existe no se quita
ni se cambia de significado dentro de la misma versión.

## Dónde vive la versión

**En la ruta:** `/v1/pacientes`, `/v1/encuentros`. Es explícito, se ve en cada llamada y en
cada log, y permite que dos versiones convivan en el mismo servidor.

El campo `info.version` del contrato sigue versionado semántico (`MAYOR.MENOR.PARCHE`):

| Cambio | Ejemplo | Versión |
|---|---|---|
| **Mayor** | Se rompe la compatibilidad | `1.4.2` → `2.0.0` y nueva ruta `/v2/` |
| **Menor** | Se agrega algo compatible | `1.4.2` → `1.5.0` |
| **Parche** | Se corrige documentación o un ejemplo | `1.4.2` → `1.4.3` |

## Qué rompe y qué no

### Compatible — se publica dentro de `/v1/`

- Agregar un endpoint nuevo
- Agregar un campo **opcional** en una solicitud
- Agregar un campo en una respuesta
- Agregar un valor nuevo a un `enum` de respuesta, siempre que los clientes ignoren los valores
  que no conocen
- Agregar un tipo de problema RFC 7807 nuevo
- Agregar un tipo de contenido alternativo, como `text/event-stream`

### Incompatible — exige `/v2/`

- Eliminar o renombrar un endpoint, un campo o un parámetro
- Volver **obligatorio** un campo que era opcional
- Cambiar el tipo de un campo
- Cambiar el significado de un campo existente, aunque se llame igual
- Cambiar el código de estado de una respuesta existente
- Restringir una validación: por ejemplo, acortar un `maxLength`

**En caso de duda, se trata como incompatible.**

## Cómo se retira una versión

Cuando exista una `/v2/`, la `/v1/` no desaparece de un día para otro:

1. **Anuncio.** Las respuestas de la versión antigua empiezan a llevar las cabeceras
   `Deprecation` y `Sunset` (RFC 8594), con la fecha de retiro.
2. **Convivencia.** Ambas versiones funcionan en paralelo durante **al menos 90 días**.
3. **Retiro.** Llegada la fecha, la versión antigua responde `410 Gone` con un problema RFC 7807
   que indica la versión vigente.

## Un caso propio de MediTriage

Los registros del **audit log se conservan 5 años**, más que la vida de cualquier versión de la
API. Por eso cada decisión registrada guarda la versión del contrato con que se creó: un
auditor que consulte en `/v3/` una decisión tomada en `/v1/` debe poder interpretarla.

## Cómo se cambia el contrato

El contrato se modifica como cualquier otro archivo del repositorio: issue, rama y Pull Request
revisado por otro integrante. Además:

- El contrato debe pasar el lint de Spectral sin errores
- Un cambio incompatible requiere un ADR que lo justifique
- Todo PR que modifique `api/openapi.yaml` declara si el cambio es compatible o incompatible
