"""Lo que se envía al motor de IA: solo datos clínicos despersonalizados (ADR 0008, G1).

Se envían la edad, el sexo, los signos vitales, el motivo y los síntomas. Nunca el RUT, el
nombre, la fecha de nacimiento ni ningún identificador. Los RUT que alguien haya escrito en el
texto libre se reemplazan por [RUT] antes de enviarlo.
"""

import re

# Un RUT con o sin puntos, con o sin guion: 12.345.678-5, 12345678-5, 9876543K.
_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b")


def borrar_rut(texto):
    return _RUT.sub("[RUT]", texto)


def edad_legible(edad_dias):
    """En días si es menor de 3 meses, en meses si es menor de 2 años, y en años en el resto: el
    protocolo ESI trata distinto a un recién nacido o a un lactante (ADR 0008)."""
    if edad_dias is None or edad_dias < 0:
        return "desconocida"
    if edad_dias < 90:
        return f"{edad_dias} días"
    if edad_dias < 730:
        return f"{edad_dias * 12 // 365} meses"   # meses cumplidos
    return f"{int(edad_dias / 365.25)} años"


def construir(datos):
    """La solicitud a partir de los últimos datos clínicos del encuentro."""
    return {
        "edad": edad_legible(datos["edad_dias"]),
        "sexo": datos["sexo"],
        "motivoConsulta": borrar_rut(datos["motivo"] or ""),
        "sintomas": [borrar_rut(s) for s in datos["sintomas"]],
        "signosVitales": datos["signos"],
    }
