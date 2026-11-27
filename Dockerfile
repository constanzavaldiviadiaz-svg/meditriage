# Imagen de MediTriage, construida en dos etapas.
#
#   Etapa 1 (build):   una imagen de Python completa, que instala las dependencias.
#   Etapa 2 (runtime): una imagen mínima, que recibe solo lo necesario para correr.
#
# Las herramientas de la etapa 1 (pip, compiladores, shell) no llegan a la imagen final:
# menos tamaño y menos superficie de ataque.
#
# Las imágenes base se fijan por digest (@sha256:...), no solo por etiqueta: una etiqueta
# puede cambiar de contenido de un día para otro; un digest, nunca.

# ---------------------------------------------------------------- Etapa 1: build
FROM python:3.13-slim-trixie@sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50 AS build

WORKDIR /app

# Las dependencias se instalan antes de copiar el código. Docker guarda cada paso en caché:
# si solo cambia el código, este paso no se repite y la construcción es mucho más rápida.
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/dependencias -r requirements.txt

COPY src/ ./src/

# ---------------------------------------------------------------- Etapa 2: runtime
# Distroless: solo Python y lo mínimo para ejecutarlo. Sin shell, sin pip, sin gestor de
# paquetes. Trae Python 3.13, la misma versión mayor y menor de la etapa 1.
# La variante "nonroot" ya define un usuario sin privilegios.
FROM gcr.io/distroless/python3-debian13:nonroot@sha256:72de1dda9d4c52c370e2ef2d93c28e3e1a8193c92058b7dfa42bace38a83d114

WORKDIR /app

COPY --from=build /app/dependencias ./dependencias
COPY --from=build /app/src ./src

# PYTHONPATH: dónde buscar las dependencias instaladas en la etapa 1.
# PYTHONUNBUFFERED: los logs salen de inmediato por la salida estándar (12-Factor, factor XI).
# PYTHONDONTWRITEBYTECODE: no escribir archivos .pyc dentro del contenedor.
ENV PYTHONPATH=/app/dependencias \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PUERTO=8080

# Nunca como root: si alguien comprometiera la aplicación, no tendría privilegios.
USER nonroot

EXPOSE 8080

# Sin shell ni curl, la revisión de salud usa el propio Python para consultar /health.
# En Kubernetes, este papel lo cumplen las sondas del Deployment.
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD ["python3", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ['PUERTO'] + '/health')"]

ENTRYPOINT ["python3", "-m", "src.main"]
