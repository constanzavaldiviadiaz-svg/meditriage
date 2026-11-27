# La clave de la API de Claude, el motor de IA (ADR 0008).
#
# Igual que las claves de las bases: no se escribe aquí, se pasa con TF_VAR_anthropic_api_key
# al ejecutar Terraform. Si no se pasa, el Secret no se crea y la API usa el simulador
# (MOTOR_IA=simulador en el ConfigMap): así el clúster local funciona sin gastar créditos.

variable "anthropic_api_key" {
  description = "Clave de la API de Claude. Vacía: no se crea el Secret y se usa el simulador."
  type        = string
  default     = ""
  sensitive   = true
}

resource "kubernetes_secret_v1" "meditriage_ia" {
  count = var.anthropic_api_key == "" ? 0 : 1

  metadata {
    name      = "meditriage-ia"
    namespace = kubernetes_namespace_v1.meditriage.metadata[0].name
  }

  data = {
    ANTHROPIC_API_KEY = var.anthropic_api_key
  }

  type = "Opaque"
}
