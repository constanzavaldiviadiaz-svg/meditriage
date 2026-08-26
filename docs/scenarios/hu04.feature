Feature: Ver pacientes priorizados

  Scenario: Ver pacientes ordenados
    Given que existen pacientes registrados
    When el personal de salud revisa la lista
    Then los pacientes aparecen ordenados por prioridad

  Scenario: Dos pacientes tienen la misma prioridad
    Given que existen dos pacientes con la misma prioridad
    When el personal de salud revisa la lista
    Then ambos pacientes aparecen con la misma prioridad

  Scenario: No existen pacientes registrados
    Given que no existen pacientes registrados
    When el personal de salud revisa la lista
    Then el sistema indica que no hay pacientes
