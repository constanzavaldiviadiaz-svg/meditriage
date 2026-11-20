
# Secret de demostración.
# No utilizar credenciales reales ni datos clínicos.

resource "kubernetes_secret_v1" "meditriage_example" {
  metadata {
    name      = "meditriage-example-secret"
    namespace = kubernetes_namespace_v1.meditriage.metadata[0].name
  }

  data = {
    DEMO_API_KEY = "meditriage-demo-not-a-real-key"
  }

  type = "Opaque"
}
