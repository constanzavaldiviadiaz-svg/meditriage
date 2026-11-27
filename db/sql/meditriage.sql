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
  sexo             varchar(10),
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

-- Encuentro: una visita del paciente a la sala de espera, de la llegada a la atención (HU02).
-- Guarda el paciente_id y no el RUT ni el nombre: esos viven solo en el contexto de identidad.
-- La edad (en días) y el sexo son una foto tomada al abrir el encuentro, para que la
-- evaluación no tenga que consultar el contexto de identidad dentro de los 3 segundos.
CREATE TYPE clinico.estado_encuentro AS ENUM (
  'abierto', 'en_espera', 'evaluado', 'derivado_triage_manual', 'confirmado', 'atendido'
);

CREATE TABLE clinico.encuentro (
  encuentro_id    uuid PRIMARY KEY,
  paciente_id     uuid NOT NULL,
  estado          clinico.estado_encuentro NOT NULL,
  abierto_en      timestamptz NOT NULL,
  cerrado_en      timestamptz,
  -- Nullable: el encuentro se abre antes de registrar los datos clínicos.
  motivo_consulta varchar(500),
  edad_dias       integer,
  sexo            varchar(10)
);

-- Un paciente tiene a lo sumo un encuentro sin atender. Dos aperturas simultáneas (dos
-- enfermeras, dos réplicas) dejan uno solo.
CREATE UNIQUE INDEX un_encuentro_activo ON clinico.encuentro (paciente_id)
  WHERE estado <> 'atendido';

-- Idempotencia de POST /v1/encuentros, igual que en el registro de pacientes.
CREATE TABLE clinico.solicitud_encuentro (
  clave        uuid PRIMARY KEY,
  hash_cuerpo  char(64) NOT NULL,
  encuentro_id uuid NOT NULL REFERENCES clinico.encuentro,
  creado_en    timestamptz NOT NULL DEFAULT now()
);

-- Datos clínicos (HU02). Cada PUT agrega una medición nueva de signos vitales: quedan todas,
-- para la reevaluación. Los síntomas se reemplazan.
CREATE TABLE clinico.signos_vitales (
  signos_vitales_id       uuid PRIMARY KEY,
  encuentro_id            uuid NOT NULL REFERENCES clinico.encuentro,
  presion_sistolica       smallint NOT NULL,
  presion_diastolica      smallint NOT NULL,
  frecuencia_cardiaca     smallint NOT NULL,
  frecuencia_respiratoria smallint,
  temperatura             numeric(4, 1) NOT NULL,
  saturacion_oxigeno      smallint NOT NULL,
  medido_en               timestamptz NOT NULL
);

CREATE TABLE clinico.sintoma (
  sintoma_id   uuid PRIMARY KEY,
  encuentro_id uuid NOT NULL REFERENCES clinico.encuentro,
  descripcion  varchar(200) NOT NULL
);

-- Las alertas que vio la enfermera, con el umbral vigente en ese momento: si los umbrales
-- cambian, la historia no se reescribe.
CREATE TABLE clinico.alerta_signo_vital (
  alerta_id         uuid PRIMARY KEY,
  signos_vitales_id uuid NOT NULL REFERENCES clinico.signos_vitales,
  signo             varchar(30) NOT NULL,
  valor             varchar(20) NOT NULL,
  nivel             varchar(15) NOT NULL,
  umbral            varchar(60) NOT NULL
);

-- Evaluación: la sugerencia del motor de IA o la derivación a triage manual (HU03, HU06).
-- Guarda la respuesta exacta del modelo, porque no es determinista: la auditoría tiene que
-- poder mostrar lo mismo que vio la enfermera (ADR 0002).
CREATE TABLE clinico.evaluacion (
  evaluacion_id         uuid PRIMARY KEY,
  encuentro_id          uuid NOT NULL REFERENCES clinico.encuentro,
  resultado             varchar(30) NOT NULL,
  categoria_sugerida    smallint,
  justificacion         jsonb,
  motivo_derivacion     varchar(30),
  duracion_ms           integer NOT NULL,
  modelo                varchar(100),
  version_prompt        varchar(30),
  respuesta_ia_original text,
  generada_en           timestamptz NOT NULL,
  trace_id              varchar(64)
);

-- Idempotencia de POST /v1/encuentros/{id}/evaluaciones: la misma clave devuelve la misma
-- evaluación, sin volver a llamar a la IA.
CREATE TABLE clinico.solicitud_evaluacion (
  clave         uuid PRIMARY KEY,
  encuentro_id  uuid NOT NULL REFERENCES clinico.encuentro,
  evaluacion_id uuid NOT NULL REFERENCES clinico.evaluacion,
  creado_en     timestamptz NOT NULL DEFAULT now()
);

-- Categoría final: la decide la enfermera, no la IA (HU03). Una por encuentro; si se vuelve a
-- confirmar, se reemplaza, y cada confirmación queda en la auditoría por su evento.
-- confirmada_por es una referencia opaca a quien confirmó, nunca su nombre ni su RUT (R1).
CREATE TABLE clinico.categoria_final (
  encuentro_id         uuid PRIMARY KEY REFERENCES clinico.encuentro,
  evaluacion_id        uuid NOT NULL REFERENCES clinico.evaluacion,
  categoria_esi        smallint NOT NULL CHECK (categoria_esi BETWEEN 1 AND 5),
  origen               varchar(30) NOT NULL,
  justificacion_cambio varchar(1000),
  confirmada_por       varchar(64),
  confirmada_en        timestamptz NOT NULL
);

-- ---------------------------------------------------------------- Permisos

GRANT USAGE ON SCHEMA identidad, clinico TO meditriage_app;
GRANT SELECT, INSERT ON identidad.paciente, identidad.consentimiento,
  identidad.solicitud_registro TO meditriage_app;
GRANT SELECT, INSERT ON clinico.outbox_evento TO meditriage_app;
-- De un evento ya guardado solo se puede marcar que se publicó.
GRANT UPDATE (publicado_en) ON clinico.outbox_evento TO meditriage_app;
GRANT SELECT, INSERT ON clinico.encuentro, clinico.solicitud_encuentro TO meditriage_app;
-- Del encuentro solo cambian el estado y el motivo de consulta.
GRANT UPDATE (estado, motivo_consulta) ON clinico.encuentro TO meditriage_app;
GRANT SELECT, INSERT ON clinico.signos_vitales, clinico.sintoma, clinico.alerta_signo_vital
  TO meditriage_app;
-- Los síntomas se reemplazan en cada registro de datos clínicos.
GRANT DELETE ON clinico.sintoma TO meditriage_app;
GRANT SELECT, INSERT ON clinico.evaluacion TO meditriage_app;
GRANT SELECT, INSERT, UPDATE ON clinico.categoria_final TO meditriage_app;
GRANT SELECT, INSERT ON clinico.solicitud_evaluacion TO meditriage_app;
