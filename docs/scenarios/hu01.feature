Feature: Ingresar datos del paciente

  Scenario: Ingreso correcto de datos
    Given que estoy en el formulario de registro
    When ingreso los datos válidos del paciente
    Then el sistema guarda los datos correctamente

  Scenario: Falta un dato obligatorio
    Given que estoy en el formulario de registro
    When dejo un dato obligatorio vacío
    Then el sistema me indica que falta completar ese dato

  Scenario: RUT inválido
    Given que estoy en el formulario de registro
    When ingreso un RUT inválido
    Then el sistema me indica que el RUT no es válido
