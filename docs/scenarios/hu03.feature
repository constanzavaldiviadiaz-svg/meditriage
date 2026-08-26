Feature: Explicar la prioridad del paciente

  Scenario: Mostrar explicación de la prioridad
    Given que el sistema asignó una prioridad al paciente
    When reviso el resultado
    Then el sistema muestra por qué se asignó esa prioridad

  Scenario: La prioridad cambia
    Given que cambian los datos del paciente
    When el sistema vuelve a analizar la información
    Then muestra una nueva explicación de la prioridad

  Scenario: No hay información suficiente
    Given que faltan datos para explicar la prioridad
    When reviso el resultado
    Then el sistema indica que no puede explicar la prioridad
