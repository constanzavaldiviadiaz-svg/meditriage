Feature: Recomendacion de prioridad ESI y explicacion por IA
  Como enfermera de triage
  Quiero recibir una sugerencia de categoria ESI con su justificacion
  Para asignar la prioridad clinica adecuada con apoyo de inteligencia artificial

  Scenario: Sugerencia exitosa de categoria ESI con explicacion
    Given los signos vitales y sintomas de un paciente ingresados
    When el motor de IA procesa la informacion clinica
    Then se asigna categoria ESI "2" junto con la explicacion de los factores de riesgo
    And la recomendacion de IA queda registrada en el audit log

  Scenario: Discordancia entre la sugerencia de IA y el criterio de la enfermera
    Given una recomendacion de categoria ESI "4" entregada por el motor de IA
    When la enfermera de triage sobreescribe manualmente la recomendacion a categoria ESI "3"
    Then el sistema solicita obligatoriamente una justificacion clinica del cambio
    And registra la sobreescritura y el motivo en el audit log

  Scenario: Fallo de estructura en la respuesta del modelo de IA
    Given los datos del paciente enviados al motor de IA
    When el servicio de IA retorna una respuesta malformada o incomprensible
    Then el sistema notifica el error de procesamiento
    And deriva el caso a evaluacion clinica manual sin recomendacion automatica
