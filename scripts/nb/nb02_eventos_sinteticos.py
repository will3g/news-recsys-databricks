"""Notebook 02 — Silver: usuários e cliques sintéticos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import BOOTSTRAP_CELL, PIP_CELL, code, header, md, source_cell


def cells(root: Path) -> list[Any]:
    return [
        header(
            "02",
            "Eventos sintéticos — camada Silver",
            "Personas, cliques e o problema de não ter dados de usuário",
        ),
        md(
            """
            ## O elefante na sala: não temos cliques reais

            Um recomendador personalizado aprende com **comportamento** (quem leu o quê). Esse
            dado é privado — fica no *analytics* do portal. Então **simulamos**, de forma explícita
            e reproduzível (`seed`):

            - 8 **personas** (politizado, investidor, torcedor, carioca, cultural, ...), cada uma
              com preferência por editorias — e cada usuário é uma variação da sua persona;
            - **subeditorias favoritas** (ex.: `esportes/futebol`) → o "gosto fino" que só a
              filtragem colaborativa consegue capturar;
            - **viés de popularidade** (matérias que "viralizam") e **de recência** (notícia velha
              perde interesse — meia-vida de 12 h).

            > Em produção, esta tabela viria de eventos reais (clickstream). **O resto do pipeline
            > não muda** — é por isso que a simulação é só uma etapa isolada.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        md("### `simulation.py`"),
        source_cell("src/news_recsys/simulation.py", root),
        md(
            """
            ### Execução: janela de catálogo + simulação

            Notícia envelhece rápido: usamos só as matérias dos **últimos 3 dias** (a "janela"
            recomendável). A janela vira uma tabela para que treino e inferência usem o mesmo catálogo.
            """
        ),
        code(
            """
            import pandas as pd

            from news_recsys.simulation import SimulationConfig, simulate

            bronze = spark.table(settings.table("bronze_articles")).toPandas()
            published = pd.to_datetime(bronze["published_at"], utc=True, format="mixed", errors="coerce")
            articles = bronze[published >= published.max() - pd.Timedelta(days=3)].reset_index(drop=True)
            print(f"janela: {len(articles)} de {len(bronze)} matérias (últimos 3 dias)")

            cfg = SimulationConfig(n_users=settings.n_users, mean_clicks_per_user=settings.mean_clicks_per_user, seed=settings.seed)
            users, clicks = simulate(articles, cfg)
            print(f"{len(users)} usuários · {len(clicks)} cliques · {clicks.groupby('user_id').size().mean():.1f} cliques/usuário")
            users.head(8)
            """
        ),
        md("### Execução: gravando as tabelas silver"),
        code(
            """
            import json

            from pyspark.sql import functions as F

            spark.createDataFrame(articles[["article_id"]]).write.mode("overwrite").saveAsTable(settings.table("silver_catalog_window"))
            users_out = users.assign(  # dict/list -> JSON/str: tipos simples e portáveis no Delta
                section_prefs=users["section_prefs"].map(json.dumps),
                favorite_subsections=users["favorite_subsections"].map(lambda v: ",".join(v)),
            )
            spark.createDataFrame(users_out).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(settings.table("silver_users"))
            (
                spark.createDataFrame(clicks)
                .withColumn("event_ts", F.col("event_ts").cast("timestamp"))
                .write.mode("overwrite").option("overwriteSchema", "true")
                .saveAsTable(settings.table("silver_interactions"))
            )
            for t in ("silver_catalog_window", "silver_users", "silver_interactions"):
                print(f"{settings.table(t):55s} {spark.table(settings.table(t)).count():6d} linhas")
            """
        ),
        md(
            """
            ### Visualizando: cada persona lê coisas diferentes?

            Se a simulação está boa, cada linha do mapa de calor tem "cor" concentrada nas
            editorias da persona — é esse padrão que os modelos vão tentar aprender.
            """
        ),
        code(
            """
            import matplotlib.pyplot as plt

            section = articles.set_index("article_id")["section"]
            mix = pd.crosstab(clicks["persona"], clicks["article_id"].map(section), normalize="index")
            mix = mix.loc[:, mix.max().sort_values(ascending=False).index[:10]]

            fig, ax = plt.subplots(figsize=(10, 4.5))
            im = ax.imshow(mix.to_numpy(), cmap="Blues", aspect="auto", vmin=0, vmax=0.8)
            ax.set_xticks(range(len(mix.columns)), mix.columns, rotation=40, ha="right")
            ax.set_yticks(range(len(mix.index)), mix.index)
            for (i, j), v in pd.DataFrame(mix.to_numpy()).stack().items():
                ax.text(j, i, f"{v:.0%}" if v >= 0.05 else "", ha="center", va="center", fontsize=8)
            ax.set_title("Fração das leituras por editoria, por persona")
            fig.colorbar(im, ax=ax, shrink=0.8)
            fig.tight_layout()
            display(fig)
            """
        ),
        md(
            """
            ### O que percebemos?

            - O dado de comportamento é o **ativo mais valioso** de um recomendador — e o mais
              sensível (LGPD). Aqui ele é sintético e público.
            - A simulação é **determinística** (`seed`): mesma entrada → mesmos cliques → métricas
              comparáveis entre execuções.
            - O formato (user, item, timestamp) é o mesmo de um log real.

            **Próximo:** `03_treino_mlflow`.
            """
        ),
    ]
