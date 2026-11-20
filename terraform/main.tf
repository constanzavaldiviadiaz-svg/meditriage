
resource "kubernetes_namespace_v1" "meditriage" {
  metadata {
    name = "meditriage"

    labels = {
      "app.kubernetes.io/name"       = "meditriage"
      "app.kubernetes.io/managed-by" = "terraform"
      "environment"                  = "development"
    }
  }
}
