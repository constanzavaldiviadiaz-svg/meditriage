Feature: Derivacion a triage manual ante fallo o demora del motor de IA
  Como enfermera de triage
  Quiero que el caso pase a triage manual cuando el motor de IA no responde a tiempo
  Para seguir atendiendo sin quedar bloqueada esperando una respuesta que no llega

  Scenario: El motor de IA supera el limite de 3 segundos
    Given un paciente con sus sintomas y signos vitales ya ingresados
    When el motor de IA no entrega una respuesta dentro de 3 segundos
    Then el sistema cancela la espera y deriva el caso a triage manual
    And notifica a la enfermera de triage que debe evaluar sin apoyo de IA
    And registra el tiempo de espera agotado en el audit log

  Scenario: El motor de IA responde justo dentro del limite
    Given un paciente con sus sintomas y signos vitales ya ingresados
    When el motor de IA entrega la sugerencia a los 2,8 segundos
    Then el sistema muestra la categoria ESI sugerida con su justificacion
    And no se activa la derivacion a triage manual

  Scenario: El servicio de IA esta caido
    Given un paciente con sus sintomas y signos vitales ya ingresados
    When el sistema no logra establecer conexion con el motor de IA
    Then el caso se deriva a triage manual sin esperar el limite de 3 segundos
    And se genera una alerta al equipo de plataforma
    And se registra la indisponibilidad del servicio en el audit log
