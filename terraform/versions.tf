
terraform {
  required_version = ">= 1.17.0"

  cloud {
    organization = "meditriage-dev-byretro"

    workspaces {
      name = "meditriage-dev"
    }
  }

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.38"
    }
  }
}
