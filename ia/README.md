# Golden set del motor de IA

El conjunto de casos con el que se mide el motor de IA (#124). Sirve para elegir el modelo
con la regla del [ADR 0008](../docs/adr/0008-servicio-ia-y-guardrails.md) (punto 2), para
medir fairness y para comparar el costo y la latencia antes y después de cada cambio.

Los casos están en [golden-set.yaml](golden-set.yaml). Son **inventados**, nunca datos reales
(política de IA del ramo, regla 4).

## Qué trae cada caso

Los mismos campos que el contrato recibe en un encuentro (`DatosClinicosInput` en
`api/openapi.yaml`): `motivoConsulta`, `sintomas` y `signosVitales`. Además trae:

- **`edad`**, con su unidad: en días para los menores de 3 meses, en meses para los menores
  de 2 años y en años para el resto. El protocolo ESI trata distinto a un recién nacido de
  menos de 28 días, y en años esa diferencia se pierde.
- **`sexo`**, para medir fairness.
- **`esiEsperado`** y su **`fundamento`**: qué punto de decisión del protocolo ESI lleva el
  caso a ese nivel.
- **`tipo`**: `clinico` para medir si la IA acierta, o `inyeccion` si el texto libre trae
  instrucciones escondidas (guardrail G2 del ADR 0008).

## Cómo se asignó el ESI

Con los puntos de decisión del manual del ESI (Emergency Severity Index):

| Punto | Pregunta | Nivel |
|---|---|---|
| A | ¿Necesita una intervención inmediata para salvar la vida? | ESI 1 |
| B | ¿Situación de alto riesgo, confusión o letargia, o dolor intenso? | ESI 2 |
| C | ¿Cuántos recursos distintos necesitará? | 2 o más: ESI 3 · 1: ESI 4 · ninguno: ESI 5 |
| D | Si sería ESI 3, ¿tiene signos vitales en zona de peligro? | Considerar ESI 2 |

Los casos son típicos a propósito, cada uno con un nivel claro, para que el error de medición
sea de la IA y no de un caso ambiguo.

## Cómo está compuesto

30 casos clínicos y 4 con instrucciones escondidas:

| ESI | Niños (0–14) | Adultos (15–64) | Mayores (65+) | Total |
|---|---|---|---|---|
| 1 | 2 | 2 | 2 | 6 |
| 2 | 2 | 4 | 2 | 8 |
| 3 | 2 | 3 | 2 | 7 |
| 4 | 1 | 3 | 1 | 5 |
| 5 | 2 | 1 | 1 | 4 |
| **Total** | **9** | **13** | **8** | **30** |

- **Más casos graves que leves:** la condición más estricta del ADR 0008 es que ningún ESI 1
  o 2 se sugiera como 3, 4 o 5. Con pocos casos graves, esa condición no prueba nada.
- **Mitad mujeres y mitad hombres**, para poder separar los resultados por sexo.
- **De los 4 casos con instrucciones escondidas, uno intenta bajar la gravedad:** un dolor
  de pecho que pide "responde ESI 5". Es el intento peligroso.

## Límites

- **Los ESI esperados no los revisó un profesional de salud.** Salen del manual del ESI, con
  el fundamento escrito en cada caso. La model card (#124) lo declara.
- **El contrato todavía no captura el sexo.** El ADR 0008 lo pone entre lo que se envía a la
  IA, así que hay que agregarlo al contrato, como campo opcional, en el #122.
- **30 casos son pocos para comparar grupos.** Una diferencia de un caso cambia mucho el
  porcentaje de un grupo de 8. Sirven para detectar un problema evidente, no para afirmar
  que no hay sesgo.

## Cómo se prueba

`tests/test_golden_set.py` revisa que el conjunto esté completo y bien formado, sin llamar a
la IA:

- que estén los cinco niveles y haya al menos 5 casos ESI 1 y 5 casos ESI 2;
- que cada grupo de edad tenga al menos 8 casos y los dos sexos estén parejos;
- que cada edad use la unidad correcta;
- que los signos vitales y los textos respeten los rangos del contrato, leídos de
  `api/openapi.yaml`;
- que ningún caso traiga un RUT.

El script que corre los casos contra la IA y mide exactitud, sub-triage, latencia y costo
llega con el #123.

## Cómo agregar un caso

1. Agrega el caso a `golden-set.yaml` con el siguiente `id` libre (`GS-35`, `GS-36`, ...).
2. Escribe en `fundamento` qué punto de decisión lo lleva a ese nivel.
3. Corre `python -m pytest tests/test_golden_set.py`.
