# Credenciales de las bases de datos (ADR 0004 y 0005).
#
# Las claves no se escriben aquí: se pasan como variables al ejecutar Terraform, con
# TF_VAR_clave_meditriage_app, TF_VAR_clave_auditoria_escritor y TF_VAR_clave_auditoria_lector.
# Terraform las guarda en el state, que vive cifrado en HCP Terraform y nunca en el
# repositorio. Ver db/README.md.
#
# Son tres Secrets, para que cada pod reciba solo lo que necesita: la API, la base principal y
# la auditoría para leer; el worker de auditoría, la base principal y la credencial que solo
# puede insertar en la auditoría.

variable "bd_host" {
  description = "Dónde está PostgreSQL. En local, el contenedor meditriage-postgres en la red de kind."
  type        = string
  default     = "meditriage-postgres"
}

variable "bd_sslmode" {
  description = "Cifrado de la conexión. En la nube, verify-full: cifrado en tránsito obligatorio."
  type        = string
  default     = "prefer"
}

variable "clave_meditriage_app" {
  description = "Clave del rol meditriage_app, en la base principal."
  type        = string
  sensitive   = true
}

variable "clave_auditoria_escritor" {
  description = "Clave del rol auditoria_escritor, que solo puede insertar en la auditoría."
  type        = string
  sensitive   = true
}

variable "clave_auditoria_lector" {
  description = "Clave del rol auditoria_lector, que solo puede leer la auditoría (lo usa la API)."
  type        = string
  sensitive   = true
}

locals {
  base_principal = "postgresql://meditriage_app:${urlencode(var.clave_meditriage_app)}@${var.bd_host}:5432/meditriage?sslmode=${var.bd_sslmode}"
  base_auditoria = "postgresql://auditoria_escritor:${urlencode(var.clave_auditoria_escritor)}@${var.bd_host}:5432/meditriage_auditoria?sslmode=${var.bd_sslmode}"
  auditoria_lectura = "postgresql://auditoria_lector:${urlencode(var.clave_auditoria_lector)}@${var.bd_host}:5432/meditriage_auditoria?sslmode=${var.bd_sslmode}"
}

resource "kubernetes_secret_v1" "meditriage_bd" {
  metadata {
    name      = "meditriage-bd"
    namespace = kubernetes_namespace_v1.meditriage.metadata[0].name
  }

  data = {
    BASE_DATOS_URL = local.base_principal
  }

  type = "Opaque"
}

resource "kubernetes_secret_v1" "meditriage_auditoria" {
  metadata {
    name      = "meditriage-auditoria"
    namespace = kubernetes_namespace_v1.meditriage.metadata[0].name
  }

  data = {
    AUDITORIA_URL = local.base_auditoria
  }

  type = "Opaque"
}

resource "kubernetes_secret_v1" "meditriage_auditoria_lectura" {
  metadata {
    name      = "meditriage-auditoria-lectura"
    namespace = kubernetes_namespace_v1.meditriage.metadata[0].name
  }

  data = {
    AUDITORIA_LECTURA_URL = local.auditoria_lectura
  }

  type = "Opaque"
}
