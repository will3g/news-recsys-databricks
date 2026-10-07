"""Notebook 01 — Camada Bronze: catálogo de matérias."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import BOOTSTRAP_CELL, PIP_CELL, code, header, md, source_cell


def cells(root: Path) -> list[Any]:
    return [
        header(
            "01",
            "Ingestão — camada Bronze",
            "Do sitemap (via GitHub Actions) para a tabela bronze_articles",
        ),
        md(
            """
            ## De onde vêm as matérias?

            Do **sitemap de notícias** do O Globo (`news.xml`): URL, título, data e imagem das
            ~700 matérias das últimas 48 h. A **editoria** sai da própria URL
            (`/economia/...`, `/esportes/futebol/...`).

            **Quem baixa é o GitHub Actions**, não o Databricks: na Free Edition a internet de saída
            é restrita. O workflow `ingest.yml` roda todo dia, grava um JSON e envia para o
            **Volume** `raw/catalog/`. Este notebook lê o que estiver lá (e, se o Volume estiver
            vazio, usa o snapshot `data/articles_snapshot.json` que vem no bundle).

            Guardamos **só metadados** — o app linka para o site original.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        md("### `features/sections.py` e `ingestion/catalog.py`"),
        source_cell("src/news_recsys/features/sections.py", root),
        source_cell("src/news_recsys/ingestion/catalog.py", root),
        md("### Execução: lendo os JSONs do Volume"),
        code(
            """
            import json

            import pandas as pd

            from news_recsys.ingestion.catalog import load_catalog, merge_records

            raw_dir = Path(settings.volume_path("catalog"))
            raw_dir.mkdir(parents=True, exist_ok=True)
            files = sorted(raw_dir.glob("*.json"))
            if not files:  # Volume vazio (primeira execução): usa o snapshot do repositório
                files = [ROOT / "data" / "articles_snapshot.json"]
                print("Volume vazio — usando o snapshot do bundle:", files[0].name)

            records: list[dict] = []
            for f in files:
                records = merge_records(records, load_catalog(f))
                print(f"{f.name:40s} acumulado: {len(records)} matérias")

            catalog_pdf = pd.DataFrame(records)
            catalog_pdf["section"].value_counts().rename("matérias").to_frame()
            """
        ),
        md(
            """
            ### Execução: `MERGE` na `bronze_articles`

            O catálogo **acumula** dia após dia. `MERGE` é o *upsert* do Delta: atualiza quem já
            existe (pela chave `article_id`) e insere o que é novo — sem duplicar.
            """
        ),
        code(
            """
            from pyspark.sql.types import StringType, StructField, StructType

            BRONZE = settings.table("bronze_articles")
            cols = ["article_id", "url", "title", "section", "subsection", "published_at", "image_url", "first_seen_at"]
            schema = StructType([StructField(c, StringType(), True) for c in cols])
            spark.createDataFrame(catalog_pdf[cols], schema=schema).createOrReplaceTempView("novas_materias")

            spark.sql(f"CREATE TABLE IF NOT EXISTS {BRONZE} ({', '.join(f'{c} STRING' for c in cols)}, ingested_at TIMESTAMP)")
            insert_cols = ", ".join(cols)
            insert_vals = ", ".join(f"s.{c}" for c in cols)
            result = spark.sql(
                f\"\"\"
                MERGE INTO {BRONZE} AS t
                USING novas_materias AS s
                ON t.article_id = s.article_id
                WHEN MATCHED THEN UPDATE SET t.title = s.title, t.image_url = s.image_url, t.ingested_at = current_timestamp()
                WHEN NOT MATCHED THEN INSERT ({insert_cols}, ingested_at) VALUES ({insert_vals}, current_timestamp())
                \"\"\"
            )
            result.toPandas()
            """
        ),
        code(
            """
            print(BRONZE, "->", spark.table(BRONZE).count(), "matérias")
            spark.table(BRONZE).select("section", "title", "published_at").orderBy("published_at", ascending=False).limit(8).toPandas()
            """
        ),
        md("### O Delta guarda o histórico de cada escrita"),
        code(
            """
            spark.sql(f"DESCRIBE HISTORY {BRONZE}").select("version", "timestamp", "operation", "operationMetrics").limit(5).toPandas()
            """
        ),
        md(
            """
            ### O que percebemos?

            - Coleta (GitHub Actions) e processamento (Databricks) estão **desacoplados** pelo Volume.
            - `MERGE` torna a ingestão **idempotente**: rodar duas vezes não duplica nada.
            - `DESCRIBE HISTORY` = auditoria grátis (dá até para consultar a tabela "como era ontem").

            **Próximo:** `02_eventos_sinteticos`.
            """
        ),
    ]
