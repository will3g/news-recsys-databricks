"""Notebook 06 — Monitoramento: cobertura, drift de editorias e tendência das métricas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import (
    BOOTSTRAP_CELL,
    LOAD_SILVER_CELL,
    PIP_CELL,
    code,
    header,
    md,
    source_cell,
)


def cells(root: Path) -> list[Any]:
    return [
        header(
            "06", "Monitoramento", "O modelo continua bom? As recomendações continuam diversas?"
        ),
        md(
            """
            ## O que monitorar num recomendador

            | Sinal | Pergunta | Como medimos |
            |---|---|---|
            | **Qualidade offline** | o modelo novo é tão bom quanto os anteriores? | tendência do NDCG@10 (`model_metrics`) |
            | **Cobertura** | estamos recomendando sempre as mesmas 20 matérias? | % do catálogo recomendado |
            | **Drift / bolha** | recomendamos o que as pessoas leem, ou só política? | **PSI** entre editorias lidas × recomendadas |
            | **Qualidade online** | as pessoas clicam? | CTR em produção / teste A/B (fora do escopo) |

            PSI (*Population Stability Index*): < 0,1 estável · 0,1–0,2 atenção · > 0,2 mudança relevante.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        LOAD_SILVER_CELL,
        md("### `monitoring.py`"),
        source_cell("src/news_recsys/monitoring.py", root),
        md("### Execução: relatório desta execução → `recs_monitoring`"),
        code(
            """
            from news_recsys.monitoring import PSI_ALERT, distribution, recs_report, report_to_records

            gold = spark.table(settings.table("gold_user_recommendations")).toPandas()
            report = recs_report(gold, clicks, articles)
            version = str(gold["model_version"].iloc[0])
            spark.createDataFrame(pd.DataFrame(report_to_records(report, model_version=version))).write.mode("append").saveAsTable(
                settings.table("recs_monitoring")
            )
            status = "ALERTA" if report["psi_sections_recs_vs_reads"] > PSI_ALERT else "ok"
            print(f"PSI editorias (lidas × recomendadas) = {report['psi_sections_recs_vs_reads']:.3f} -> {status}")
            pd.Series(report).round(4).to_frame("valor")
            """
        ),
        md("### Visualizando: o que as pessoas leem × o que recomendamos"),
        code(
            """
            import matplotlib.pyplot as plt

            section = articles.set_index("article_id")["section"]
            dist = pd.DataFrame(
                {"lidas": distribution(clicks["article_id"].map(section).dropna()), "recomendadas": distribution(gold["section"].dropna())}
            ).fillna(0).sort_values("lidas", ascending=True)
            ax = dist.plot.barh(figsize=(8, 4.5))
            ax.set_title("Distribuição por editoria")
            ax.set_xlabel("fração")
            plt.tight_layout()
            display(ax.figure)
            """
        ),
        md("### Execução: tendência do campeão ao longo dos dias"),
        code(
            """
            mm = spark.table(settings.table("model_metrics")).toPandas()
            trend = mm[(mm["metric"] == "ndcg_at_k") & (mm["promoted"])].sort_values("evaluated_at")
            if len(trend) > 1:
                ax = trend.plot(x="evaluated_at", y="value", marker="o", figsize=(8, 3.5), legend=False, title="NDCG@10 do campeão")
                plt.tight_layout()
                display(ax.figure)
            mm.pivot_table(index=["evaluated_at", "model_version"], columns="metric", values="value", aggfunc="max").tail(5).round(4)
            """
        ),
        md(
            """
            ### Um alerta em SQL (Databricks SQL → Alerts)

            ```sql
            SELECT value AS psi
            FROM workspace.news_recsys.recs_monitoring
            WHERE metric = 'psi_sections_recs_vs_reads'
            ORDER BY generated_at DESC
            LIMIT 1
            -- condição: psi > 0.2  → e-mail para o time
            ```
            """
        ),
        md(
            """
            ## Fechando o ciclo de MLOps

            ```
            dados novos (GitHub Actions) → bronze → silver → treino (MLflow) → gate → @champion
                  ↑                                                                     │
                  └──── monitoramento ◄──── gold ◄──── inferência batch ◄──────────────┘
            ```

            ### O que explorar a seguir

            - **Teste A/B** online: CTR do campeão × desafiante com tráfego real.
            - **Modelos híbridos** (conteúdo + colaborativo) para o *cold start* de matérias.
            - **Feature Store** e **Model Serving** para recomendação em tempo real.
            - **Lakehouse Monitoring** e dashboards AI/BI sobre `recs_monitoring`.
            """
        ),
    ]
