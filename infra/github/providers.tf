terraform {
  required_version = ">= 1.6"
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
  # State LOCAL (gitignored). Ele contém os secrets em texto puro!
  # Em produção: backend remoto criptografado (S3+KMS, GCS, Terraform Cloud...).
}

# Autenticação: export GITHUB_TOKEN=$(gh auth token)   (o Makefile já faz isso)
provider "github" {
  owner = var.github_owner
}
