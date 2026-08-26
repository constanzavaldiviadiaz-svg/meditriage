Charter del equipo — MediTriage

Misión: Crear una herramienta que ayude a ordenar y priorizar pacientes usando IA, de forma clara, segura y fácil de usar.

## Integrantes y roles

| Integrante | Rol | Responsabilidad |
|---|---|---|
| Constanza Valdivia | Product Owner | Define qué se va a construir y en qué orden de importancia. Escribe y prioriza el backlog. |
| Fernando Ureta | Tech Lead · AI/Data Lead | Define cómo se construye el software a nivel técnico y guía al equipo. Custodio de la arquitectura y los ADR. Responsable de las funcionalidades de IA y sus métricas. |
| Matías Sepúlveda | DevSecOps Lead | Automatiza la entrega del software de forma rápida, estable y segura. Responsable de los pipelines, la seguridad y la observabilidad. |
| Matías Casa | QA Lead | Asegura que el software funcione correctamente y sin errores. Responsable de la estrategia de pruebas y de los criterios de aceptación. |

El ramo define cinco roles y el equipo son cuatro personas. Fernando asume además el rol de
AI/Data Lead, porque en MediTriage las decisiones de arquitectura y las del modelo de IA
están demasiado ligadas como para separarlas.

## Valores

* Responsabilidad
* Comunicación
* Trabajo en equipo
* Calidad
* Seguridad

## Reglas de trabajo

* Mantener una buena comunicación.
* Organizar las tareas en GitHub.
* Cumplir con las fechas acordadas.
* Revisar el trabajo antes de darlo por terminado.
* Avisar si existe algún problema o atraso.

## Comunicación y reuniones

Canal: WhatsApp y GitHub.
Reuniones: Dos veces por semana para revisar avances y organizar las tareas.

## Política de uso de IA

El uso de inteligencia artificial generativa en este proyecto está **permitido y es
esperado**. No la tratamos como un atajo, sino como una herramienta de trabajo más, sujeta a
las mismas reglas de calidad y revisión que el resto de lo que producimos.

**1. Toda contribución hecha con IA se declara.**
Cuando una parte del trabajo se generó con asistencia de IA, queda escrito en el mensaje del
commit. Indicamos qué herramienta se usó y qué parte del contenido asistió. Un commit sin
declaración significa que ese trabajo es enteramente del autor.

**2. Nadie sube lo que no entiende.**
Quien firma un commit responde por su contenido y debe ser capaz de explicarlo y defenderlo
ante el equipo o el docente. Si no podemos explicar por qué algo está escrito así, no entra
al repositorio: se estudia primero o se descarta.

**3. La revisión humana no se reemplaza.**
Nuestro Definition of Done exige que cada tarea sea revisada por el otro integrante. Esa
revisión aplica igual —o con más razón— al contenido asistido por IA.

**4. Ningún dato sensible entra a una herramienta de IA.**
MediTriage trabaja con datos de salud protegidos por la Ley 19.628 y la Ley 21.719. No
compartimos con herramientas de IA datos reales de pacientes, identificadores como el RUT,
credenciales ni claves de acceso. Para pruebas y ejemplos usamos siempre datos ficticios.

**5. La responsabilidad es del equipo.**
Un error introducido con ayuda de IA es un error del equipo, no de la herramienta. No es una
excusa válida ante una falla, y menos en un sistema que sugiere prioridades clínicas.

## Definition of Done

Una tarea está terminada cuando:

* Cumple con lo solicitado.
* Fue probada.
* Fue revisada y aprobada por al menos otro integrante, mediante Pull Request.
* Si el cambio afecta a un área con responsable —calidad, seguridad o arquitectura—, revisa
  además quien tiene ese rol.
* Se realizó el commit correspondiente.
* El Issue fue actualizado o cerrado.
