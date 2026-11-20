# Catálogo de Eventos de Dominio - MediTriage

Este catálogo define los eventos de dominio que ocurren en el sistema. Todos los eventos representan hechos inmutables que ya sucedieron (`recurso.accion.pasado`), incluyen `version` y `trace_id`, y deben ser consumidos bajo el principio **at-least-once** (requiriendo **idempotencia por `event_id`** en los consumidores).

---

## Esquema Base de Eventos

Todos los eventos del sistema extienden la siguiente estructura común:

```json
{
  "event_id": "uuid-v4",
  "event_type": "nombre.del.evento.pasado",
  "version": "1.0",
  "timestamp": "ISO-8601 UTC",
  "trace_id": "uuid-v4-para-trazabilidad",
  "producer": "nombre-del-contenedor-productor",
  "data": {}
}
