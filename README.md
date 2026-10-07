# Recomendação de notícias com MLOps no Databricks

**FIAP Pós-Tech · Fase 5 — MLOps · projeto de aula**

Um recomendador **personalizado** de notícias treinado, versionado e servido no
**Databricks Free Edition**, com **CI/CD no GitHub Actions**, **GitHub como código
(Terraform)** e um app **Streamlit** publicado no **Streamlit Community Cloud**.

- Matérias **reais**: sitemap de notícias do O Globo (só metadados; o app linka para o site).
- Usuários e cliques **sintéticos**: 8 personas, reproduzíveis por `seed` (não há clickstream público).
- 5 famílias de modelo comparadas no MLflow: **popularidade** (baseline), **item-item CF**, **SVD**,
  **conteúdo (TF-IDF)** e **híbrido** (CF + conteúdo), que resolve o *cold start* de matéria nova.

  | Candidato (local, 07/10/2026) | NDCG@10 | HitRate@10 | HitRate@10 em matérias frias |
  |---|---|---|---|
  | **híbrido α=0,4 (campeão)** | **0,212** | 0,68 | 0,20 |
  | conteúdo (TF-IDF) | 0,155 | 0,59 | 0,39 |
  | item-item CF | 0,139 | 0,56 | 0,00 |
  | SVD (16 fatores) | 0,125 | 0,49 | 0,00 |
  | popularidade | 0,035 | 0,16 | 0,00 |
- *Quality gate* champion/challenger → alias `@champion` no Unity Catalog → **inferência batch** → app.

```
GitHub Actions ──(cron)──► sitemap ──► Volume ──► Job Databricks (6 tasks) ──► gold_user_recommendations
     │  ci: ruff/pytest/bundle validate                  │ MLflow + Unity Catalog            │
     │  cd: bundle deploy -t prod                        └─► @champion                       ▼
     └─ Terraform: repo, secrets, environment, proteção da main            App Streamlit (Community Cloud)
```

## Stack

| Camada | Ferramenta | Onde |
|---|---|---|
| Ingestão | `scripts/fetch_sitemap.py` | GitHub Actions (`ingest.yml`, diário) |
| Dados | Delta Lake + Unity Catalog (bronze/silver/gold) + Volume | Databricks |
| Treino | scikit-learn/scipy + **MLflow** (runs aninhadas) | Databricks (serverless) |
| Registro | **Unity Catalog Models** + alias `@champion` + quality gate | Databricks |
| Inferência | batch → `gold_user_recommendations` | Databricks (Job) |
| Orquestração / IaC do projeto | **Databricks Asset Bundles** (`databricks.yml`) | Databricks |
| CI/CD | **GitHub Actions** (`ci.yml`, `cd.yml`, `ingest.yml`) | GitHub |
| IaC do GitHub | **Terraform** (`integrations/github`) | `infra/github` |
| App | **Streamlit** + `databricks-sql-connector` (fallback: `sample_data`) | Streamlit Community Cloud |

## Estrutura

```
src/news_recsys/        código de produção (testado, sem SDKs no import)
  ingestion/            sitemap.py, catalog.py
  features/sections.py  editoria a partir da URL
  simulation.py         personas e cliques sintéticos
  models/               base.py, popularity.py, item_cf.py, svd.py, content.py, hybrid.py
  evaluation/           split.py (temporal), metrics.py (P/R/NDCG/Hit@K)
  training.py           treina e compara candidatos
  registry.py           quality gate + alias @champion
  monitoring.py         cobertura, PSI de editorias
  pyfunc_model.py       wrapper MLflow (o artefato registrado)
notebooks/              00–06: a aula (exportados com outputs)
scripts/                fetch_sitemap, train_local, build/validate_notebooks, nb/ (fontes)
app/                    streamlit_app.py, data_access.py, sample_data/
databricks.yml, resources/   Asset Bundle (job de 6 tasks, targets dev/prod)
.github/workflows/      ci.yml, cd.yml, ingest.yml
infra/github/           Terraform do repositório
docs/                   GUIA_DO_PROFESSOR.md, ROTEIRO_AULA.md, ARCHITECTURE.md, ARQUITETURA_MERMAID.md
```

## Rodar localmente (sem Databricks)

```bash
make install
make test lint
make fetch-sitemap      # atualiza data/articles_snapshot.json
make train-local        # simula, treina os 3 modelos, imprime métricas e gera app/sample_data
make app                # http://localhost:8501 (modo amostra)
```

## Passo a passo completo

O roteiro detalhado, com prints de onde clicar, está em
[`docs/GUIA_DO_PROFESSOR.md`](docs/GUIA_DO_PROFESSOR.md). Resumo:

1. **Databricks:** gere um PAT (Settings → Developer → Access tokens), rode `make db-configure`,
   `make bundle-deploy` e depois `make bundle-run` (ou rode os notebooks 00→06 na UI).
2. **GitHub (Terraform):**
   ```bash
   cp infra/github/terraform.tfvars.example infra/github/terraform.tfvars   # edite
   export TF_VAR_databricks_token="dapi..."
   make tf-init tf-plan tf-apply
   git remote add origin git@github.com:<owner>/news-recsys-databricks.git && git push -u origin main
   # depois: enable_branch_protection = true no tfvars -> make tf-plan tf-apply
   ```
3. **Streamlit Community Cloud:** share.streamlit.io → *Create app* → repositório / `main` /
   `app/streamlit_app.py` → *Advanced settings* → cole os secrets de
   `app/.streamlit/secrets.toml.example` (host, `http_path` do SQL warehouse, token, `schema = "news_recsys"`).

## Custos

R$ 0: Databricks Free Edition (uso não comercial), GitHub Actions (repo público),
Streamlit Community Cloud (app público).

## Pontos de atenção

- **State do Terraform contém o token do Databricks em texto puro** → fica local e gitignored.
- **PAT expira** → renovar em: secrets do GitHub (`make tf-apply`) e secrets do Streamlit.
- **Cold start de usuário** (sem histórico) → popularidade com recência; de **matéria** → conteúdo/híbrido.
- Os **cliques são sintéticos**: as métricas medem o quanto o modelo recupera o padrão simulado,
  não o comportamento real de leitores.
