# Casos de prueba de la regla meditriage-pii-en-logs.
# "ruleid" marca una línea que la regla debe detectar; "ok", una que debe dejar pasar.
import logging

logger = logging.getLogger(__name__)


def casos(datos, paciente, rut, nombre):
    # ruleid: meditriage-pii-en-logs
    print(datos.rut)

    # ruleid: meditriage-pii-en-logs
    logger.info("Registrando paciente %s", datos.rut)

    # ruleid: meditriage-pii-en-logs
    logging.warning(f"Paciente {nombre} sin consentimiento")

    # ruleid: meditriage-pii-en-logs
    logger.error("RUT inválido: " + rut)

    # ok: meditriage-pii-en-logs
    logger.info("Paciente registrado: %s", paciente.pacienteId)

    # ok: meditriage-pii-en-logs
    logger.info("RUT recibido: %s", enmascarar_rut(datos.rut))

    # ok: meditriage-pii-en-logs
    print(paciente.rutEnmascarado)

    # ok: meditriage-pii-en-logs
    lista = [datos.rut]
    lista.append(datos.nombre)


def enmascarar_rut(rut):
    return rut
