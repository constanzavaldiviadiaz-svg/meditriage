# Prueba de que los gates de seguridad bloquean

Issue #97 · Sesión 09 · 27/11/2026

La rúbrica de la S09 no pide solo que existan los escaneos: pide que sean **bloqueantes**. Un
gate que nunca se vio fallar no está demostrado. Esta prueba hace fallar cada gate de
`.github/workflows/security.yml` con un caso propio, y verifica que falle **ese** gate y no
los otros.

## Cómo se hizo

- **Dónde:** en el PR #160, un borrador que nunca se fusionó. Partió de la rama del #143,
  porque el SCA con Trivy todavía no estaba en `main`.
- **Cómo:** un caso por commit. Cada paso revierte el caso anterior antes de agregar el
  siguiente, para que en cada ejecución haya una sola cosa mal.
- **Con datos falsos:** el `print` no imprime ningún RUT real (en la prueba no corre nada), y
  el token se generó al azar y nunca fue una credencial.
- **Al terminar:** el PR se cerró sin fusionar y su rama se borró. Gitleaks revisa todas las
  ramas, así que mientras la rama existía el token falso hacía fallar el check en los demás
  PRs.

## Resultado

| Paso | Commit | Qué se agregó | SAST (Semgrep) | SCA (Trivy) | Secretos (Gitleaks) |
|---|---|---|---|---|---|
| 0 | `7afb9b6` | Nada: es la rama del #143, la línea base | ✅ | ✅ | ✅ |
| 1 | `d093315` | Un `print` del RUT en `src/registro/rutas.py` | ❌ | ✅ | ✅ |
| 2 | `7774db7` | `django==2.2.0` en `requirements.txt` | ✅ | ❌ | ✅ |
| 3 | `3848fbf` | Un token falso en `prueba_gate_secretos.py` | ✅ | ✅ | ❌ |
| 4 | `155a597` | Se revierte el token | ✅ | ✅ | ❌ |

**Cada gate falló con su caso, y solo con su caso.** Los demás checks del PR (Ruff, pruebas y
Spectral) siguieron en verde en todos los pasos.

| Paso | Ejecución de `security.yml` |
|---|---|
| 0 | [46025755561](https://github.com/constanzavaldiviadiaz-svg/meditriage/actions/runs/46025755561) |
| 1 | [46026003257](https://github.com/constanzavaldiviadiaz-svg/meditriage/actions/runs/46026003257) |
| 2 | [46027010582](https://github.com/constanzavaldiviadiaz-svg/meditriage/actions/runs/46027010582) |
| 3 | [46027282546](https://github.com/constanzavaldiviadiaz-svg/meditriage/actions/runs/46027282546) |
| 4 | [46027623244](https://github.com/constanzavaldiviadiaz-svg/meditriage/actions/runs/46027623244) |

GitHub borra los logs de las ejecuciones a los 90 días. Por eso los extractos y las capturas
quedan aquí.

### Paso 0 · Línea base: los tres checks en verde

![Los tres jobs de security.yml en verde en el PR #143](evidencias/gates-0-linea-base.png)

### Paso 1 · SAST: un `print` del RUT

Lo detecta una de nuestras reglas propias, `meditriage-pii-en-logs`, y no una regla genérica:
la Ley 19.628 exige enmascarar los datos personales en los logs.

```text
    src/registro/rutas.py
   ❯❯❱ semgrep.meditriage-pii-en-logs
          ❰❰ Blocking ❱❱
          El RUT o el nombre del paciente llegan a un log o a la salida estándar. La Ley 19.628 exige
          enmascarar los datos personales: registra el pacienteId o usa enmascarar_rut().

           65┆ print("Registrando paciente", datos.rut)  # PRUEBA #97: debe bloquear el SAST

 • Findings: 1 (1 blocking)
```

![Solo falla el job de Semgrep](evidencias/gates-1-sast.png)

### Paso 2 · SCA: una dependencia con CVE críticos

`django==2.2.0` tiene seis vulnerabilidades CRITICAL conocidas, todas con parche. Falla la
primera pasada de Trivy, la que bloquea toda CRITICAL, tenga o no parche.

```text
Total: 6 (CRITICAL: 6)
│ django  │ CVE-2019-14234 │ CRITICAL │ fixed  │ 2.2.0 │ 1.11.23, 2.1.11, 2.2.4 │ Django: SQL injection possibility in key and index lookups
│         │ CVE-2019-19844 │          │        │       │ 1.11.27, 2.2.9, 3.0.1  │ Django: crafted email address allows account takeover
│         │ CVE-2020-7471  │          │        │       │ 1.11.28, 2.2.10, 3.0.3 │ django: potential SQL injection via StringAgg(delimiter)
│         │ CVE-2022-28346 │          │        │       │ 2.2.28, 3.2.13, 4.0.4  │ Django: SQL injection in QuerySet.annotate(),aggregate() and
│         │ CVE-2022-28347 │          │        │       │                        │ Django: SQL injection via QuerySet.explain(options) on
│         │ CVE-2025-64459 │          │        │       │ 5.2.8, 5.1.14, 4.2.26  │ django: Django SQL injection
```

![Solo falla el job de Trivy](evidencias/gates-2-sca.png)

### Paso 3 · Secretos: un token en el código

```text
INF 145 commits scanned.
WRN leaks found: 1
```

El log no muestra el valor encontrado: el workflow corre Gitleaks con `--redact`, así que un
secreto real tampoco quedaría expuesto en los logs del pipeline.

![Solo falla el job de Gitleaks](evidencias/gates-3-secretos.png)

### Paso 4 · Revertir el token no basta

Después de borrar el token en un commit nuevo, Gitleaks **sigue fallando**:

```text
INF 145 commits scanned.
WRN leaks found: 1
```

Es lo esperado: el workflow descarga el historial completo (`fetch-depth: 0`) y revisa todos
los commits de todas las ramas (`--log-opts="--all"`), y el token sigue en el commit que lo
agregó. **Por eso un secreto que llegó al repositorio se rota, aunque después se borre.** El
procedimiento está en `docs/security/secretos.md`.

![Gitleaks sigue fallando después de revertir](evidencias/gates-4-historial.png)

## Gates de la S10

La S10 agrega tres controles: el IaC scan con Checkov (#144), el DAST con ZAP (#162) y la
admisión con Kyverno (#146). Los dos primeros se probaron igual que los de la S09, en el PR
#163, un borrador que juntó el #162, el #144 y la excepción de Gitleaks del #143. Nunca se
fusionó y su rama se borró.

| Paso | Commit | Qué se agregó | SAST | Secretos | IaC (Checkov) | DAST (ZAP) |
|---|---|---|---|---|---|---|
| 0 | `24d3cca` | Nada: la línea base | ✅ | ✅ | ✅ | ✅ |
| 1 | `5d819bf` | `privileged: true` en el contenedor de `k8s/deployment.yaml` | ✅ | ✅ | ❌ | ✅ |
| 2 | `072bf74` | Se revierte el paso 1 y la app agrega `Access-Control-Allow-Origin: *` a todas las respuestas | ✅ | ✅ | ✅ | ❌ |

### Paso 1 · IaC scan: un contenedor privilegiado

```text
Check: CKV_K8S_16: "Container should not be privileged"
	FAILED for resource: Deployment.meditriage.meditriage-api
	File: /k8s/deployment.yaml:1-67
Passed checks: 94, Failed checks: 1, Skipped checks: 0
```

![Solo falla el job de Checkov](evidencias/gates-s10-1-checkov.png)

### Paso 2 · DAST: CORS abierto a cualquier origen

ZAP no bloquea por sus propias advertencias: el umbral lo decide `.zap/evaluar.py`, que bloquea
con riesgo Medium o superior. Las alertas Low siguen en el informe, pero no bloquean.

```text
Medium        BLOQUEA      Cross-Domain Misconfiguration [10098], 2 instancia(s)
Low           no bloquea   X-Content-Type-Options Header Missing [10021], 1 instancia(s)
Informational no bloquea   A Client Error response code was returned by the server [100000], 16 instancia(s)

1 alerta(s) de riesgo Medium o superior: el DAST bloquea.
```

![Solo falla el job de ZAP](evidencias/gates-s10-2-dast.png)

### Kyverno: una imagen sin firma no entra al clúster

Este gate no es del pipeline sino del clúster, así que se prueba en kind con
`bash k8s/policies/probar-policy.sh` (#146). La imagen "sin firma" es la que desplegaba
`k8s/deployment.yaml` hasta el #146: se publicó antes de que el pipeline firmara.

```text
== Admisión en el namespace meditriage
   ok: imagen firmada por el pipeline -> entra
   ok: nuestra imagen, pero sin firma -> rechazada
      Policy require-image-signature failed: La imagen no tiene una firma válida del pipeline de MediTriage 
   ok: imagen de terceros -> rechazada
      Policy require-image-signature failed: La imagen no tiene una firma válida del pipeline de MediTriage 

Todas las pruebas pasaron.
```

## Lo que la prueba no cubre

- **Que el merge se bloquee.** El check falla, pero lo que impide fusionar es que el check sea
  obligatorio en la protección de `main`. Hoy lo son Semgrep y Gitleaks. **Los checks de Trivy
  (#143), Checkov (#144) y ZAP (#162) hay que agregarlos como obligatorios cuando se fusionen.**

## Cómo repetirla

1. Crear una rama desde `main` y abrir un PR en borrador, marcado **NO FUSIONAR**.
2. Un commit por caso, revirtiendo el anterior: un `print` de `datos.rut` en `src/`, una
   dependencia vieja con CVE CRITICAL en `requirements.txt`, y un token falso generado al azar
   con forma de clave (`API_KEY = "..."` con 40 caracteres aleatorios).
3. Revisar en cada ejecución de `security.yml` que falle solo el job esperado.
4. Cerrar el PR sin fusionar y **borrar la rama de inmediato**.
