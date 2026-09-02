# Cómo trabajamos en MediTriage

Este documento describe **cómo se contribuye al repositorio**. Los acuerdos del equipo
—roles, valores, Definition of Done y política de uso de IA— están en el
[CHARTER](CHARTER.md).

## Regla base

**Nadie sube cambios directo a `main`.** Ni siquiera la dueña del repositorio.

Todo cambio pasa por una rama y un Pull Request, porque nuestro Definition of Done exige que
cada tarea sea revisada por al menos otro integrante. El Pull Request es el lugar donde esa
revisión ocurre.

## El ciclo completo

```
issue  →  rama  →  commit  →  push  →  Pull Request  →  revisión  →  merge
```

Un issue = una rama = un Pull Request.

### 1. Parte de un issue

Si no existe un issue para lo que vas a hacer, créalo primero. El issue dice *qué* hay que
hacer y cuándo se considera terminado.

### 2. Crea la rama

El formato es `tipo/N-descripcion-corta`, donde `N` es el número del issue:

| Prefijo | Para qué |
|---|---|
| `feat/` | funcionalidad nueva |
| `fix/` | corrección de un error |
| `docs/` | documentación |
| `chore/` | configuración, dependencias, mantenimiento |

Ejemplos: `docs/12-impact-map` · `feat/23-formulario-sintomas` · `chore/6-gitignore`

### 3. Trabaja y haz commit

El mensaje de commit explica **por qué** se hizo el cambio, no solo qué archivo se tocó.

Si usaste IA generativa, declárala en el mensaje del commit. Es regla del ramo y está en el
[CHARTER](CHARTER.md).

### 4. Sube la rama y abre el Pull Request

En el cuerpo del PR, incluye `Closes #N` para que el issue se cierre solo al fusionar.

> ⚠️ La palabra clave debe ir **en inglés**: `Closes`, `Fixes` o `Resolves`. En español no
> funciona: GitHub no la reconoce y el issue queda abierto.

### 5. Espera la revisión

**No fusiones tu propio Pull Request.** Pide revisión a otro integrante. Si el cambio afecta
a un área con responsable —calidad, seguridad o arquitectura— pide además la revisión de
quien tiene ese rol.

### 6. Fusiona y limpia

Merge con **squash**, y borra la rama después. Nunca hagas `force-push` sobre `main`.

## Desde la terminal

```bash
git switch main
git pull

git switch -c docs/12-impact-map
# ...trabajas...
git add -A
git commit -m "docs: completa el Impact Map"
git push -u origin docs/12-impact-map

gh pr create --base main
```

## Desde el editor web de GitHub

No hace falta clonar el repositorio ni instalar nada. Al editar un archivo y guardar, GitHub
ofrece la opción **"Create a new branch for this commit and start a pull request"**.
Selecciónala, ponle a la rama el nombre según la convención de arriba, y el Pull Request
queda abierto.

## Antes de empezar a trabajar, siempre

```bash
git pull
```

Git no sincroniza solo. Si alguien subió cambios y tú no los bajaste, vas a trabajar sobre
una versión desactualizada y después los cambios chocan.

## Dónde vive cada cosa

| Ruta | Contenido |
|---|---|
| `docs/adr/NNNN-titulo.md` | Decisiones de arquitectura. Formato: Título · Contexto · Decisión · Consecuencias · Fecha · Autores |
| `docs/impact-map.md` | Objetivo de negocio, actores, impactos y entregables |
| `docs/backlog.md` | Historias de usuario y priorización |
| `docs/scenarios/*.feature` | Criterios de aceptación en Gherkin, un archivo por historia |

Los ADR no se reescriben cuando cambian las circunstancias: son actas históricas. Si una
decisión cambia, se escribe un ADR nuevo que reemplace al anterior.
