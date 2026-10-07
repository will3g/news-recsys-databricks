"""Baixa o sitemap do O Globo e grava o catálogo de matérias em JSON.

Roda no GitHub Actions (cron diário) — o Databricks Free Edition não tem internet de saída
liberada. Uso:
    python -m scripts.fetch_sitemap --out data/raw/catalog_20261007.json
    python -m scripts.fetch_sitemap --merge-into data/articles_snapshot.json
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from news_recsys.config import Settings
from news_recsys.ingestion.catalog import fetch_catalog, load_catalog, merge_records, save_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="grava só o catálogo de hoje neste arquivo")
    parser.add_argument("--merge-into", type=Path, help="une ao catálogo acumulado neste arquivo")
    parser.add_argument("--sitemap-url", default=Settings(_env_file=None).sitemap_url)
    args = parser.parse_args()
    if not (args.out or args.merge_into):
        parser.error("informe --out e/ou --merge-into")

    records = fetch_catalog(args.sitemap_url)
    print(f"{len(records)} matérias recomendáveis no sitemap")
    print("editorias:", dict(Counter(r["section"] for r in records).most_common(8)))
    if args.out:
        save_catalog(records, args.out)
        print("->", args.out)
    if args.merge_into:
        merged = merge_records(load_catalog(args.merge_into), records)
        save_catalog(merged, args.merge_into)
        print(f"-> {args.merge_into} ({len(merged)} matérias acumuladas)")


if __name__ == "__main__":
    main()
