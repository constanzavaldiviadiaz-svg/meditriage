# Bounded Contexts de MediTriage

## 1. Alcance

MediTriage se organiza mediante Bounded Contexts para separar las responsabilidades del dominio y mantener límites claros entre la información clínica, la identidad del paciente y la auditoría.

Los cuatro contextos identificados son:

- Clínico
- Identidad
- Auditoría
- Facturación

Para el alcance actual del producto se consideran dentro del sistema los contextos Clínico, Identidad y Auditoría.

El contexto de Facturación queda fuera del alcance actual, debido a que el backlog de MediTriage no contiene historias relacionadas con cobros, pagos o gestión de planes.

---

## 2. Contexto Clínico

### Propósito

El contexto Clínico representa la atención y el proceso de triaje del paciente.

Su responsabilidad es gestionar la información clínica necesaria para evaluar al paciente y determinar su categoría de prioridad.

### ¿Qué significa "Paciente"?

Dentro del contexto Clínico, un paciente es una persona que presenta signos vitales, síntomas y una categoría ESI como resultado del proceso de evaluación.

El contexto Clínico no necesita conocer directamente todos los datos de identidad de la persona.

### Vocabulario

- Paciente: persona evaluada durante el proceso de triaje.
- Signos vitales: mediciones clínicas utilizadas para evaluar al paciente.
- Síntomas: manifestaciones reportadas por el paciente.
- ESI: sistema utilizado para determinar la prioridad del paciente.
- Triaje: proceso de evaluación y clasificación de prioridad.
- Encuentro: instancia clínica asociada a la atención del paciente.

### Aggregate

El Aggregate principal es `encuentro`.

`encuentro` representa la instancia clínica en la que se registra y procesa la información necesaria para realizar el triaje.

---

## 3. Contexto de Identidad

### Propósito

El contexto de Identidad administra la información necesaria para identificar a una persona y gestionar los datos relacionados con su identidad y consentimiento.

### ¿Qué significa "Paciente"?

Dentro del contexto de Identidad, un paciente representa una persona cuyo RUT ha sido validado y que puede tener información relacionada con consentimiento y contactos.

El foco de este contexto es la identidad de la persona y no su evaluación clínica.

### Vocabulario

- Paciente: persona identificada dentro del sistema.
- RUT: identificador utilizado para validar la identidad de una persona.
- Consentimiento: autorización otorgada para el tratamiento de información.
- Contacto: información utilizada para comunicarse con la persona.
- Identidad: información que permite representar y validar a una persona.

### Aggregate

El Aggregate principal es `Person`.

`Person` representa la identidad de la persona dentro del contexto de Identidad.

---

## 4. Contexto de Auditoría

### Propósito

El contexto de Auditoría permite registrar las acciones y decisiones relevantes realizadas por el sistema, especialmente las relacionadas con las decisiones del motor de IA.

### ¿Qué significa "Paciente"?

Dentro del contexto de Auditoría, el paciente se representa mediante una referencia opaca.

No es necesario almacenar directamente información personal como el RUT para registrar una decisión.

### Vocabulario

- Decisión: resultado generado por el sistema o por el motor de IA.
- Auditoría: registro de una acción o decisión relevante.
- Decision ID: identificador de una decisión registrada.
- Referencia opaca: identificador que no contiene información personal directa.
- Trazabilidad: capacidad de conocer qué decisión ocurrió y cuándo ocurrió.

### Aggregate

El Aggregate principal es `AuditLog`.

`AuditLog` representa el registro de una acción o decisión que debe mantenerse para efectos de trazabilidad.

---

## 5. Contexto de Facturación

### Alcance

El contexto de Facturación queda fuera del alcance actual de MediTriage.

El backlog actual no contempla historias relacionadas con:

- Cobros.
- Pagos.
- Planes.
- Facturas.
- Gestión de cuentas.

Por esta razón, Facturación no forma parte de la implementación actual.

Si en el futuro MediTriage incorpora funcionalidades de pagos o gestión de planes, este contexto podría incorporarse como un Bounded Context independiente.

---

## 6. Context Map

La relación entre los contextos internos y los sistemas externos se puede representar de la siguiente manera:

```text
                         ┌─────────────────────┐
                         │    REGISTRO CIVIL   │
                         │       Externo       │
                         └──────────┬──────────┘
                                    │
                                    │ validación
                                    ▼
                         ┌─────────────────────┐
                         │     IDENTIDAD       │
                         │                     │
                         │       Person        │
                         └──────────┬──────────┘
                                    │
                                    │ identidad válida
                                    │ y consentimiento
                                    ▼
                         ┌─────────────────────┐
                         │       CLÍNICO       │
                         │                     │
                         │      encuentro      │
                         │                     │
                         │     Triaje / ESI    │
                         └──────────┬──────────┘
                                    │
                                    │ datos clínicos
                                    │ sin identificadores
                                    ▼
                         ┌─────────────────────┐
                         │    SERVICIO DE IA   │
                         │       Externo       │
                         └──────────┬──────────┘
                                    │
                                    │ sugerencia y
                                    │ justificación
                                    ▼
                         ┌─────────────────────┐
                         │      AUDITORÍA      │
                         │                     │
                         │      AuditLog       │
                         └─────────────────────┘


                         ┌─────────────────────┐
                         │    FACTURACIÓN      │
                         │                     │
                         │  Fuera del alcance  │
                         └─────────────────────┘
