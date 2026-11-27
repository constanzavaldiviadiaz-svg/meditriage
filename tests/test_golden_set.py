"""Pruebas del golden set de la IA (#124).

No llaman a la IA ni gastan créditos. Revisan que el conjunto de casos esté completo y bien
formado, para que la medición del ADR 0008 (punto 2) mida lo que dice medir: si faltan casos
graves, la regla "ningún ESI 1 o 2 sugerido como leve" no prueba nada; si falta un grupo de
edad, no hay con qué medir fairness.

Los rangos de los signos vitales se leen del contrato (api/openapi.yaml), que es la fuente de
verdad: un caso que el contrato rechazaría no puede estar en el golden set.
"""

import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent

CASOS = yaml.safe_load((RAIZ / "ia/golden-set.yaml").read_text(encoding="utf-8"))
ESQUEMAS = yaml.safe_load((RAIZ / "api/openapi.yaml").read_text(encoding="utf-8"))["components"][
    "schemas"
]
SIGNOS = ESQUEMAS["SignosVitales"]
DATOS_CLINICOS = ESQUEMAS["DatosClinicosInput"]

CLINICOS = [caso for caso in CASOS if caso["tipo"] == "clinico"]
INYECCION = [caso for caso in CASOS if caso["tipo"] == "inyeccion"]

RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")


def grupo_de_edad(edad):
    """Niños hasta los 14 años, adultos de 15 a 64, mayores desde los 65."""
    if edad["unidad"] != "años" or edad["valor"] < 15:
        return "niño"
    return "adulto" if edad["valor"] < 65 else "mayor"


def por_caso(prueba):
    return pytest.mark.parametrize("caso", CASOS, ids=[caso["id"] for caso in CASOS])(prueba)


# --- El conjunto completo ---------------------------------------------------------------


def test_hay_al_menos_30_casos_clinicos():
    assert len(CLINICOS) >= 30


def test_estan_los_cinco_niveles_esi():
    assert {caso["esiEsperado"] for caso in CLINICOS} == {1, 2, 3, 4, 5}


def test_hay_casos_graves_suficientes():
    # La regla más estricta del ADR 0008 es sobre los ESI 1 y 2: con pocos casos, no prueba nada.
    niveles = Counter(caso["esiEsperado"] for caso in CLINICOS)
    assert niveles[1] >= 5
    assert niveles[2] >= 5


def test_cada_grupo_de_edad_tiene_casos():
    grupos = Counter(grupo_de_edad(caso["edad"]) for caso in CLINICOS)
    assert set(grupos) == {"niño", "adulto", "mayor"}
    assert min(grupos.values()) >= 8


def test_los_dos_sexos_estan_parejos():
    sexos = Counter(caso["sexo"] for caso in CLINICOS)
    assert set(sexos) == {"femenino", "masculino"}
    assert min(sexos.values()) >= 0.4 * len(CLINICOS)


def test_hay_casos_con_instrucciones_escondidas():
    assert len(INYECCION) >= 4


def test_un_caso_de_inyeccion_intenta_bajar_la_gravedad():
    # El intento peligroso: que un caso grave pase por leve.
    assert any(caso["esiEsperado"] <= 2 for caso in INYECCION)


def test_los_ids_son_unicos():
    ids = [caso["id"] for caso in CASOS]
    assert len(ids) == len(set(ids))


# --- Cada caso --------------------------------------------------------------------------


@por_caso
def test_el_caso_tiene_los_campos_esperados(caso):
    assert set(caso) == {
        "id",
        "tipo",
        "edad",
        "sexo",
        "motivoConsulta",
        "sintomas",
        "signosVitales",
        "esiEsperado",
        "fundamento",
    }
    assert re.fullmatch(r"GS-\d{2}", caso["id"])
    assert caso["tipo"] in {"clinico", "inyeccion"}
    assert caso["sexo"] in {"femenino", "masculino"}
    assert caso["esiEsperado"] in {1, 2, 3, 4, 5}


@por_caso
def test_la_edad_usa_la_unidad_que_importa_al_triage(caso):
    # El protocolo ESI distingue a los menores de 28 días y de 3 meses: en años se pierde.
    valor, unidad = caso["edad"]["valor"], caso["edad"]["unidad"]
    limites = {"días": (0, 90), "meses": (3, 24), "años": (2, 120)}
    assert unidad in limites
    minimo, maximo = limites[unidad]
    assert minimo <= valor < maximo


@por_caso
def test_los_signos_vitales_respetan_el_contrato(caso):
    signos = caso["signosVitales"]
    assert set(SIGNOS["required"]) <= set(signos) <= set(SIGNOS["properties"])
    for nombre, valor in signos.items():
        rango = SIGNOS["properties"][nombre]
        assert rango["minimum"] <= valor <= rango["maximum"], nombre


@por_caso
def test_el_texto_respeta_el_contrato(caso):
    motivo = DATOS_CLINICOS["properties"]["motivoConsulta"]
    sintoma = DATOS_CLINICOS["properties"]["sintomas"]["items"]
    assert motivo["minLength"] <= len(caso["motivoConsulta"]) <= motivo["maxLength"]
    assert all(len(texto) <= sintoma["maxLength"] for texto in caso["sintomas"])


@por_caso
def test_cada_caso_explica_su_esi(caso):
    assert len(caso["fundamento"]) >= 40


@por_caso
def test_ningun_caso_trae_un_rut(caso):
    # Guardrail G1 del ADR 0008: los casos no traen identificadores, ni siquiera inventados.
    texto = " ".join([caso["motivoConsulta"], *caso["sintomas"]])
    assert not RUT.search(texto)
