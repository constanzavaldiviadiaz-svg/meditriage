"""Validación y enmascaramiento del RUT chileno."""


def calcular_digito_verificador(numero: str) -> str:
    """Calcula el dígito verificador de un RUT con el algoritmo módulo 11.

    1. Se recorren los dígitos de derecha a izquierda.
    2. Cada uno se multiplica por 2, 3, 4, 5, 6, 7, y se vuelve a empezar en 2.
    3. Se suman los resultados.
    4. El dígito es 11 menos el resto de dividir esa suma por 11.
       Si da 11, el dígito es "0". Si da 10, es "K".

    Ejemplo con 12345678:  8·2 + 7·3 + 6·4 + 5·5 + 4·6 + 3·7 + 2·2 + 1·3 = 138
                           138 % 11 = 6   →   11 - 6 = 5   →   dígito "5"
    """
    suma = 0
    multiplicador = 2
    for digito in reversed(numero):
        suma += int(digito) * multiplicador
        multiplicador = multiplicador + 1 if multiplicador < 7 else 2

    resultado = 11 - (suma % 11)
    if resultado == 11:
        return "0"
    if resultado == 10:
        return "K"
    return str(resultado)


def es_rut_valido(rut: str) -> bool:
    """Indica si el dígito verificador corresponde al número.

    Recibe el formato del contrato: "12345678-5". El formato en sí (dígitos, guion) ya lo
    revisó el schema antes de llegar aquí; esta función revisa la matemática.
    """
    numero, digito = rut.split("-")
    return calcular_digito_verificador(numero) == digito.upper()


def enmascarar_rut(rut: str) -> str:
    """Oculta los dígitos centrales: "12345678-5" → "12.***.***-5".

    La API nunca devuelve el RUT completo: quien lo envió ya lo conoce (Ley 19.628).
    """
    numero, digito = rut.split("-")
    inicio = numero[:-6]  # los 1 o 2 primeros dígitos, según el largo del RUT
    return f"{inicio}.***.***-{digito.upper()}"
