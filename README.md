# Recomendação de notícias com MLOps no Databricks

Um recomendador de notícias que **se re-treina sozinho todo dia** e só troca o modelo em
produção quando o novo é melhor.

- **Dados:** matérias **reais** do sitemap do O Globo + leitores e cliques **sintéticos**.
- **Modelos:** popularidade (baseline) Vs item-CF Vs **híbrido** (recomenda até matéria nova).
- **MLOps:** MLflow, Unity Catalog (`@champion`), quality gate, Job agendado, monitoramento.
- **Entrega:** app Streamlit + CI/CD no GitHub Actions + GitHub configurado com Terraform.

```mermaid
flowchart LR
    GH["GitHub Actions<br/>06:00"] -- "1: sitemap" --> V[("Volume")]
    V --> N1["01_dados"] --> N2["02_treino<br/>MLflow + gate"] --> N3["03_recomendacoes"]
    N2 -- "@champion" --> UC[("Unity Catalog")]
    N3 --> G[("gold_recommendations")] --> APP["App Streamlit"]
```

> Detalhes e mais diagramas: [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## Estrutura do projeto

| Pasta / arquivo | Para quê |
|---|---|
| `notebooks/01_dados.ipynb` | sitemap → matérias (`bronze_articles`) + alerta de mudança nos dados (`data_monitoring`) + cliques sintéticos (`silver_*`) |
| `notebooks/02_treino.ipynb` | 3 modelos, MLflow, registro no Unity Catalog e quality gate |
| `notebooks/03_recomendacoes.ipynb` | top-10 de cada leitor (`gold_recommendations`) + monitoramento |
| `databricks.yml`, `resources/job.yml` | o Job (3 tasks) descrito em código (Asset Bundle) |
| `app/streamlit_app.py` | o app (lê a tabela gold; aba "Monte seu perfil" recomenda na hora para um leitor novo; sem conexão, usa `app/sample_data`) |
| `.github/workflows/` | `ci.yml` (lint + validação), `cd.yml` (deploy), `ingest.yml` (cron diário) |
| `infra/github/` | Terraform: repositório, secrets e proteção da `main` |
| `docs/` | arquitetura, guia do professor, roteiro da aula |

> Todo o código do modelo está **dentro dos notebooks**.

## O que é utilizado no Databricks

| Termo | Em uma linha |
|---|---|
| Workspace | o "site" do Databricks da sua conta |
| Unity Catalog | catálogo de dados e modelos: `workspace.news_recsys_dev.tabela` |
| Volume | pasta de arquivos dentro do catálogo (`/Volumes/workspace/news_recsys_dev/raw/`) |
| Delta | formato das tabelas (Parquet + histórico de versões) |
| Serverless | o compute liga sozinho; ninguém cria máquina |
| Job | notebooks encadeados como tasks, com agenda e histórico |
| Asset Bundle | `databricks.yml`: o Job descrito em código; `make deploy` publica |
| MLflow run | um treino registrado (parâmetros + métricas + modelo) |
| Versão / alias | cada registro do modelo vira versão 1, 2, 3...; `@champion` aponta para a que está em uso |

**Três ambientes, um workspace:**
   - `dev` (o seu, pelo `make`)
   - `qa` (merge na `develop`)
   - `prod` (merge na `main`)
   
> Cada um tem schema, Job, modelo e experimento próprios (`news_recsys_<ambiente>`). Qualquer comando do `make` aceita `TARGET=qa` ou `TARGET=prod`.

## Instalação (macOS, Linux e Windows)

| Sistema | Antes de começar |
|---|---|
| macOS | `xcode-select --install` |
| Linux (Ubuntu/Debian) | `sudo apt install -y python3 python3-venv make curl unzip git jq` |
| Windows | PowerShell como administrador: `wsl --install -d Ubuntu-24.04`, depois use o terminal do Ubuntu |

```bash
make doctor        # confere o que está instalado
```

## Mão na massa

1. Conta Free Edition: <https://www.databricks.com/learn/free-edition>.

2. Token: avatar → **Settings** → **Developer** → **Access tokens** → *Generate new token*.

3. No terminal, na pasta do projeto:
```bash
make db-install
make db-configure      # URL do workspace + token
make setup
make deploy
make run               # ~5 min; acompanhe em Jobs & Pipelines
```

4. Para visualizar as recomendações, vai em **SQL Editor**:
```sql
WITH lidas AS (
SELECT u.persona, a.section, count(*) AS n
FROM workspace.news_recsys_dev.silver_clicks c
JOIN workspace.news_recsys_dev.silver_users u USING (user_id)
JOIN workspace.news_recsys_dev.bronze_articles a USING (url)
GROUP BY ALL
),
recomendadas AS (
    SELECT u.persona, g.section, count(*) AS n
    FROM workspace.news_recsys_dev.gold_recommendations g
    JOIN workspace.news_recsys_dev.silver_users u USING (user_id)
    GROUP BY ALL
)
SELECT persona, section,
        round(100 * coalesce(l.n, 0) / sum(l.n) OVER (PARTITION BY persona), 1) AS pct_lidas,
        round(100 * coalesce(r.n, 0) / sum(r.n) OVER (PARTITION BY persona), 1) AS pct_recomendadas
FROM lidas l
FULL JOIN recomendadas r USING (persona, section)
QUALIFY pct_lidas >= 5 OR pct_recomendadas >= 5
ORDER BY persona, pct_lidas DESC
```

5. Volta para o **terminal** e executa:
```bash
make install
make app
```
> Realize os testes locais e veja se está funcionando

6. **GitHub (uma vez):** cria o repositório e liga a esteira.
```bash
make gh-login
make gh-repo
```

7. **Token do GitHub para o Terraform da esteira**
```yml
# TF_GITHUB_TOKEN: Settings → Developer settings → o token → Edit → Repository access
7.1: **Repository access:** *Only select repositories* → `will3g/news-recsys-databricks`
7.2: **Permissions → Repositories → + Add permissions:**
7.3:
.---------------------------------.
| Permissão      | Acesso         |
|----------------|----------------|
| Administration | Read and write |
| Environments   | Read and write |
`---------------------------------´
7.4: *Generate token* (ou *Update*), e copie o valor.
```

8. Secrets e primeiro push:
```bash
make gh-secrets
make gh-push
```

9. **Acompanhe a esteira** em **Actions** → `cd` (develop = QA, main = PROD):
```yml
infra (Terraform) → databricks (setup + deploy + run, ~5 min) → streamlit
```
> Se não disparar: **Actions** → `cd` → *Run workflow* → escolha a branch.

10. **Streamlit Cloud (2 apps):** <https://share.streamlit.io> → *Create app* → *Deploy a public
    app from GitHub*:
```bash
┌────────────────┬───────────────────────────────┬───────────────────────────────┐
│     Campo      │            App QA             │           App PROD            │
├────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Repository     │ will3g/news-recsys-databricks │ will3g/news-recsys-databricks │
├────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Branch         │ develop                       │ main                          │
├────────────────┼───────────────────────────────┼───────────────────────────────┤
│ Main file path │ app/streamlit_app.py          │ app/streamlit_app.py          │
├────────────────┼───────────────────────────────┼───────────────────────────────┤
│ App URL        │ will3g-news-recsys-homolog    │ will3g-news-recsys            │
└────────────────┴───────────────────────────────┴───────────────────────────────┘
```

11. **Secrets de cada app:** *Advanced settings* (ou **Manage app** → ⋮ → *Settings*) → *Secrets*.
    A linha `[databricks]` é obrigatória:
```bash
# EX: http_path = "/sql/1.0/warehouses/a72a5e4a3480ab26" (SQL -> SQL WAREHOUSE)

[databricks]
server_hostname = "<host>.cloud.databricks.com"
http_path = "/sql/1.0/warehouses/<sql-warehouse-http-path-id>"
access_token = "token"
catalog = "workspace"
schema = "news_recsys_<qa|prod>"
```
> Depois: **Manage app** → ⋮ → *Reboot app*.

## Custos

R$ 0: Databricks Free Edition, GitHub Actions (repo público) e Streamlit Community Cloud.

## Limitações conhecidas

- Os cliques são **sintéticos**: as métricas medem o padrão das personas, não leitores reais.
- O state do Terraform fica num Volume do Databricks e não guarda tokens (os secrets são criados pelo `make gh-secrets`).
- O token do Databricks expira: renove no GitHub (`make gh-secrets`) e no Streamlit Cloud.
