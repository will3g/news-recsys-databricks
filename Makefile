# Ambiente: dev (padrão, isolado) | qa | prod  →  ex.: make deploy TARGET=qa
TARGET  ?= dev
SCHEMA   = news_recsys_$(TARGET)
VOLUME   = /Volumes/workspace/$(SCHEMA)/raw
SITEMAP  = https://oglobo.globo.com/sitemap/oglobo/news.xml
DATABRICKS_INSTALL_URL = https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh
GH_OWNER ?= $(shell gh api user -q .login 2>/dev/null)
GH_REPO   = $(GH_OWNER)/news-recsys-databricks
# Terraform: no Actions o GITHUB_TOKEN vem do secret TF_GITHUB_TOKEN; local, do gh
TF_ENV    = GITHUB_TOKEN=$${GITHUB_TOKEN:-$$(gh auth token)} TF_VAR_github_owner=$(GH_OWNER)
TF_STATE  = dbfs:/Volumes/workspace/default/tfstate/github.tfstate

.PHONY: help doctor gh-login db-install db-configure install setup sitemap deploy run db-destroy lint app \
	gh-repo gh-secrets gh-push gh-destroy tf-plan tf-apply

help: ## Mostra os comandos
	@grep -E '^[a-z-]+:.*## ' Makefile | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

# ---- Preparação ---------------------------------------------------------------
doctor: ## Confere as ferramentas instaladas (macOS, Linux, Windows/WSL)
	@sh scripts/doctor.sh jq terraform gh

gh-login: ## Dá ao gh permissão para enviar os workflows e apagar o repositório (gh-destroy)
	gh auth refresh -h github.com -s workflow,delete_repo

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

gh-secrets: ## 2) Secrets do Actions: Databricks (do ~/.databrickscfg) + PAT do GitHub (pede para colar)
	databricks auth env | jq -r .env.DATABRICKS_HOST | gh secret set DATABRICKS_HOST -R $(GH_REPO)
	databricks auth env | jq -r .env.DATABRICKS_TOKEN | gh secret set DATABRICKS_TOKEN -R $(GH_REPO)
	gh secret set TF_GITHUB_TOKEN -R $(GH_REPO)

gh-push: ## 3) Envia main e develop: a esteira assume (infra, Databricks, Streamlit)
	git push -u origin main develop

gh-destroy: ## Apaga o repositório no GitHub e o state do Terraform (para recriar do zero)
	@printf "Apagar o repositório $(GH_REPO) e o state do Terraform? [s/N] " && read r && [ "$$r" = s ]
	-gh repo delete $(GH_REPO) --yes
	-databricks fs rm $(TF_STATE)
	-git remote remove origin

# ---- Terraform (roda no cd.yml; local também funciona) -------------------------------
tf-plan: ## terraform plan (baixa o state do Volume workspace.default.tfstate)
	-@databricks volumes create workspace default tfstate MANAGED >/dev/null 2>&1
	-@databricks fs cp $(TF_STATE) infra/github/terraform.tfstate --overwrite 2>/dev/null
	$(TF_ENV) terraform -chdir=infra/github init -input=false
	$(TF_ENV) terraform -chdir=infra/github plan -input=false -out=tfplan

tf-apply: ## terraform apply do plano e devolve o state ao Volume
	$(TF_ENV) terraform -chdir=infra/github apply -input=false tfplan
	databricks fs cp infra/github/terraform.tfstate $(TF_STATE) --overwrite
