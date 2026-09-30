# Atributos de calidad prioritarios

Para MediTriage se priorizan los atributos de **Seguridad**, **Disponibilidad** y **Observabilidad**.

Estos tres atributos fueron seleccionados porque están directamente relacionados con los riesgos principales del sistema: el manejo de datos clínicos sensibles, la necesidad de mantener operativo el proceso de triage y la obligación de conservar trazabilidad sobre las decisiones realizadas por el sistema.

## 1. Seguridad

**Métrica:**
100% de los datos sensibles deben estar cifrados tanto en tránsito como en reposo, y no debe existir exposición de información personal identificable (PII) en los logs.

**Implicancia en la arquitectura:**
La arquitectura debe considerar cifrado en las comunicaciones y en el almacenamiento de datos, gestión segura de secretos y enmascaramiento de PII en los registros del sistema.

## 2. Disponibilidad

**Métrica:**
El sistema debe mantener una disponibilidad mensual mínima de **99,5%**.

**Implicancia en la arquitectura:**
La arquitectura debe incorporar mecanismos de detección y recuperación ante fallos, como health checks y redundancia en los componentes críticos, evitando puntos únicos de falla.

## 3. Observabilidad

**Métrica:**
El 100% de las decisiones de priorización realizadas por el sistema deben quedar registradas y ser trazables.

**Implicancia en la arquitectura:**
La arquitectura debe incorporar logging estructurado, monitoreo de los componentes y un mecanismo de auditoría que permita rastrear las decisiones realizadas por el sistema.

## Justificación de la priorización

Se priorizan Seguridad, Disponibilidad y Observabilidad porque son los atributos que tienen mayor impacto sobre el funcionamiento y los riesgos de MediTriage.

Seguridad es fundamental por el tratamiento de información clínica y datos personales. Disponibilidad es necesaria porque el sistema apoya un proceso operativo de atención de pacientes y debe mantenerse accesible. Observabilidad permite supervisar el comportamiento del sistema y mantener trazabilidad sobre las decisiones de priorización.

Otros atributos como costo y performance siguen siendo relevantes para el proyecto, pero no fueron seleccionados entre los tres prioritarios. El costo deberá considerarse posteriormente en las decisiones de infraestructura, mientras que performance ya cuenta con el requisito de respuesta de triage inferior a 3 segundos.