Feature: Ingreso de sintomas y signos vitales
  Como enfermera de triage
  Quiero ingresar los sintomas y signos vitales del paciente
  Para que el sistema recopile la informacion necesaria para la categorizacion

  Scenario: Ingreso completo de signos vitales dentro de rangos normales
    Given un paciente previamente registrado
    When la enfermera de triage ingresa la presion, frecuencia cardiaca, saturacion y sintomas
    Then el sistema valida la coherencia de todos los datos ingresados
    And guarda los signos vitales asociados a la consulta del paciente

  Scenario: Ingreso con signos vitales en limites criticos
    Given un paciente previamente registrado
    When la enfermera de triage ingresa una saturacion de oxigeno del 85%
    Then el sistema genera una alerta visual de valor critico
    And permite continuar con el proceso de categorizacion inmediata

  Scenario: Omision de campos obligatorios en el formulario
    Given un paciente previamente registrado
    When la enfermera de triage intenta enviar el formulario sin ingresar los sintomas principales
    Then el sistema bloquea el envio destacando los campos requeridos faltantes
    And no se envia la informacion al motor de evaluacion
