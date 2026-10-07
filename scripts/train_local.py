"""Pipeline completo LOCAL (sem Databricks): catálogo → simulação → treino → recomendações.

Serve para (1) validar o código antes do Databricks e (2) gerar ``app/sample_data/``, os dados
que o app usa quando não há conexão com o Lakehouse.

Uso: python -m scripts.train_local [--catalog data/articles_snapshot.json] [--sample-users 60]
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from news_recsys.config import Settings
from news_recsys.ingestion.catalog import load_catalog
from news_recsys.monitoring import recs_report
from news_recsys.simulation import SimulationConfig, simulate
from news_recsys.training import best_candidate, refit_full, train_candidates

SAMPLE_DIR = Path("app/sample_data")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("data/articles_snapshot.json"))
    parser.add_argument("--sample-users", type=int, default=60)
    parser.add_argument("--no-sample", action="store_true", help="não grava app/sample_data")
    args = parser.parse_args()
    s = Settings(_env_file=None)

    articles = pd.DataFrame(load_catalog(args.catalog))
    if articles.empty:
        raise SystemExit(f"catálogo vazio: {args.catalog} — rode `make fetch-sitemap`")
    cfg = SimulationConfig(
        n_users=s.n_users, mean_clicks_per_user=s.mean_clicks_per_user, seed=s.seed
    )
    users, clicks = simulate(articles, cfg)
    print(f"{len(articles)} matérias · {len(users)} usuários sintéticos · {len(clicks)} cliques\n")

    results = train_candidates(clicks, articles, k=s.k, test_fraction=s.test_fraction)
    header = ("candidato", "NDCG@10", "P@10", "R@10", "Hit@10", "cobert.")
    print(f"{header[0]:32s}" + "".join(f"{h:>9s}" for h in header[1:]))
    for r in results:
        m = r.metrics
        cols = ("ndcg_at_k", "precision_at_k", "recall_at_k", "hit_rate_at_k", "catalog_coverage")
        print(f"{r.label:32s}" + "".join(f"{m[c]:9.4f}" for c in cols))
    best = best_candidate(results, s.promotion_metric)
    print(f"\nvencedor ({s.promotion_metric}): {best.label}")

    model = refit_full(best, clicks, articles)
    recs = model.recommend(users["user_id"].tolist(), k=s.k)
    print(
        "monitoramento:", {k: round(v, 3) for k, v in recs_report(recs, clicks, articles).items()}
    )

    if args.no_sample:
        return
    sample_users = users.groupby("persona").head(max(1, args.sample_users // 8))["user_id"]
    write_sample(articles, users, clicks, recs, results, best, set(sample_users))


def write_sample(articles, users, clicks, recs, results, best, sample_users: set[str]) -> None:
    """Mesmo formato das tabelas do Lakehouse lidas pelo app (ver app/data_access.py)."""
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    meta = articles[["article_id", "title", "url", "section", "image_url", "published_at"]]
    u = users[users["user_id"].isin(sample_users)].copy()
    u["section_prefs"] = u["section_prefs"].map(lambda d: {k: v for k, v in d.items() if v > 0.02})
    u[["user_id", "persona"]].to_parquet(SAMPLE_DIR / "users.parquet", index=False)
    c = clicks[clicks["user_id"].isin(sample_users)].merge(meta, on="article_id")
    c.to_parquet(SAMPLE_DIR / "interactions.parquet", index=False)
    r = recs[recs["user_id"].isin(sample_users)].merge(meta, on="article_id")
    r["model_version"] = "local"
    r["generated_at"] = now
    r.to_parquet(SAMPLE_DIR / "recommendations.parquet", index=False)
    metrics = pd.DataFrame(
        [
            {
                "evaluated_at": now,
                "model_version": "local",
                "candidate": res.label,
                "metric": k,
                "value": v,
                "promoted": res is best,
            }
            for res in results
            for k, v in res.metrics.items()
        ]
    )
    metrics.to_parquet(SAMPLE_DIR / "model_metrics.parquet", index=False)
    print(f"\namostra do app gravada em {SAMPLE_DIR}/ ({len(sample_users)} usuários)")


if __name__ == "__main__":
    main()
