locals {
  common_labels = {
    "project"     = "meditriage"
    "environment" = "development"
    "cost-center" = "meditriage"
  }
}

resource "kubernetes_namespace_v1" "meditriage" {
  metadata {
    name = "meditriage"

    labels = merge(local.common_labels, {
      "app.kubernetes.io/name"       = "meditriage"
      "app.kubernetes.io/managed-by" = "terraform"
    })
  }
}