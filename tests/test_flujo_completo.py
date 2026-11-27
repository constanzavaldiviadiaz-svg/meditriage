"""El flujo completo de HU01 a HU05, de punta a punta, contra PostgreSQL.

Es el recorrido de la demo: una enfermera registra al paciente, abre su encuentro, registra
los signos vitales (con una alerta crítica), la IA sugiere una categoría, la enfermera la
confirma, el médico la ve en la sala de espera y el auditor consulta la decisión con su hash.
La sugerencia de la IA la simula el repositorio de evaluaciones: la ruta llega con el #123.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.auditoria import relay
from src.main import app
from tests.ayudantes import NOMBRE, datos_clinicos, evaluar
from tests.conftest import BASE_AUDITORIA, admin

pytestmark = pytest.mark.usefixtures("base_limpia")

cliente = TestClient(app)


def test_flujo_completo_hu01_a_hu05():
    # HU01 · La enfermera registra al paciente, con su consentimiento.
    registro = cliente.post("/v1/pacientes", headers={"Idempotency-Key": str(uuid4())}, json={
        "rut": "12345678-5", "nombre": NOMBRE, "fechaNacimiento": "1958-03-14",
        "sexo": "femenino", "consentimiento": {"estado": "otorgado"},
    })
    assert registro.status_code == 201
    paciente_id = registro.json()["pacienteId"]

    # HU02 · Abre el encuentro y registra los signos vitales: saturación de 85 %.
    encuentro = cliente.post("/v1/encuentros", headers={"Idempotency-Key": str(uuid4())},
                             json={"pacienteId": paciente_id})
    assert encuentro.status_code == 201
    encuentro_id = encuentro.json()["encuentroId"]

    datos = cliente.put(f"/v1/encuentros/{encuentro_id}/datos-clinicos",
                        json=datos_clinicos(motivo="Dificultad respiratoria",
                                            saturacionOxigeno=85))
    assert datos.status_code == 200
    assert {"signo": "saturacion_oxigeno", "valor": "85", "nivel": "critico"} in (
        datos.json()["alertas"])

    # HU03 · La IA sugiere ESI 2 y la enfermera la confirma.
    evaluacion_id = evaluar(encuentro_id, categoria=2)
    confirmacion = cliente.put(f"/v1/encuentros/{encuentro_id}/categoria-final",
                               json={"categoriaEsi": 2},
                               headers={"X-Usuario": "enfermera-demo-1"})
    assert confirmacion.status_code == 200
    assert confirmacion.json()["origen"] == "confirmada_sugerencia_ia"

    # HU04 · El médico jefe la ve en la sala de espera, con su prioridad.
    [en_espera] = cliente.get("/v1/sala-de-espera").json()["pacientes"]
    assert (en_espera["encuentroId"], en_espera["nombre"], en_espera["categoriaEsi"]) == (
        encuentro_id, NOMBRE, 2)

    # HU05 · El worker lleva los eventos a la auditoría, y el auditor consulta la decisión.
    relay.procesar_pendientes()
    decision = cliente.get(f"/v1/auditoria/decisiones/{evaluacion_id}").json()
    assert (decision["pacienteRef"], decision["categoriaSugerida"],
            decision["categoriaFinal"], decision["confirmadaPor"]) == (
        paciente_id, 2, 2, "enfermera-demo-1")

    # La cadena de hashes de la auditoría está intacta y cubre todos los eventos del caso.
    with admin(BASE_AUDITORIA) as conexion:
        [(registros,)] = conexion.execute("SELECT count(*) FROM auditoria.registro").fetchall()
        [(primer_alterado,)] = conexion.execute(
            "SELECT auditoria.verificar_cadena()").fetchall()
    # verificar_cadena() devuelve la secuencia del primer registro alterado, o NULL si no hay.
    assert primer_alterado is None
    # patient.registered, vitals.captured, symptoms.reported, vitals.critical_detected,
    # triage.completed y triage.confirmed.
    assert registros == 6
