Feature: Registro de paciente y consentimiento informado
  Como enfermera de triage
  Quiero registrar a un paciente con su RUT y consentimiento informado
  Para iniciar de forma legal y segura su proceso de evaluacion clinica

  Scenario: Registro exitoso de paciente con consentimiento firmado
    Given un paciente que otorga su consentimiento informado
    When la enfermera de triage ingresa un RUT chileno valido "12.345.678-9" y sus datos personales
    Then el sistema registra al paciente exitosamente
    And la decision queda registrada en el audit log

  Scenario: Registro de paciente inconsciente o imposibilitado de firmar
    Given un paciente en estado critico que no puede otorgar consentimiento
    When la enfermera de triage marca la casilla de exencion por emergencia vital
    Then el sistema permite el registro provisorio del paciente
    And se registra la exencion de consentimiento en el audit log

  Scenario: Intento de registro con RUT invalido
    Given un paciente que presenta un documento con formato incorrecto
    When la enfermera de triage ingresa el RUT "12.345.678-K" con digito verificador erróneo
    Then el sistema rechaza el registro mostrando un mensaje de error de validacion
    And no se crea ninguna ficha de paciente en el sistema
