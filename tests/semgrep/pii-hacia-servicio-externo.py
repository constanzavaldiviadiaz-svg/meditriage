# Casos de prueba de la regla meditriage-pii-hacia-servicio-externo.
# "ruleid" marca una línea que la regla debe detectar; "ok", una que debe dejar pasar.
import httpx


def casos(cliente, datos, signos, encuentro_id, rut, nombre):
    # ruleid: meditriage-pii-hacia-servicio-externo
    cliente.post("/evaluar", json={"rut": rut, "signos": signos})

    # ruleid: meditriage-pii-hacia-servicio-externo
    httpx.post("https://ia.example/evaluar", json={"nombre": nombre})

    # ruleid: meditriage-pii-hacia-servicio-externo
    cliente.post("/evaluar", json={"paciente": datos.rut, "signos": signos})

    # ruleid: meditriage-pii-hacia-servicio-externo
    cliente.get("/buscar", params=dict(rut=rut))

    # ok: meditriage-pii-hacia-servicio-externo
    cliente.post("/evaluar", json={"encuentroId": encuentro_id, "signos": signos})

    # ok: meditriage-pii-hacia-servicio-externo
    cliente.post("/evaluar", json={"motivoConsulta": datos.motivo_consulta})
