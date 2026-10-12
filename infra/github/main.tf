# GitHub como código: environments (qa e prod) e proteção da develop e da main.
# O repositório é criado à mão (make gh-repo) e os secrets também (make gh-secrets):
# a esteira não pode criar as próprias credenciais.

data "github_repository" "this" {
  name = var.repository_name
}

# develop → qa · main → prod (o cd.yml escolhe o environment pela branch)
resource "github_repository_environment" "env" {
  for_each    = toset(["qa", "prod"])
  repository  = data.github_repository.this.name
  environment = each.key
}

# develop e main só recebem PR com CI verde
resource "github_branch_protection" "branch" {
  for_each      = toset(["develop", "main"])
  repository_id = data.github_repository.this.node_id
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
