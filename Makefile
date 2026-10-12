SCHEMA  ?= news_recsys_dev
VOLUME   = /Volumes/workspace/$(SCHEMA)/raw
SITEMAP  = https://oglobo.globo.com/sitemap/oglobo/news.xml
DATABRICKS_INSTALL_URL = https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh

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

deploy: ## Publica notebooks + Job no workspace
	databricks bundle deploy

run: ## Executa o Job (dados → treino → recomendações)
	databricks bundle run recsys

export-notebooks: ## Traz os notebooks executados (com resultados) para notebooks/
	@ROOT=$$(databricks bundle summary -o json | jq -r .workspace.file_path); \
	for nb in notebooks/*.ipynb; do \
		databricks workspace export "$$ROOT/$${nb%.ipynb}" --format JUPYTER --file "$$nb"; \
	done

# ---- Local -----------------------------------------------------------------------
lint: ## Lint dos notebooks e do app
	.venv/bin/ruff check notebooks app

app: ## Roda o app Streamlit (sem secrets usa app/sample_data)
	.venv/bin/streamlit run app/streamlit_app.py

# ---- Terraform (GitHub) -----------------------------------------------------------
tf-init: ## terraform init
	terraform -chdir=infra/github init

tf-plan: ## terraform plan (usa o token do gh e TF_VAR_databricks_token)
	GITHUB_TOKEN=$$(gh auth token) terraform -chdir=infra/github plan -out=tfplan

tf-apply: ## terraform apply
	GITHUB_TOKEN=$$(gh auth token) terraform -chdir=infra/github apply tfplan
