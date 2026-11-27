"""Datos clínicos de un encuentro: signos vitales, síntomas y alertas (HU02).

Todo se guarda en una transacción, junto con sus eventos en la outbox: o queda todo o no
queda nada.
"""

from datetime import UTC, datetime
from uuid import uuid4

from src import bd
from src.auditoria.eventos import encolar
from src.evaluacion import encuentros
from src.evaluacion.alertas import calcular_alertas
from src.evaluacion.modelos import AlertaSignoVital, DatosClinicos


def registrar(encuentro, datos, trace_id):
    """Guarda una medición nueva con sus alertas, reemplaza el motivo y los síntomas, y deja
    el encuentro en espera de la evaluación.

    `datos` ya viene revisado por la ruta: trae el motivo y los cinco signos obligatorios.
    """
    signos = datos.signosVitales.model_dump()
    alertas = calcular_alertas(signos, encuentro.edad_dias)
    signos_id = uuid4()
    ahora = datetime.now(UTC)

    with bd.principal() as conexion:
        conexion.execute(
            "INSERT INTO clinico.signos_vitales (signos_vitales_id, encuentro_id,"
            " presion_sistolica, presion_diastolica, frecuencia_cardiaca,"
            " frecuencia_respiratoria, temperatura, saturacion_oxigeno, medido_en)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (signos_id, encuentro.encuentro_id, signos["presionSistolica"],
             signos["presionDiastolica"], signos["frecuenciaCardiaca"],
             signos["frecuenciaRespiratoria"], signos["temperatura"],
             signos["saturacionOxigeno"], ahora),
        )
        for alerta in alertas:
            conexion.execute(
                "INSERT INTO clinico.alerta_signo_vital"
                " (alerta_id, signos_vitales_id, signo, valor, nivel, umbral)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (uuid4(), signos_id, alerta.signo, alerta.valor, alerta.nivel, alerta.umbral),
            )
        conexion.execute(
            "UPDATE clinico.encuentro SET motivo_consulta = %s WHERE encuentro_id = %s",
            (datos.motivoConsulta.strip(), encuentro.encuentro_id),
        )
        conexion.execute("DELETE FROM clinico.sintoma WHERE encuentro_id = %s",
                         (encuentro.encuentro_id,))
        for sintoma in datos.sintomas:
            conexion.execute(
                "INSERT INTO clinico.sintoma (sintoma_id, encuentro_id, descripcion)"
                " VALUES (%s, %s, %s)",
                (uuid4(), encuentro.encuentro_id, sintoma),
            )
        encuentros.cambiar_estado(conexion, encuentro.encuentro_id, "en_espera")
        _encolar_eventos(conexion, encuentro.encuentro_id, signos_id, ahora,
                         len(datos.sintomas), alertas, trace_id)

    return DatosClinicos(
        encuentroId=encuentro.encuentro_id,
        registradoEn=ahora,
        alertas=[AlertaSignoVital(signo=a.signo, valor=a.valor, nivel=a.nivel)
                 for a in alertas],
    )


def _encolar_eventos(conexion, encuentro_id, signos_id, medido_en, cantidad_sintomas,
                     alertas, trace_id):
    """Los eventos del catálogo (docs/data/event-catalog.md). Ninguno lleva el texto libre del
    motivo ni de los síntomas: podría traer un nombre."""
    encuentro = str(encuentro_id)
    encolar(conexion, "vitals.captured", encuentro_id, trace_id,
            {"encuentroId": encuentro, "signosVitalesId": str(signos_id),
             "medidoEn": medido_en.isoformat()})
    encolar(conexion, "symptoms.reported", encuentro_id, trace_id,
            {"encuentroId": encuentro, "cantidadSintomas": cantidad_sintomas})
    # Solo las críticas: es lo que dice el nombre del evento. Las advertencias quedan en la
    # tabla de alertas.
    for alerta in alertas:
        if alerta.nivel == "critico":
            encolar(conexion, "vitals.critical_detected", encuentro_id, trace_id,
                    {"encuentroId": encuentro, "signo": alerta.signo, "nivel": alerta.nivel,
                     "umbralAplicado": alerta.umbral})


_SIGNOS = ("presionSistolica", "presionDiastolica", "frecuenciaCardiaca",
           "frecuenciaRespiratoria", "temperatura", "saturacionOxigeno")


def ultimos(encuentro_id):
    """Lo que la evaluación necesita: la edad y el sexo del encuentro, el motivo, los síntomas y
    la última medición. None si todavía no tiene datos clínicos."""
    with bd.principal() as conexion:
        encuentro = conexion.execute(
            "SELECT edad_dias, sexo, motivo_consulta FROM clinico.encuentro"
            " WHERE encuentro_id = %s", (encuentro_id,)).fetchone()
        signos = conexion.execute(
            "SELECT presion_sistolica, presion_diastolica, frecuencia_cardiaca,"
            " frecuencia_respiratoria, temperatura, saturacion_oxigeno"
            " FROM clinico.signos_vitales WHERE encuentro_id = %s"
            " ORDER BY medido_en DESC LIMIT 1", (encuentro_id,)).fetchone()
        sintomas = conexion.execute(
            "SELECT descripcion FROM clinico.sintoma WHERE encuentro_id = %s",
            (encuentro_id,)).fetchall()
    if encuentro is None or signos is None:
        return None
    edad_dias, sexo, motivo = encuentro
    return {
        "edad_dias": edad_dias,
        "sexo": sexo,
        "motivo": motivo,
        "sintomas": [s for (s,) in sintomas],
        "signos": {nombre: (float(v) if nombre == "temperatura" and v is not None else v)
                   for nombre, v in zip(_SIGNOS, signos, strict=True)},
    }
