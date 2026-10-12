# GitHub como código: repositório, environments (qa e prod), secrets do CI/CD e
# proteção da develop e da main. (O Databricks é gerenciado pelo Asset Bundle; o Streamlit Cloud pela UI.)

resource "github_repository" "this" {
  name                   = var.repository_name
  description            = "Recomendação de notícias com MLOps no Databricks - aula FIAP Pós-Tech Fase 5"
  visibility             = var.visibility
  has_issues             = true
  has_wiki               = false
  delete_branch_on_merge = true
  allow_merge_commit     = false
  allow_squash_merge     = true
  topics                 = ["mlops", "databricks", "mlflow", "recommender-system", "streamlit", "fiap"]
}

# develop → qa · main → prod (o cd.yml escolhe o environment pela branch)
resource "github_repository_environment" "env" {
  for_each    = toset(["qa", "prod"])
  repository  = github_repository.this.name
  environment = each.key
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

# develop e main só recebem PR com CI verde
resource "github_branch_protection" "branch" {
  for_each      = var.enable_branch_protection ? toset(["develop", "main"]) : toset([])
  repository_id = github_repository.this.node_id
  pattern       = each.key

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
