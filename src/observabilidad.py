"""Metricas Prometheus y logging estructurado de MediTriage."""

import json
import logging
from datetime import UTC, datetime

from prometheus_client import Counter, Histogram

logger = logging.getLogger("meditriage.observabilidad")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

HTTP_REQUESTS = Counter(
    "meditriage_http_requests_total",
    "Total de solicitudes HTTP procesadas",
    ["method", "route", "status"],
)

HTTP_DURATION = Histogram(
    "meditriage_http_request_duration_seconds",
    "Duracion de las solicitudes HTTP en segundos",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10),
)


def registrar_solicitud(
    method: str,
    route: str,
    status: int,
    duration: float,
    trace_id: str,
) -> None:
    """Registra metricas y un evento estructurado sin datos clinicos."""

    HTTP_REQUESTS.labels(
        method=method,
        route=route,
        status=str(status),
    ).inc()

    HTTP_DURATION.labels(
        method=method,
        route=route,
    ).observe(duration)

    evento = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "http_request",
        "trace_id": trace_id,
        "method": method,
        "route": route,
        "status": status,
        "duration_ms": round(duration * 1000, 2),
    }

    logger.info(json.dumps(evento, ensure_ascii=False))