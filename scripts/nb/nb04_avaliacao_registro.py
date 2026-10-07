"""Notebook 04 — Quality gate champion/challenger e alias no Unity Catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import BOOTSTRAP_CELL, MLFLOW_CELL, PIP_CELL, code, header, md, source_cell


def cells(root: Path) -> list[Any]:
    return [
        header("04", "Avaliação e registro", "Champion × challenger: só promove se for melhor"),
        md(
            """
            ## Por que um *quality gate*?

            O pipeline re-treina **todo dia, sozinho**. Se um dia os dados vierem estranhos (sitemap
            quebrado, bug na simulação), o modelo novo pode ser pior — e ninguém está olhando.

            Regra: a versão nova (*challenger*) só recebe o alias **`@champion`** se o NDCG@10 dela
            **superar** o do campeão atual. O app e a inferência batch sempre usam `@champion`,
            nunca "a última versão". **Rollback** = apontar o alias para a versão anterior.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        MLFLOW_CELL,
        md("### `registry.py`"),
        source_cell("src/news_recsys/registry.py", root),
        md("### Execução: quem é o desafiante e quem é o campeão?"),
        code(
            """
            import pandas as pd
            from mlflow import MlflowClient

            from news_recsys.registry import champion_metrics, decide_promotion, set_champion

            client = MlflowClient(registry_uri="databricks-uc")
            version = dbutils.jobs.taskValues.get(taskKey="treino", key="model_version", default="", debugValue="")
            if not version:  # execução interativa: pega a versão mais recente
                version = max(client.search_model_versions(f"name='{settings.model_fqn}'"), key=lambda v: int(v.version)).version
            candidate = client.get_model_version(settings.model_fqn, version)
            candidate_metrics = client.get_run(candidate.run_id).data.metrics
            current = champion_metrics(settings.model_fqn)

            pd.DataFrame(
                {"desafiante (v" + str(version) + ")": candidate_metrics, "campeão atual": current or {}}
            ).loc[["ndcg_at_k", "precision_at_k", "recall_at_k", "hit_rate_at_k", "catalog_coverage", "cold_hit_rate_at_k"]].round(4)
            """
        ),
        md("### Execução: a decisão"),
        code(
            """
            decision = decide_promotion(candidate_metrics, current, settings.promotion_metric, settings.min_improvement)
            print("PROMOVER" if decision.promote else "MANTER CAMPEÃO", "—", decision.reason)

            client.set_model_version_tag(settings.model_fqn, version, "gate_decision", "promoted" if decision.promote else "rejected")
            client.set_model_version_tag(settings.model_fqn, version, "gate_reason", decision.reason)
            if decision.promote:
                champ = set_champion(settings.model_fqn, version)
                print(f"@champion -> versão {champ.version}")
            """
        ),
        md(
            """
            ### Execução: histórico de métricas (tabela `model_metrics`)

            Gravamos as métricas de **todos os candidatos** desta execução (lidas das runs filhas
            via `mlflow.search_runs`). O app mostra essa tabela na aba "Modelo" e o notebook 06 usa
            para acompanhar a tendência.
            """
        ),
        code(
            """
            from datetime import UTC, datetime

            children = mlflow.search_runs(filter_string=f"tags.mlflow.parentRunId = '{candidate.run_id}'")
            winner = client.get_run(candidate.run_id).data.params.get("winner")
            now = datetime.now(UTC).isoformat(timespec="seconds")
            metric_names = ["ndcg_at_k", "precision_at_k", "recall_at_k", "hit_rate_at_k", "catalog_coverage", "cold_hit_rate_at_k"]
            rows = [
                {
                    "evaluated_at": now,
                    "model_version": str(version),
                    "candidate": run["tags.mlflow.runName"],
                    "metric": m,
                    "value": float(run[f"metrics.{m}"]),
                    "promoted": bool(decision.promote and run["tags.mlflow.runName"] == winner),
                }
                for _, run in children.iterrows()
                for m in metric_names
            ]
            spark.createDataFrame(pd.DataFrame(rows)).write.mode("append").saveAsTable(settings.table("model_metrics"))
            spark.table(settings.table("model_metrics")).orderBy("evaluated_at", ascending=False).limit(10).toPandas()
            """
        ),
        md("### Versões e aliases no Unity Catalog"),
        code(
            """
            pd.DataFrame(
                [
                    {"versão": v.version, "aliases": list(v.aliases or []), "gate": (v.tags or {}).get("gate_decision"), "run_id": v.run_id}
                    for v in client.search_model_versions(f"name='{settings.model_fqn}'")
                ]
            ).sort_values("versão", key=lambda s: s.astype(int), ascending=False)
            """
        ),
        md(
            """
            ### O que percebemos?

            - A promoção é **automática e auditável** (tags `gate_decision`/`gate_reason` em cada versão).
            - Consumidores dependem do **alias**, não do número da versão → deploy e rollback sem mexer no app.
            - Rode o Job duas vezes com o mesmo `seed`: a segunda versão empata e **não** é promovida.

            **Próximo:** `05_inferencia_batch`.
            """
        ),
    ]
