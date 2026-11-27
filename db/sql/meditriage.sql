-- Base principal de MediTriage: contextos de identidad y clínico (ADR 0004).
--
-- La aplicación entra con el rol meditriage_app, que lee y escribe datos pero no puede
-- cambiar la estructura de las tablas.
--
-- Se ejecuta una vez, con un usuario administrador, conectado a la base principal ya
-- creada. La clave del rol se asigna aparte: no va en el repositorio.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'meditriage_app') THEN
    CREATE ROLE meditriage_app LOGIN;
  END IF;
END
$$;

-- ---------------------------------------------------------------- Contexto de identidad
-- El único lugar donde viven el RUT y el nombre. Los demás contextos guardan solo el
-- paciente_id.

CREATE SCHEMA identidad;

CREATE TYPE identidad.estado_consentimiento AS ENUM (
  'otorgado', 'exencion_emergencia_vital', 'rechazado'
);

CREATE TABLE identidad.paciente (
  paciente_id      uuid PRIMARY KEY,
  rut              varchar(10) NOT NULL UNIQUE,
  nombre           varchar(200) NOT NULL,
  fecha_nacimiento date,
  registrado_en    timestamptz NOT NULL
);

CREATE TABLE identidad.consentimiento (
  paciente_id   uuid PRIMARY KEY REFERENCES identidad.paciente,
  estado        identidad.estado_consentimiento NOT NULL,
  observacion   varchar(500),
  registrado_en timestamptz NOT NULL
);

-- Idempotencia de POST /v1/pacientes: qué respuesta corresponde a cada clave. Guarda el
-- hash del cuerpo, no el cuerpo, para no copiar el RUT y el nombre en otra tabla.
CREATE TABLE identidad.solicitud_registro (
  clave       uuid PRIMARY KEY,
  hash_cuerpo char(64) NOT NULL,
  paciente_id uuid NOT NULL REFERENCES identidad.paciente,
  creado_en   timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- Contexto clínico

CREATE SCHEMA clinico;

-- Patrón Outbox (ADR 0004, sección 3): el evento se guarda en la misma transacción que el
-- hecho que lo origina. El relay lo copia después a la auditoría y marca publicado_en.
CREATE TABLE clinico.outbox_evento (
  evento_id    uuid PRIMARY KEY,
  tipo         varchar(100) NOT NULL,
  version      varchar(10) NOT NULL,
  aggregate_id uuid NOT NULL,
  trace_id     varchar(64) NOT NULL,
  payload      jsonb NOT NULL,
  creado_en    timestamptz NOT NULL DEFAULT now(),
  publicado_en timestamptz
);

CREATE INDEX outbox_pendientes ON clinico.outbox_evento (creado_en)
  WHERE publicado_en IS NULL;

-- ---------------------------------------------------------------- Permisos

GRANT USAGE ON SCHEMA identidad, clinico TO meditriage_app;
GRANT SELECT, INSERT ON identidad.paciente, identidad.consentimiento,
  identidad.solicitud_registro TO meditriage_app;
GRANT SELECT, INSERT ON clinico.outbox_evento TO meditriage_app;
-- De un evento ya guardado solo se puede marcar que se publicó.
GRANT UPDATE (publicado_en) ON clinico.outbox_evento TO meditriage_app;
