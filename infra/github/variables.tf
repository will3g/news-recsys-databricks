variable "github_owner" {
  description = "Usuário ou organização dona do repositório"
  type        = string
}

variable "repository_name" {
  description = "Nome do repositório"
  type        = string
  default     = "news-recsys-databricks"
}

variable "visibility" {
  description = "public é necessário para o Streamlit Community Cloud gratuito (só 1 app privado)"
  type        = string
  default     = "public"
}

variable "databricks_host" {
  description = "URL do workspace (https://dbc-xxxx.cloud.databricks.com)"
  type        = string
}

variable "databricks_token" {
  description = "PAT do Databricks - passe via TF_VAR_databricks_token, nunca no tfvars versionado"
  type        = string
  sensitive   = true
}

variable "enable_branch_protection" {
  description = "Ligue DEPOIS do primeiro push (develop e main precisam existir)"
  type        = bool
  default     = false
}
