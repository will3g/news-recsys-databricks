"""Helpers para montar os notebooks com nbformat (células padrão e utilitários)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import Any

from nbformat.v4 import new_code_cell, new_markdown_cell


def md(text: str) -> Any:
    return new_markdown_cell(dedent(text).strip("\n"))


def code(text: str) -> Any:
    return new_code_cell(dedent(text).strip("\n"))


def header(number: str, title: str, subtitle: str) -> Any:
    return md(
        f"""
        # {number} · {title}

        *{subtitle}*

        > **FIAP Pós-Tech · Fase 5 (MLOps)** — Recomendação de notícias com MLOps no Databricks.
        > Matérias **reais** (sitemap do O Globo) · usuários e cliques **sintéticos**.
        """
    )


def source_cell(rel_path: str, root: Path) -> Any:
    """Mostra um arquivo do pacote: o notebook 'espelha' o código de produção."""
    content = (root / rel_path).read_text(encoding="utf-8").rstrip()
    return code(f"# {rel_path}  (somente leitura — o código de verdade está em src/)\n{content}")


PIP_CELL = code(
    """
    # Célula 1 — dependências (sempre a primeira: o restartPython apaga as variáveis)
    %pip install -q -r ../requirements-databricks.txt
    dbutils.library.restartPython()
    """
)

BOOTSTRAP_CELL = code(
    """
    # Célula 2 — src/ no sys.path + widgets (= parâmetros do Job) -> settings
    import sys
    from pathlib import Path


    def _find_src() -> Path:
        candidates = [Path.cwd().parent / "src"]
        try:  # fallback: caminho do notebook no workspace
            ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
            candidates.append(Path("/Workspace" + ctx.notebookPath().get()).parent.parent / "src")
        except Exception:  # noqa: BLE001
            pass
        for c in candidates:
            if (c / "news_recsys").is_dir():
                return c.resolve()
        raise FileNotFoundError(f"src/ não encontrado em {candidates}")


    SRC = _find_src()
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    ROOT = SRC.parent

    from news_recsys.config import Settings

    dbutils.widgets.text("catalog", "workspace")
    dbutils.widgets.text("schema", "news_recsys_dev")
    dbutils.widgets.text("n_users", "300")
    dbutils.widgets.text("seed", "42")

    settings = Settings(_env_file=None).with_overrides(
        catalog=dbutils.widgets.get("catalog"),
        schema_name=dbutils.widgets.get("schema"),
        n_users=dbutils.widgets.get("n_users"),
        seed=dbutils.widgets.get("seed"),
    )
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {settings.catalog}.{settings.schema_name}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {settings.catalog}.{settings.schema_name}.{settings.volume}")
    print(f"schema ..... {settings.catalog}.{settings.schema_name}")
    print(f"modelo ..... {settings.model_fqn}")
    print(f"usuários ... {settings.n_users} (seed={settings.seed})")
    """
)

MLFLOW_CELL = code(
    """
    # MLflow: experimento por usuário + registro de modelos no Unity Catalog
    import mlflow
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    ME = w.current_user.me().user_name
    EXPERIMENT = f"/Users/{ME}/news_recsys_{settings.schema_name}"
    mlflow.set_experiment(EXPERIMENT)
    mlflow.set_registry_uri("databricks-uc")
    print("experimento:", EXPERIMENT)
    """
)

LOAD_SILVER_CELL = code(
    """
    # Dados de entrada: catálogo (bronze) + usuários e cliques (silver)
    import pandas as pd

    articles = spark.table(settings.table("bronze_articles")).toPandas()
    window = spark.table(settings.table("silver_catalog_window")).toPandas()["article_id"]
    articles = articles[articles["article_id"].isin(window)].reset_index(drop=True)
    users = spark.table(settings.table("silver_users")).toPandas()
    clicks = spark.table(settings.table("silver_interactions")).toPandas()
    clicks["event_ts"] = pd.to_datetime(clicks["event_ts"], utc=True)
    print(f"{len(articles)} matérias · {len(users)} usuários · {len(clicks)} cliques")
    """
)
