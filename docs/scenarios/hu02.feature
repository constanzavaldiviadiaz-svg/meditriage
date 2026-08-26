Feature: Obtener la prioridad del paciente

  Scenario: Obtener una prioridad
    Given que los datos del paciente están ingresados
    When el sistema analiza sus síntomas y signos vitales
    Then muestra una prioridad de atención

  Scenario: Síntomas de prioridad alta
    Given que el paciente presenta síntomas graves
    When el sistema analiza sus datos
    Then asigna una prioridad alta

  Scenario: Datos insuficientes
    Given que faltan datos del paciente
    When el sistema intenta calcular la prioridad
    Then indica que no puede determinar la prioridad
