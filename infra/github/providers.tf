terraform {
  required_version = ">= 1.6"
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
  # State no HCP Terraform (gratuito): o runner do GitHub Actions é descartável.
  # A organização vem de TF_CLOUD_ORGANIZATION (Makefile e infra.yml já definem).
  cloud {
    workspaces {
      name = "news-recsys-github"
    }
  }
}

# Autenticação: GITHUB_TOKEN = PAT com admin do repositório (secret TF_GITHUB_TOKEN no Actions)
provider "github" {
  owner = var.github_owner
}
