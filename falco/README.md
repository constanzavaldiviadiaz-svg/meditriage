# Falco: detección dentro del clúster

Falco observa lo que hacen los contenedores mientras corren: cada proceso que se abre y cada
conexión que sale. Lo ve desde el kernel, con el driver `modern_ebpf`. Cuando algo coincide
con una regla, escribe una alerta. No bloquea nada: **detecta y avisa**. La prevención, que
una imagen sin firma no entre al clúster, le toca a Kyverno (#118, ADR 0007).

Cómo instalarlo y probarlo en el clúster local: [cluster-local/README.md](../cluster-local/README.md#detección-con-falco).

## Las tres reglas propias

Están en [rules-custom.yaml](rules-custom.yaml) y vigilan los dos contenedores de la
aplicación en el namespace `meditriage`: la API (`api`) y el worker de auditoría (`worker`).
Los dos usan la misma imagen distroless, y su comportamiento normal es muy acotado: un solo
proceso, `python3`, que se conecta a PostgreSQL y al servicio de IA.

| Regla | Qué detecta | Por qué es sospechoso | Severidad |
|---|---|---|---|
| Shell en un contenedor de MediTriage | `sh`, `bash` u otro shell | La imagen no trae shell: si aparece, alguien lo metió | **Critical** |
| Proceso inesperado en un contenedor de MediTriage | Cualquier programa que no sea `python3` | Puede ser una herramienta de ataque o un minero | **Error** |
| Conexión saliente no autorizada desde MediTriage | Una conexión a un destino que no sea DNS, PostgreSQL o `api.anthropic.com` | Puede ser alguien llevándose datos de pacientes (ADR 0002 y 0008) | **Error** |

Falco no tiene una severidad "High". Aquí **Critical** es un compromiso casi seguro y
**Error** es un comportamiento que la aplicación nunca tiene. Las dos son incidentes.

### Lo que se excluye, y por qué

Dos cosas que ocurren dentro de los contenedores pero que no son la aplicación. Las dos
aparecieron como falsas alarmas al probar en kind:

- **`runc init`.** Para entrar a un contenedor, runc ejecuta dentro de él una copia de sí
  mismo, que aparece como un proceso con nombre de número (por ejemplo `6`). Ocurre en cada
  `kubectl exec`.
- **El hook de kind.** Al crear cada contenedor, el nodo de kind corre
  `/kind/bin/mount-product-...`, que lanza `jq` y `cp`. No existe en un clúster gestionado.

Las dos exclusiones exigen que el proceso venga de runc, una cadena que nadie puede fabricar
desde dentro del contenedor.

### Una configuración que importa: `rule_matching: all`

Por defecto, Falco informa solo **la primera** regla que coincide con un evento, y sus reglas
propias se cargan antes que las nuestras. Al probar, una conexión a la API de Kubernetes salió
como **Notice** de una regla de Falco, y la nuestra, que es **Error** y por lo tanto un
incidente, no se informó. Con `rule_matching: all` ([values.yaml](values.yaml)) se informan
todas las reglas que coinciden.

## Cómo se prueba

[probar-reglas.sh](probar-reglas.sh) levanta un pod de prueba ([pod-de-prueba.yaml](pod-de-prueba.yaml))
que simula un contenedor de la API comprometido: está en el mismo namespace y tiene el mismo
nombre de contenedor, pero su imagen trae shell. El script hace dos grupos de cosas:

1. **Casos legítimos, que no deben alertar:** ejecutar `python3`, conectarse a PostgreSQL y al
   servicio de IA.
2. **Casos de ataque, que deben alertar cada uno:** abrir un shell, ejecutar `id` y conectarse
   a la API de Kubernetes.

Además, se probó con la aplicación real: reiniciar la API y el worker, registrar pacientes y
dejar que el worker los audite no genera ninguna alerta.

## Ruta de alerta

**Toda alerta Critical o Error de estas reglas es un incidente**, no una línea más del log.

| Quién | Cuándo |
|---|---|
| **DevSecOps Lead** (Matías Sepúlveda) | Responsable del incidente, desde la alerta |
| **Tech Lead** (Fernando Ureta) | Si el DevSecOps Lead no responde en 15 minutos |
| **Product Owner** (Constanza Valdivia) | Si pudo haber datos de pacientes comprometidos |

Las alertas de las reglas que trae Falco (Notice o Warning) se revisan, pero no son
incidentes.

**Los primeros pasos:**

1. **No borrar el pod:** es la evidencia. Primero se aísla, quitándole la etiqueta que usa el
   Service. Así deja de recibir tráfico, y el Deployment levanta un reemplazo:
   ```bash
   kubectl label pod -n meditriage <pod> app-
   ```
2. **Guardar la evidencia:** el log de Falco, `kubectl describe pod` y el log del pod.
   ```bash
   kubectl logs -n falco ds/falco -c falco | grep "MediTriage" > alertas.txt
   ```
3. **Si alertó la regla de conexiones,** suponer que hubo filtración: rotar las credenciales
   (`meditriage-bd`, `meditriage-auditoria` y la clave del servicio de IA) con Terraform.
4. **Revisar la auditoría:** `auditoria.verificar_cadena()` dice si alguien la alteró (ver
   `db/README.md`, que llega con el #142).
5. **Con la Product Owner,** si hubo datos de pacientes en riesgo, evaluar si corresponde
   informar a los afectados o a la autoridad (Ley 21.719).
6. **Después:** borrar el pod aislado, y escribir qué pasó y qué se cambia para que no se
   repita.

Por ahora las alertas se leen en el log de Falco. Para que lleguen solas a un canal del equipo
(Discord, Slack, correo) está Falcosidekick, que queda apagado en
[values.yaml](values.yaml) hasta que el equipo elija el canal. Eso requiere un webhook, que
es un secreto más.

## Límites conocidos

- **El DNS queda abierto.** La regla permite cualquier conexión al puerto 53. Alguien podría
  sacar datos escondidos en consultas DNS, y esta regla no lo vería.
- **El destino del servicio de IA se reconoce por nombre.** Falco resuelve `api.anthropic.com`
  por su cuenta. Si el proveedor cambia de IP y Falco aún no se entera, una llamada legítima
  podría alertar. Es una falsa alarma ruidosa, no un ataque silencioso.
- **El Registro Civil no está integrado.** Su destino queda preparado en
  `meditriage_destino_registro_civil`, para cuando exista.
- **Solo vigila los contenedores `api` y `worker`.** Un contenedor nuevo en el namespace
  necesita sumarse a `meditriage_contenedores`.
