"""Alertas de signos vitales (HU02).

Marcan los signos fuera de rango apenas la enfermera los registra, antes de cualquier
evaluación con IA. Son reglas fijas, sin modelo: lo que la enfermera ve no depende de un
servicio externo.

Hay dos niveles:

- **advertencia**: la zona de peligro de signos vitales del manual ESI (Emergency Severity
  Index, v4), que depende de la edad, más los umbrales de fiebre, saturación y presión alta.
- **critico**: valores que exigen atención inmediata.

Los umbrales son una decisión del #122 y los validan QA y la Product Owner. Sin edad conocida
se usan los de adulto: es el criterio más conservador para un paciente que no es niño.
"""

from dataclasses import dataclass

# Tramos de edad del manual ESI, en días: (desde, nombre, FC máxima, FR máxima).
TRAMOS = [
    (0, "< 3 meses", 180, 50),
    (90, "3 meses a 3 años", 160, 40),
    (1095, "3 a 8 años", 140, 30),
    (2920, "> 8 años", 100, 20),
]
ADULTO_DESDE_DIAS = 18 * 365

# Para todas las edades.
SATURACION_ADVERTENCIA = 92   # SatO2 < 92 %
SATURACION_CRITICA = 90       # SatO2 < 90 %
FIEBRE = 38                   # T >= 38 °C
HIPERTERMIA = 40              # T >= 40 °C
HIPOTERMIA = 35               # T < 35 °C
PAS_ALTA = 180                # PAS >= 180 mmHg
PAD_ALTA = 110                # PAD >= 110 mmHg

# Solo adultos.
PAS_BAJA = 90                 # PAS < 90 mmHg
FC_BAJA = 40                  # FC < 40 lpm
FC_ALTA = 150                 # FC > 150 lpm


@dataclass(frozen=True)
class Alerta:
    signo: str    # nombre del contrato, p. ej. "saturacion_oxigeno"
    valor: str    # lo medido, p. ej. "85" o "185/115"
    nivel: str    # "advertencia" o "critico"
    umbral: str   # la regla que la disparó, p. ej. "SatO2 < 90"


def _tramo(edad_dias):
    if edad_dias is None:
        return TRAMOS[-1]
    return [t for t in TRAMOS if edad_dias >= t[0]][-1]


def _es_adulto(edad_dias):
    return edad_dias is None or edad_dias >= ADULTO_DESDE_DIAS


def calcular_alertas(signos, edad_dias):
    """Las alertas de una medición. `signos` usa los nombres del contrato (SignosVitales).

    Una alerta por signo: si un valor cumple una regla de advertencia y una crítica, queda la
    crítica.
    """
    _, nombre_tramo, fc_maxima, fr_maxima = _tramo(edad_dias)
    adulto = _es_adulto(edad_dias)
    pas, pad = signos["presionSistolica"], signos["presionDiastolica"]
    fc, fr = signos["frecuenciaCardiaca"], signos.get("frecuenciaRespiratoria")
    temperatura, saturacion = signos["temperatura"], signos["saturacionOxigeno"]

    # Cada signo: (nombre, valor, [(se cumple, nivel, umbral), ...]), críticas primero.
    reglas = [
        ("presion_arterial", f"{pas}/{pad}", [
            (adulto and pas < PAS_BAJA, "critico", f"PAS < {PAS_BAJA} (adulto)"),
            (pas >= PAS_ALTA or pad >= PAD_ALTA, "advertencia",
             f"PAS >= {PAS_ALTA} o PAD >= {PAD_ALTA}"),
        ]),
        ("frecuencia_cardiaca", str(fc), [
            (adulto and (fc < FC_BAJA or fc > FC_ALTA), "critico",
             f"FC < {FC_BAJA} o > {FC_ALTA} (adulto)"),
            (fc > fc_maxima, "advertencia", f"FC > {fc_maxima} ({nombre_tramo})"),
        ]),
        ("frecuencia_respiratoria", str(fr), [
            (fr is not None and fr > fr_maxima, "advertencia",
             f"FR > {fr_maxima} ({nombre_tramo})"),
        ]),
        ("temperatura", str(temperatura), [
            (temperatura >= HIPERTERMIA, "critico", f"T >= {HIPERTERMIA}"),
            (temperatura < HIPOTERMIA, "critico", f"T < {HIPOTERMIA}"),
            (temperatura >= FIEBRE, "advertencia", f"T >= {FIEBRE}"),
        ]),
        ("saturacion_oxigeno", str(saturacion), [
            (saturacion < SATURACION_CRITICA, "critico", f"SatO2 < {SATURACION_CRITICA}"),
            (saturacion < SATURACION_ADVERTENCIA, "advertencia",
             f"SatO2 < {SATURACION_ADVERTENCIA}"),
        ]),
    ]

    alertas = []
    for signo, valor, condiciones in reglas:
        for se_cumple, nivel, umbral in condiciones:
            if se_cumple:
                alertas.append(Alerta(signo=signo, valor=valor, nivel=nivel, umbral=umbral))
                break
    return alertas
