"""Métricas de ranking (Precision/Recall/NDCG/HitRate @K) e cobertura de catálogo."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd


def precision_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return sum(1 for a in list(recommended)[:k] if a in relevant) / k


def recall_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    return len(set(list(recommended)[:k]) & relevant) / len(relevant)


def hit_rate_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(list(recommended)[:k]) & relevant else 0.0


def ndcg_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    """Ganho cumulativo descontado: acertar no topo vale mais que acertar no fim da lista."""
    if not relevant or k <= 0:
        return 0.0
    dcg = sum(1.0 / np.log2(i + 2) for i, a in enumerate(list(recommended)[:k]) if a in relevant)
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return float(dcg / ideal) if ideal else 0.0


def evaluate_recommendations(
    recs: pd.DataFrame, test: pd.DataFrame, k: int, catalog_size: int
) -> dict[str, float]:
    """Média das métricas por usuário do teste + cobertura de catálogo."""
    relevant = test.groupby("user_id")["article_id"].apply(set).to_dict()
    by_user = (
        recs.sort_values(["user_id", "rank"]).groupby("user_id")["article_id"].apply(list).to_dict()
    )
    rows = []
    for user, rel in relevant.items():
        rec = by_user.get(user, [])
        rows.append(
            (
                precision_at_k(rec, rel, k),
                recall_at_k(rec, rel, k),
                ndcg_at_k(rec, rel, k),
                hit_rate_at_k(rec, rel, k),
            )
        )
    arr = np.array(rows) if rows else np.zeros((1, 4))
    n_distinct = recs["article_id"].nunique() if len(recs) else 0
    return {
        "precision_at_k": float(arr[:, 0].mean()),
        "recall_at_k": float(arr[:, 1].mean()),
        "ndcg_at_k": float(arr[:, 2].mean()),
        "hit_rate_at_k": float(arr[:, 3].mean()),
        "catalog_coverage": n_distinct / catalog_size if catalog_size else 0.0,
        "n_users_eval": float(len(rows)),
    }


def evaluate_model(
    model: Any, test: pd.DataFrame, k: int, catalog_size: int
) -> tuple[dict[str, float], pd.DataFrame]:
    """Recomenda para os usuários do teste e mede. Retorna (métricas, recomendações)."""
    users = sorted(test["user_id"].unique())
    recs = model.recommend(users, k=k)
    return evaluate_recommendations(recs, test, k, catalog_size), recs
