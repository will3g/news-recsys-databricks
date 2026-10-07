"""Notebook 05 — Inferência batch com o @champion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import (
    BOOTSTRAP_CELL,
    LOAD_SILVER_CELL,
    MLFLOW_CELL,
    PIP_CELL,
    code,
    header,
    md,
)


def cells(root: Path) -> list[Any]:
    return [
        header(
            "05", "Inferência batch", "Pré-calcular o top-10 de cada usuário — como o mercado faz"
        ),
        md(
            """
            ## Batch ou tempo real?

            | | **Batch** (nosso) | **Tempo real** (Model Serving) |
            |---|---|---|
            | Como | Job calcula o top-10 de todos e grava numa tabela | API calcula a cada requisição |
            | Latência no app | só uma leitura (ms) | inferência a cada clique |
            | Frescor | atualiza a cada execução (diária/horária) | instantâneo |
            | Custo/complexidade | baixo | endpoint sempre de pé, autoscaling |
            | Quando usar | home personalizada, e-mail, push | "porque você acabou de ler X" |

            Muitos portais combinam os dois: **candidatos em batch + reordenação em tempo real**.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        MLFLOW_CELL,
        LOAD_SILVER_CELL,
        md("### Execução: carregando o `@champion` e recomendando para todos"),
        code(
            """
            from datetime import UTC, datetime

            from mlflow import MlflowClient

            champion = MlflowClient(registry_uri="databricks-uc").get_model_version_by_alias(settings.model_fqn, "champion")
            model = mlflow.pyfunc.load_model(f"models:/{settings.model_fqn}@champion")
            print(f"usando {settings.model_fqn} versão {champion.version} (@champion)")

            recs = model.predict(pd.DataFrame({"user_id": users["user_id"]}), params={"k": settings.k})
            meta = articles[["article_id", "title", "url", "section", "image_url", "published_at"]]
            gold = recs.merge(meta, on="article_id", how="left").assign(
                model_version=str(champion.version), generated_at=datetime.now(UTC).isoformat(timespec="seconds")
            )
            print(f"{len(gold)} recomendações para {gold['user_id'].nunique()} usuários")
            gold.head(10)[["user_id", "rank", "section", "title", "score"]]
            """
        ),
        md("### Execução: gravando `gold_user_recommendations`"),
        code(
            """
            GOLD = settings.table("gold_user_recommendations")
            spark.createDataFrame(gold).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(GOLD)
            print(GOLD, "->", spark.table(GOLD).count(), "linhas")
            spark.sql(f"SELECT model_version, generated_at, count(*) AS recs, count(DISTINCT user_id) AS usuarios FROM {GOLD} GROUP BY ALL").toPandas()
            """
        ),
        md(
            """
            ### Faz sentido? Um usuário de cada persona

            O que o usuário leu (editorias) × o que recomendamos. É a "checagem de bom senso" que
            nenhuma métrica substitui.
            """
        ),
        code(
            """
            section = articles.set_index("article_id")["section"]
            sample = users.groupby("persona").head(1)
            rows = []
            for u in sample.itertuples():
                read = clicks.loc[clicks["user_id"] == u.user_id, "article_id"].map(section).value_counts().head(2)
                rec = gold.loc[gold["user_id"] == u.user_id, "section"].value_counts().head(2)
                rows.append({"usuário": u.user_id, "persona": u.persona, "leu (top editorias)": dict(read), "recomendado": dict(rec)})
            pd.DataFrame(rows)
            """
        ),
        md(
            """
            ### O que percebemos?

            - A inferência usa **`@champion`**, não "a última versão" → o gate do notebook 04 protege o app.
            - A tabela gold carrega `model_version`: dá para saber **qual modelo** gerou cada recomendação.
            - O app Streamlit só faz `SELECT ... WHERE user_id = ?` nesta tabela (via SQL warehouse).

            **Próximo:** `06_monitoramento`.
            """
        ),
    ]
