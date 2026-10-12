# Ambiente: dev (padrão, isolado) | qa | prod  →  ex.: make deploy TARGET=qa
TARGET  ?= dev
SCHEMA   = news_recsys_$(TARGET)
VOLUME   = /Volumes/workspace/$(SCHEMA)/raw
SITEMAP  = https://oglobo.globo.com/sitemap/oglobo/news.xml
DATABRICKS_INSTALL_URL = https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh
GH_OWNER ?= $(shell gh api user -q .login 2>/dev/null)
GH_REPO   = $(GH_OWNER)/news-recsys-databricks
# Organização no HCP Terraform (nome único; crie em app.terraform.io)
TF_ORG   ?= $(GH_OWNER)-mlops
TF_ENV    = TF_CLOUD_ORGANIZATION=$(TF_ORG) TF_VAR_github_owner=$(GH_OWNER) GITHUB_TOKEN=$$(gh auth token)

.PHONY: help doctor gh-login db-install db-configure install setup sitemap deploy run db-destroy lint app \
	gh-repo tf-login tf-workspace gh-secrets gh-push tf-init tf-plan tf-apply

help: ## Mostra os comandos
	@grep -E '^[a-z-]+:.*## ' Makefile | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

# ---- Preparação ---------------------------------------------------------------
doctor: ## Confere as ferramentas instaladas (macOS, Linux, Windows/WSL)
	@sh scripts/doctor.sh jq terraform gh

db-install: ## Instala a Databricks CLI (script oficial)
	curl -fsSL $(DATABRICKS_INSTALL_URL) | sh
	databricks --version

db-configure: ## Conecta a CLI ao workspace (pede URL e token)
	databricks configure --token

install: ## Ambiente Python local (lint + app)
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

# ---- Databricks ----------------------------------------------------------------
setup: ## Cria schema e Volume e envia o sitemap de exemplo
	-databricks schemas create $(SCHEMA) workspace
	-databricks volumes create workspace $(SCHEMA) raw MANAGED
	databricks fs mkdirs dbfs:$(VOLUME)/sitemaps
	databricks fs cp data/sitemap_snapshot.xml dbfs:$(VOLUME)/sitemaps/sitemap_snapshot.xml --overwrite

sitemap: ## Baixa o sitemap de hoje e envia para o Volume
	curl -fsSL -A "Mozilla/5.0" $(SITEMAP) -o /tmp/sitemap.xml
	databricks fs mkdirs dbfs:$(VOLUME)/sitemaps
	databricks fs cp /tmp/sitemap.xml dbfs:$(VOLUME)/sitemaps/sitemap_$$(date +%Y%m%d).xml --overwrite

deploy: ## Publica notebooks + Job no workspace (TARGET=dev|qa|prod)
	databricks bundle deploy -t $(TARGET)

run: ## Executa o Job (dados → treino → recomendações)
	databricks bundle run recsys -t $(TARGET)

db-destroy: ## Apaga do Databricks o Job, os notebooks, o schema (tabelas, Volume, modelo) e o experimento
	@printf "Apagar o Job e TUDO em workspace.$(SCHEMA)? [s/N] " && read r && [ "$$r" = s ]
	-databricks bundle destroy -t $(TARGET) --auto-approve
	-databricks schemas delete workspace.$(SCHEMA) --force
	-databricks workspace delete "/Users/$$(databricks current-user me | jq -r .userName)/$(SCHEMA)"
	rm -rf .databricks/bundle/$(TARGET)

# ---- Local -----------------------------------------------------------------------
lint: ## Lint dos notebooks e do app
	.venv/bin/ruff check notebooks app

app: ## Roda o app Streamlit (sem secrets usa app/sample_data)
	.venv/bin/streamlit run app/streamlit_app.py

# ---- GitHub: preparação manual, uma vez (a esteira não cria as próprias credenciais) ----
gh-repo: ## 1) Cria o repositório público e aponta o remote origin
	gh repo create $(GH_REPO) --public --source . --remote origin

tf-login: ## 2) Login no HCP Terraform (abre o navegador; crie antes a organização em app.terraform.io)
	terraform login

tf-workspace: ## 3) Cria o workspace do state no HCP Terraform (execução local = no runner)
	@curl -sf -X POST https://app.terraform.io/api/v2/organizations/$(TF_ORG)/workspaces \
		-H "Authorization: Bearer $$(jq -r '.credentials["app.terraform.io"].token' ~/.terraform.d/credentials.tfrc.json)" \
		-H "Content-Type: application/vnd.api+json" \
		-d '{"data":{"type":"workspaces","attributes":{"name":"news-recsys-github","execution-mode":"local"}}}' \
		>/dev/null && echo "workspace criado" || echo "workspace já existe (ou organização $(TF_ORG) não existe)"

gh-secrets: ## 4) Secrets do Actions (pede o PAT do GitHub com admin do repositório)
	databricks auth env | jq -r .env.DATABRICKS_HOST | gh secret set DATABRICKS_HOST -R $(GH_REPO)
	databricks auth env | jq -r .env.DATABRICKS_TOKEN | gh secret set DATABRICKS_TOKEN -R $(GH_REPO)
	jq -r '.credentials["app.terraform.io"].token' ~/.terraform.d/credentials.tfrc.json | gh secret set TF_API_TOKEN -R $(GH_REPO)
	gh variable set TF_CLOUD_ORGANIZATION --body $(TF_ORG) -R $(GH_REPO)
	gh secret set TF_GITHUB_TOKEN -R $(GH_REPO)

gh-push: ## 5) Envia main e develop: a esteira assume (infra, QA e PROD)
	git push -u origin main develop

# ---- Terraform local (opcional: o normal é o infra.yml rodar) ------------------------
tf-init: ## terraform init (state no HCP Terraform)
	$(TF_ENV) terraform -chdir=infra/github init

tf-plan: ## terraform plan
	$(TF_ENV) terraform -chdir=infra/github plan

tf-apply: ## terraform apply
	$(TF_ENV) terraform -chdir=infra/github apply
