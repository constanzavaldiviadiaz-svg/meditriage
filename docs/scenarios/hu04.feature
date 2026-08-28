Feature: Tablero de priorizacion dinamica
  Como medico jefe de turno
  Quiero visualizar el tablero de pacientes ordenado dinamicamente
  Para gestionar los tiempos de espera y la capacidad de la sala de urgencia

  Scenario: Visualizacion de pacientes ordenados por categoria ESI
    Given una sala de espera con multiples pacientes categorizados
    When el medico jefe de turno accede al tablero de control
    Then los pacientes se muestran priorizados de categoria ESI "1" a ESI "5"
    And los casos de mayor gravedad encabezan la lista de atencion

  Scenario: Reordenamiento dinamico por reevaluacion de paciente
    Given un paciente registrado con categoria ESI "3" en sala de espera
    When la enfermera actualiza sus signos vitales a estado critico y pasa a categoria ESI "2"
    Then el tablero del medico jefe se actualiza automaticamente en tiempo real
    And el paciente sube de posicion en la lista de espera

  Scenario: Desconexion del servicio en tiempo real del tablero
    Given el medico jefe de turno monitoreando el tablero activo
    When se pierde la conexion con el servidor WebSocket del tablero
    Then el sistema despliega un aviso de advertencia de datos no actualizados
    And reintenta la reconexion automatica sin cerrar la sesion
