"""Relay: lleva los eventos de la outbox a la base de auditoría (ADR 0004).

Es el worker del ADR 0004: corre como un proceso aparte, con la misma imagen que la API y
otro comando:

    python -m src.auditoria.relay

Así la escritura de la auditoría es asíncrona (ADR 0002) y no consume el presupuesto de
3 segundos. Y solo el worker tiene la credencial de auditoría: la API no la recibe, de modo
que quien la comprometa no puede insertar registros falsos (amenaza S3 del threat model).

Entrega al menos una vez. Si el relay se cae después de escribir en la auditoría y antes de
marcar la outbox, el evento se vuelve a enviar, y la auditoría descarta el repetido porque
`evento_id` es único. Si la base de auditoría no responde, los eventos esperan en la outbox.

Se pueden correr varias réplicas del worker. `FOR UPDATE SKIP LOCKED` reparte los eventos:
dos réplicas nunca toman el mismo.

Simplificación consciente: en el ADR 0004 el relay publica los eventos en Redis Streams y el
worker los escribe en la auditoría. Mientras no exista el tablero en tiempo real, que es lo
que necesita Redis, el relay escribe directo en la auditoría. La outbox, el worker y sus
garantías no cambian.
"""

import logging
import signal
import threading

from psycopg.types.json import Jsonb

from src import bd, config

log = logging.getLogger(__name__)

LOTE = 100


def procesar_pendientes(limite=LOTE):
    """Copia hasta `limite` eventos pendientes a la auditoría. Devuelve cuántos procesó."""
    with bd.principal() as principal:
        eventos = principal.execute(
            "SELECT evento_id, tipo, version, aggregate_id, trace_id, payload, creado_en"
            " FROM clinico.outbox_evento WHERE publicado_en IS NULL"
            " ORDER BY creado_en LIMIT %s FOR UPDATE SKIP LOCKED",
            (limite,),
        ).fetchall()
        if not eventos:
            return 0

        with bd.auditoria() as auditoria, auditoria.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO auditoria.registro"
                " (evento_id, tipo, version, aggregate_id, trace_id, payload, creado_en)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)"
                # Sin nombrar la columna: con una columna, PostgreSQL exige permiso de lectura,
                # y el rol de la aplicación solo puede insertar.
                " ON CONFLICT DO NOTHING",
                [(*evento[:5], Jsonb(evento[5]), evento[6]) for evento in eventos],
            )

        principal.execute(
            "UPDATE clinico.outbox_evento SET publicado_en = now() WHERE evento_id = ANY(%s)",
            ([evento[0] for evento in eventos],),
        )
    return len(eventos)


class Relay:
    """Ejecuta `procesar_pendientes()` cada `intervalo` segundos, hasta que se le ordena
    detenerse."""

    def __init__(self, intervalo=1.0):
        self.intervalo = intervalo
        self._detener = threading.Event()
        self._hilo = None

    def iniciar(self):
        """Corre en un hilo aparte. Lo usan las pruebas."""
        self._hilo = threading.Thread(target=self.ejecutar, name="relay", daemon=True)
        self._hilo.start()

    def corriendo(self):
        return self._hilo is not None and self._hilo.is_alive()

    def detener(self):
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=5)

    def ejecutar(self):
        """Corre en el hilo actual hasta que alguien llame a `detener()`."""
        while not self._detener.wait(self.intervalo):
            try:
                # Si hay más de un lote pendiente, sigue hasta vaciar la outbox.
                while procesar_pendientes() == LOTE:
                    pass
            except Exception as error:
                # Solo el tipo de error: el mensaje de la base puede traer datos.
                # Los eventos siguen en la outbox y se reintentan en la próxima vuelta.
                log.warning("No se pudo auditar los eventos pendientes: %s",
                            type(error).__name__)


def main():
    """Punto de entrada del worker. Kubernetes lo detiene con SIGTERM: termina la vuelta en
    curso y sale. Si muriera a mitad de camino, no se pierde nada: los eventos siguen en la
    outbox."""
    logging.basicConfig(level=logging.INFO)
    worker = Relay(config.INTERVALO_RELAY)
    signal.signal(signal.SIGTERM, lambda *_: worker.detener())
    log.info("Relay de auditoría iniciado")
    worker.ejecutar()
    bd.cerrar()


if __name__ == "__main__":
    main()
