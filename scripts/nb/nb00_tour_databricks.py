"""Notebook 00 — Tour pelo Databricks (para alunos E para quem vai dar a aula)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import BOOTSTRAP_CELL, PIP_CELL, code, header, md


def cells(root: Path) -> list[Any]:
    return [
        header(
            "00", "Tour pelo Databricks", "O mínimo de Databricks para entender (e explicar) a aula"
        ),
        md(
            """
            ## O que é o Databricks, em uma frase?

            Uma plataforma onde **dados, código, modelos e agendamentos vivem juntos e governados**:
            você guarda tabelas, roda notebooks em Spark/Python, registra experimentos e modelos
            e agenda pipelines — tudo no mesmo lugar, com o mesmo controle de acesso.

            | Ideia | No Databricks | Analogia |
            |---|---|---|
            | Onde ficam os dados | **Unity Catalog**: `catálogo.schema.tabela` | banco → schema → tabela |
            | Arquivos brutos | **Volume**: `/Volumes/catálogo/schema/volume/` | um "bucket" governado |
            | Tabelas | **Delta Lake** (Parquet + histórico + ACID) | tabela de banco com `git log` |
            | Rodar código | **Notebook** em **serverless compute** | Jupyter, mas sem gerenciar máquina |
            | Experimentos | **MLflow Experiments** | planilha automática de treinos |
            | Modelos | **Models** no Unity Catalog (versões + aliases) | "releases" do modelo |
            | Agendar | **Jobs** (Jobs & Pipelines) | cron com DAG, retries e logs |
            | Infra como código | **Asset Bundles** (`databricks.yml`) | Terraform do projeto |
            """
        ),
        md(
            """
            ## Onde clicar (menu lateral esquerdo)

            | Menu | O que vamos ver nesta aula |
            |---|---|
            | **Workspace** | pasta `.bundle/news-recsys-databricks/...` com notebooks e `src/` (deploy do bundle) |
            | **Catalog** | `workspace` → `news_recsys_dev` → tabelas `bronze_*`, `silver_*`, `gold_*` e o Volume `raw` |
            | **Jobs & Pipelines** | job `[dev ...] news-recsys-pipeline` (6 tasks) — histórico de execuções |
            | **Experiments** | `news_recsys_...` — cada treino é uma *run* com parâmetros e métricas |
            | **Models** (dentro do Catalog) | `news_recommender` — versões e alias `@champion` |
            | **SQL Warehouses** | o warehouse que o app Streamlit usa para ler a tabela gold |

            > **Dica para a aula:** deixe essas abas abertas antes de começar.
            """
        ),
        md(
            """
            ## O que vamos construir

            ```
            GitHub Actions (cron) ──► sitemap O Globo ──► JSON ──► Volume raw
                                                                     │
               01 bronze_articles ◄──────────────────────────────────┘
                     │
               02 silver_users + silver_interactions   (cliques SINTÉTICOS)
                     │
               03 treino: popularidade × item-CF × SVD   ──► MLflow (runs) ──► Unity Catalog (versão N)
                     │
               04 quality gate: N supera o @champion?  ──► sim: alias @champion = N
                     │
               05 inferência batch com @champion ──► gold_user_recommendations
                     │                                        │
               06 monitoramento (cobertura, drift)           └──► App Streamlit (Community Cloud)
            ```

            Os notebooks 01→06 são as **tasks do Job**. O GitHub Actions faz CI (testes), CD
            (deploy do bundle) e o gatilho diário. O Terraform cria o repositório e os secrets.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        md("### Execução: quem sou eu e o que existe no catálogo?"),
        code(
            """
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            print("usuário:  ", w.current_user.me().user_name)
            print("workspace:", w.config.host)
            spark.sql(f"SHOW TABLES IN {settings.catalog}.{settings.schema_name}").toPandas()
            """
        ),
        md(
            """
            ### Execução: Spark × pandas em 10 segundos

            `spark` é um DataFrame **distribuído** (e preguiçoso: só executa no `.toPandas()`,
            `.count()`, `display()`...). Nossos dados são pequenos, então treinamos com pandas e
            scikit-learn no *driver* — e usamos Spark para ler/gravar tabelas Delta.
            """
        ),
        code(
            """
            df = spark.range(1_000_000).selectExpr("id", "id % 7 AS resto")
            print(type(df).__name__, "->", df.count(), "linhas (calculado no cluster serverless)")
            df.groupBy("resto").count().orderBy("resto").toPandas()
            """
        ),
        md(
            """
            ### O que percebemos?

            - Tudo tem **endereço no catálogo** (`workspace.news_recsys_dev.tabela`) e permissões.
            - Não criamos nenhuma máquina: serverless liga e desliga sozinho.
            - O schema e o Volume foram criados pelo bootstrap (`CREATE ... IF NOT EXISTS`) —
              rodar de novo não quebra nada (**idempotência**).

            **Próximo:** `01_ingestao_bronze`.
            """
        ),
    ]
