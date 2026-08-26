Feature: Revisar historial

  Scenario: Revisar recomendaciones realizadas
    Given que existen recomendaciones registradas
    When el auditor revisa el historial
    Then puede ver las recomendaciones realizadas

  Scenario: Revisar una recomendación por fecha
    Given que existe una recomendación registrada
    When el auditor revisa el historial
    Then puede ver la fecha de la recomendación

  Scenario: No existen recomendaciones
    Given que no existen recomendaciones registradas
    When el auditor revisa el historial
    Then el sistema indica que no hay registros
