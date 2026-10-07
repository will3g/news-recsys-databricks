.PHONY: help install test lint format fetch-sitemap train-local app build-notebooks validate-notebooks \
        db-install db-configure db-check db-upload-catalog bundle-validate bundle-deploy bundle-run \
        bundle-deploy-prod export-notebooks tf-init tf-plan tf-apply tf-output clean

PYTHON  ?= python3.12
VENV    ?= .venv
ACTIVATE = . $(VENV)/bin/activate

PROFILE ?= DEFAULT
TARGET  ?= dev
CATALOG ?= workspace
SCHEMA  ?= news_recsys_dev
TODAY   := $(shell date +%Y%m%d)
NOTEBOOKS = $(wildcard notebooks/*.ipynb)

help: ## Mostra este help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ----- Local ---------------------------------------------------------------------
install: ## Cria venv e instala dependências (core + dev)
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip && pip install -e ".[dev]"

test: ## Roda pytest
	$(ACTIVATE) && pytest

lint: ## Roda ruff (check + format --check)
	$(ACTIVATE) && ruff check . && ruff format --check .

format: ## Formata com ruff
	$(ACTIVATE) && ruff format . && ruff check --fix .

fetch-sitemap: ## Baixa o sitemap e acumula em data/articles_snapshot.json
	$(ACTIVATE) && python -m scripts.fetch_sitemap --merge-into data/articles_snapshot.json

train-local: ## Pipeline completo local (simulação + 3 modelos) e gera app/sample_data
	$(ACTIVATE) && python -m scripts.train_local

app: ## Roda o app Streamlit localmente (usa sample_data se não houver secrets)
	$(ACTIVATE) && streamlit run app/streamlit_app.py

build-notebooks: ## (Re)gera notebooks/*.ipynb a partir de scripts/nb/*.py (SEM outputs)
	$(ACTIVATE) && python -m scripts.build_notebooks

validate-notebooks: ## Valida os .ipynb e conta outputs
	$(ACTIVATE) && python -m scripts.validate_notebooks

# ----- Databricks ------------------------------------------------------------------
db-install: ## Instala a Databricks CLI (Homebrew)
	brew tap databricks/tap && brew trust databricks/tap && brew install databricks

db-configure: ## Configura profile com PAT (interativo: host + token)
	databricks configure --token --profile $(PROFILE)

db-check: ## Usuário atual + SQL warehouses
	databricks current-user me --profile $(PROFILE) -o json | jq -r .userName
	databricks warehouses list --profile $(PROFILE)

db-upload-catalog: ## Envia o catálogo acumulado para o Volume (raw/catalog/)
	databricks fs cp data/articles_snapshot.json \
		dbfs:/Volumes/$(CATALOG)/$(SCHEMA)/raw/catalog/catalog_$(TODAY).json --overwrite --profile $(PROFILE)

bundle-validate: ## databricks bundle validate
	databricks bundle validate -t $(TARGET) --profile $(PROFILE)

bundle-deploy: ## Deploy do bundle (schema, volume, job, notebooks, src)
	databricks bundle deploy -t $(TARGET) --profile $(PROFILE)

bundle-run: ## Executa o job de treino ponta a ponta
	databricks bundle run recsys_pipeline -t $(TARGET) --profile $(PROFILE)

bundle-deploy-prod: ## Deploy no target prod (normalmente feito pelo GitHub Actions)
	databricks bundle deploy -t prod --profile $(PROFILE)

export-notebooks: ## Baixa os notebooks executados (COM outputs) para notebooks/
	@ROOT=$$(databricks bundle summary -t $(TARGET) --profile $(PROFILE) -o json | jq -r '.workspace.file_path'); \
	for nb in $(NOTEBOOKS); do \
		echo "-> $$nb"; \
		databricks workspace export "$$ROOT/$$nb" --format JUPYTER --file "$$nb" --profile $(PROFILE); \
	done
	$(ACTIVATE) && python -m scripts.validate_notebooks

# ----- Terraform (GitHub) ---------------------------------------------------------------
tf-init: ## terraform init (infra/github)
	terraform -chdir=infra/github init

tf-plan: ## terraform plan — usa GITHUB_TOKEN do gh e TF_VAR_databricks_token do ambiente
	GITHUB_TOKEN=$$(gh auth token) terraform -chdir=infra/github plan -out=tfplan

tf-apply: ## terraform apply do plano salvo
	GITHUB_TOKEN=$$(gh auth token) terraform -chdir=infra/github apply tfplan

tf-output: ## Mostra outputs (URL do repo etc.)
	terraform -chdir=infra/github output

clean: ## Remove venv e caches
	rm -rf $(VENV) .pytest_cache .ruff_cache **/__pycache__ *.egg-info
