Feature: Registro inmutable y auditoria de decisiones
  Como auditor clinico
  Quiero consultar el historial inmutable de las decisiones de triage
  Para evaluar el cumplimiento de protocolos y respaldar auditorias legales

  Scenario: Consulta de trazabilidad completa de una evaluacion
    Given un proceso de triage finalizado hace 6 meses
    When el auditor clinico busca el registro mediante el identificador unico
    Then el sistema muestra los datos ingresados, sugerencia ESI, decision final y explicacion
    And confirma la firma digital de inmutabilidad del audit log

  Scenario: Filtrado de auditoria por rango de fechas extenso
    Given un volumen de 50.000 registros almacenados en el ultimo ano
    When el auditor clinico aplica un filtro por rango de fechas de los ultimos 3 meses
    Then el sistema entrega la lista filtrada resguardando la enmascaracion de PII
    And exporta el reporte manteniendo los registros de integridad

  Scenario: Intento de consulta sin credenciales o permisos de auditoria
    Given un usuario autenticado con rol de enfermera de triage
    When intenta acceder al modulo de consulta inmutable del audit log
    Then el sistema deniega el acceso por falta de privilegios
    And registra el intento de acceso no autorizado en el log de seguridad
