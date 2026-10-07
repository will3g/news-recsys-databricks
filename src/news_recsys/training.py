"""Pipeline de treino puro (sem MLflow): split → fit → avaliação de cada candidato.

Os notebooks embrulham isto com MLflow; os testes e o ``make train-local`` usam direto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from news_recsys.evaluation.metrics import evaluate_model
from news_recsys.evaluation.split import temporal_split
from news_recsys.models import MODEL_REGISTRY
from news_recsys.models.base import Recommender

DEFAULT_CANDIDATES: list[tuple[str, dict[str, Any]]] = [
    ("popularidade", {"recency_half_life_h": 24.0}),
    ("item_cf", {"n_neighbors": 50}),
    ("svd", {"n_components": 16}),
    ("svd", {"n_components": 32}),
]


@dataclass
class CandidateResult:
    name: str
    params: dict[str, Any]
    metrics: dict[str, float]
    model: Recommender = field(repr=False)

    @property
    def label(self) -> str:
        suffix = ",".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.name}({suffix})"


def build_model(name: str, params: dict[str, Any]) -> Recommender:
    if name not in MODEL_REGISTRY:
        raise KeyError(f"modelo desconhecido: {name} (opções: {sorted(MODEL_REGISTRY)})")
    return MODEL_REGISTRY[name](**params)


def train_candidates(
    interactions: pd.DataFrame,
    articles: pd.DataFrame,
    candidates: list[tuple[str, dict[str, Any]]] | None = None,
    k: int = 10,
    test_fraction: float = 0.2,
) -> list[CandidateResult]:
    """Treina e avalia cada candidato no MESMO split (comparação justa)."""
    train, test = temporal_split(interactions, test_fraction=test_fraction)
    results = []
    for name, params in candidates or DEFAULT_CANDIDATES:
        model = build_model(name, params).fit(train, articles)
        metrics, _ = evaluate_model(model, test, k=k, catalog_size=len(articles))
        results.append(CandidateResult(name, params, metrics, model))
    return results


def best_candidate(results: list[CandidateResult], metric: str = "ndcg_at_k") -> CandidateResult:
    return max(results, key=lambda r: r.metrics[metric])


def refit_full(
    result: CandidateResult, interactions: pd.DataFrame, articles: pd.DataFrame
) -> Recommender:
    """Depois de escolher, re-treina com TODOS os cliques (o modelo de produção)."""
    return build_model(result.name, result.params).fit(interactions, articles)
