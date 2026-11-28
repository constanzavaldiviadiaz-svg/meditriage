
"""Pruebas de metricas, trazabilidad y privacidad."""

import json

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from src.main import app
from src.observabilidad import logger

client = TestClient(app)


def test_endpoint_metrics():
    respuesta = client.get("/metrics")

    assert respuesta.status_code == 200
    assert "text/plain" in respuesta.headers["content-type"]
    assert "meditriage_http_requests_total" in respuesta.text
    assert "meditriage_http_request_duration_seconds" in respuesta.text


def test_contador_solicitudes():
    labels = {
        "method": "POST",
        "route": "/v1/pacientes",
        "status": "400",
    }

    nombre = "meditriage_http_requests_total"
    antes = REGISTRY.get_sample_value(nombre, labels) or 0

    respuesta = client.post("/v1/pacientes", json={})

    despues = REGISTRY.get_sample_value(nombre, labels)

    assert respuesta.status_code == 400
    assert despues == antes + 1


def test_histograma_duracion():
    labels = {
        "method": "POST",
        "route": "/v1/pacientes",
    }

    nombre = "meditriage_http_request_duration_seconds_count"
    antes = REGISTRY.get_sample_value(nombre, labels) or 0

    client.post("/v1/pacientes", json={})

    despues = REGISTRY.get_sample_value(nombre, labels)

    assert despues == antes + 1


def test_trace_id_interno(monkeypatch):
    eventos = []
    monkeypatch.setattr(logger, "info", eventos.append)

    respuesta = client.post("/v1/pacientes", json={})

    evento = json.loads(eventos[-1])

    assert evento["trace_id"] == respuesta.headers["X-Trace-Id"]
    assert evento["event"] == "http_request"
    assert evento["status"] == 400
    assert evento["duration_ms"] >= 0


def test_trace_id_externo_enmascarado(monkeypatch):
    eventos = []
    monkeypatch.setattr(logger, "info", eventos.append)

    dato_ficticio = "DATO_FICTICIO"

    respuesta = client.post(
        "/v1/pacientes",
        json={},
        headers={"X-Trace-Id": dato_ficticio},
    )

    evento = json.loads(eventos[-1])

    assert respuesta.headers["X-Trace-Id"] == dato_ficticio
    assert evento["trace_id"] == "[REDACTED]"
    assert dato_ficticio not in eventos[-1]


def test_ruta_sin_datos_sensibles(monkeypatch):
    eventos = []
    monkeypatch.setattr(logger, "info", eventos.append)

    respuesta = client.get(
        "/ruta-inexistente?nombre=PACIENTE_FICTICIO"
    )

    evento = json.loads(eventos[-1])

    assert respuesta.status_code == 404
    assert evento["route"] == "unknown"
    assert "PACIENTE_FICTICIO" not in eventos[-1]


def test_endpoints_tecnicos_no_generan_eventos(monkeypatch):
    eventos = []
    monkeypatch.setattr(logger, "info", eventos.append)

    for ruta in ("/health", "/ready", "/metrics"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200

    assert eventos == []
