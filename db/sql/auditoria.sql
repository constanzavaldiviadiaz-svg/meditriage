-- Base de auditoría de MediTriage (ADR 0004, sección 5).
--
-- Cada decisión queda registrada y no se puede alterar durante 5 años. Tres capas lo
-- hacen cumplir dentro de la base:
--
--   1. Permisos: quien escribe solo puede insertar; quien audita solo puede leer.
--   2. Trigger: rechaza UPDATE, DELETE y TRUNCATE, venga de quien venga.
--   3. Cadena de hashes: cada registro guarda el hash del anterior. Alterar o borrar uno
--      rompe la cadena, y auditoria.verificar_cadena() dice dónde.
--
-- La cuarta capa, los respaldos WORM, es del servicio gestionado, no de este script.
--
-- Se ejecuta una vez, con un usuario administrador, conectado a la base de auditoría ya
-- creada. Las claves de los roles se asignan aparte: no van en el repositorio.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'auditoria_escritor') THEN
    CREATE ROLE auditoria_escritor LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'auditoria_lector') THEN
    CREATE ROLE auditoria_lector LOGIN;
  END IF;
END
$$;

CREATE SCHEMA auditoria;

CREATE TABLE auditoria.registro (
  -- Posición en la cadena. La asigna el trigger, no quien inserta.
  secuencia       bigint PRIMARY KEY,
  -- El mismo identificador del evento en la outbox: un evento repetido se descarta.
  evento_id       uuid NOT NULL UNIQUE,
  tipo            varchar(100) NOT NULL,
  version         varchar(10) NOT NULL,
  aggregate_id    uuid NOT NULL,
  trace_id        varchar(64) NOT NULL,
  -- Nunca RUT ni nombre: solo referencias opacas y datos ya enmascarados.
  payload         jsonb NOT NULL,
  -- Cuándo ocurrió el hecho, y cuándo llegó a la auditoría.
  creado_en       timestamptz NOT NULL,
  registrado_en   timestamptz NOT NULL,
  hash_anterior   char(64) NOT NULL,
  hash_integridad char(64) NOT NULL
);

-- El hash de un registro: su contenido completo más el hash del anterior. Las fechas se
-- escriben siempre en UTC, para que el resultado no dependa de la zona horaria de la sesión.
-- Para consultar las decisiones (HU05) sin recorrer toda la tabla: las evaluaciones se buscan
-- por tipo en orden de llegada, y sus confirmaciones por el encuentro al que pertenecen.
CREATE INDEX registro_tipo ON auditoria.registro (tipo, secuencia);
CREATE INDEX registro_aggregate ON auditoria.registro (aggregate_id);

CREATE FUNCTION auditoria.calcular_hash(r auditoria.registro) RETURNS char(64)
LANGUAGE sql STABLE
SET search_path = pg_catalog
AS $$
  SELECT encode(sha256(convert_to(concat_ws('|',
    r.hash_anterior, r.secuencia, r.evento_id, r.tipo, r.version, r.aggregate_id,
    r.trace_id, r.payload::text,
    to_char(r.creado_en AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    to_char(r.registrado_en AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
  ), 'UTF8')), 'hex')
$$;

-- Antes de cada INSERT: encadena el registro con el último. Se ejecuta con los permisos del
-- dueño de la tabla (SECURITY DEFINER), porque quien inserta no puede leer.
CREATE FUNCTION auditoria.encadenar() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, auditoria
AS $$
DECLARE
  ultimo auditoria.registro;
BEGIN
  -- Un registro a la vez: para encadenar hay que saber cuál es el último, y dos inserciones
  -- simultáneas lo leerían igual.
  PERFORM pg_advisory_xact_lock(hashtext('auditoria.registro'));
  SELECT * INTO ultimo FROM auditoria.registro ORDER BY secuencia DESC LIMIT 1;

  -- Lo que venga en estos campos se ignora: los calcula la base, no quien inserta.
  NEW.secuencia := coalesce(ultimo.secuencia, 0) + 1;
  NEW.hash_anterior := coalesce(ultimo.hash_integridad, repeat('0', 64));
  NEW.registrado_en := now();
  NEW.hash_integridad := auditoria.calcular_hash(NEW);
  RETURN NEW;
END
$$;

CREATE FUNCTION auditoria.rechazar_cambios() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'La auditoría es append-only: % no está permitido', TG_OP;
END
$$;

CREATE TRIGGER encadenar BEFORE INSERT ON auditoria.registro
  FOR EACH ROW EXECUTE FUNCTION auditoria.encadenar();

CREATE TRIGGER impedir_cambios BEFORE UPDATE OR DELETE ON auditoria.registro
  FOR EACH ROW EXECUTE FUNCTION auditoria.rechazar_cambios();

CREATE TRIGGER impedir_truncate BEFORE TRUNCATE ON auditoria.registro
  FOR EACH STATEMENT EXECUTE FUNCTION auditoria.rechazar_cambios();

-- Recorre la cadena y devuelve la secuencia del primer registro alterado, o NULL si está
-- intacta. Detecta un registro modificado, uno insertado a mano y un hueco por un borrado.
CREATE FUNCTION auditoria.verificar_cadena() RETURNS bigint
LANGUAGE plpgsql STABLE
SET search_path = pg_catalog, auditoria
AS $$
DECLARE
  r auditoria.registro;
  hash_esperado char(64) := repeat('0', 64);
  secuencia_esperada bigint := 1;
BEGIN
  FOR r IN SELECT * FROM auditoria.registro ORDER BY secuencia LOOP
    IF r.secuencia <> secuencia_esperada
       OR r.hash_anterior <> hash_esperado
       OR r.hash_integridad <> auditoria.calcular_hash(r) THEN
      RETURN r.secuencia;
    END IF;
    hash_esperado := r.hash_integridad;
    secuencia_esperada := secuencia_esperada + 1;
  END LOOP;
  RETURN NULL;
END
$$;

-- Permisos: nadie tiene UPDATE ni DELETE.
REVOKE ALL ON SCHEMA auditoria FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA auditoria FROM PUBLIC;

GRANT USAGE ON SCHEMA auditoria TO auditoria_escritor, auditoria_lector;
GRANT INSERT ON auditoria.registro TO auditoria_escritor;
GRANT SELECT ON auditoria.registro TO auditoria_lector;
GRANT EXECUTE ON FUNCTION auditoria.verificar_cadena(),
  auditoria.calcular_hash(auditoria.registro) TO auditoria_lector;
