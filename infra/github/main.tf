# GitHub como código: repositório, environment de produção, secrets/variáveis do CI/CD e
# proteção da main. (O Databricks é gerenciado pelo Asset Bundle; o Streamlit Cloud pela UI.)

resource "github_repository" "this" {
  name                   = var.repository_name
  description            = "Recomendação de notícias com MLOps no Databricks — aula FIAP Pós-Tech Fase 5"
  visibility             = var.visibility
  has_issues             = true
  has_wiki               = false
  delete_branch_on_merge = true
  allow_merge_commit     = false
  allow_squash_merge     = true
  topics                 = ["mlops", "databricks", "mlflow", "recommender-system", "streamlit", "fiap"]
}

resource "github_repository_environment" "prod" {
  repository  = github_repository.this.name
  environment = "prod"
}

# Secrets do repositório (usados por ci.yml, cd.yml e ingest.yml)
resource "github_actions_secret" "databricks_host" {
  repository      = github_repository.this.name
  secret_name     = "DATABRICKS_HOST"
  plaintext_value = var.databricks_host
}

resource "github_actions_secret" "databricks_token" {
  repository      = github_repository.this.name
  secret_name     = "DATABRICKS_TOKEN"
  plaintext_value = var.databricks_token
}

resource "github_actions_variable" "catalog" {
  repository    = github_repository.this.name
  variable_name = "DATABRICKS_CATALOG"
  value         = var.databricks_catalog
}

resource "github_actions_variable" "schema" {
  repository    = github_repository.this.name
  variable_name = "DATABRICKS_SCHEMA"
  value         = var.databricks_schema_prod
}

# main só recebe PR com CI verde
resource "github_branch_protection" "main" {
  count         = var.enable_branch_protection ? 1 : 0
  repository_id = github_repository.this.node_id
  pattern       = "main"

  required_status_checks {
    strict   = true
    contexts = ["test"]
  }

  required_pull_request_reviews {
    required_approving_review_count = 0
  }

  enforce_admins      = false
  allows_force_pushes = false
  allows_deletions    = false
}
