# Escenarios Gherkin — MediTriage

## HU01 — Registrar información del paciente

### Escenario 1
**Dado** que el personal de salud está registrando un paciente  
**Cuando** ingresa los síntomas y signos vitales  
**Entonces** el sistema guarda la información.

### Escenario 2
**Dado** que falta un dato obligatorio  
**Cuando** el personal intenta guardar la información  
**Entonces** el sistema indica que debe completar el dato.

### Escenario 3
**Dado** que todos los datos están completos  
**Cuando** el personal guarda la información  
**Entonces** el paciente queda registrado.

---

## HU02 — Obtener prioridad

### Escenario 1
**Dado** que los datos del paciente están registrados  
**Cuando** el sistema analiza la información  
**Entonces** entrega un nivel de prioridad.

### Escenario 2
**Dado** que el paciente tiene síntomas de mayor gravedad  
**Cuando** la IA analiza sus datos  
**Entonces** asigna una prioridad más alta.

### Escenario 3
**Dado** que la información está incompleta  
**Cuando** se intenta obtener la prioridad  
**Entonces** el sistema solicita completar los datos.

---

## HU03 — Ver explicación

### Escenario 1
**Dado** que el sistema entregó una prioridad  
**Cuando** el personal revisa el resultado  
**Entonces** puede ver una explicación.

### Escenario 2
**Dado** que existen datos que influyeron en la prioridad  
**Cuando** el personal revisa la explicación  
**Entonces** puede identificar esos datos.

### Escenario 3
**Dado** que la prioridad fue calculada  
**Cuando** el personal consulta el resultado  
**Entonces** la explicación aparece junto a la prioridad.

---

## HU04 — Ver pacientes priorizados

### Escenario 1
**Dado** que existen pacientes registrados  
**Cuando** el personal abre la lista de pacientes  
**Entonces** los puede ver ordenados por prioridad.

### Escenario 2
**Dado** que existen pacientes con diferentes prioridades  
**Cuando** se muestra la lista  
**Entonces** los pacientes con mayor urgencia aparecen primero.

### Escenario 3
**Dado** que un nuevo paciente recibe una prioridad  
**Cuando** se actualiza la lista  
**Entonces** aparece en el lugar correspondiente.

---

## HU05 — Revisar historial

### Escenario 1
**Dado** que existen recomendaciones realizadas  
**Cuando** el auditor revisa el historial  
**Entonces** puede ver las recomendaciones.

### Escenario 2
**Dado** que una recomendación fue realizada  
**Cuando** se consulta el historial  
**Entonces** se muestra la fecha de la recomendación.

### Escenario 3
**Dado** que existen varias recomendaciones  
**Cuando** el auditor consulta el historial  
**Entonces** puede revisar las recomendaciones realizadas.
