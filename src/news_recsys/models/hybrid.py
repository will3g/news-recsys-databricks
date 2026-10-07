"""Híbrido: colaborativo (quem leu X leu Y) + conteúdo (título/editoria parecidos).

score = α · CF_normalizado + (1 − α) · conteúdo_normalizado

O CF é forte em matérias com histórico; o conteúdo cobre as matérias novas (cold start).
O α é um hiperparâmetro: escolhemos comparando candidatos no MLflow.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from news_recsys.models.base import Recommender
from news_recsys.models.content import ContentRecommender
from news_recsys.models.item_cf import ItemCFRecommender


def _row_normalize(scores: np.ndarray) -> np.ndarray:
    """Leva cada linha para [0, 1] (as escalas de CF e conteúdo são diferentes)."""
    top = scores.max(axis=1, keepdims=True)
    return np.divide(scores, top, out=np.zeros_like(scores, dtype=float), where=top > 0)


class HybridRecommender(Recommender):
    name = "hibrido"

    def __init__(
        self, alpha: float = 0.4, n_neighbors: int = 50, recency_half_life_h: float | None = 24.0
    ) -> None:
        super().__init__()
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha deve estar entre 0 e 1")
        self.alpha = alpha
        self.n_neighbors = n_neighbors
        self.recency_half_life_h = recency_half_life_h
        self.cf = ItemCFRecommender(n_neighbors=n_neighbors)
        self.content = ContentRecommender(recency_half_life_h=recency_half_life_h)

    def _fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> None:
        self.cf.fit(interactions, articles)
        self.content.fit(interactions, articles)
        # mesmos dados → mesmos índices de usuário/matéria nos três modelos
        assert list(self.cf.user_ids) == list(self.user_ids)
        assert list(self.content.user_ids) == list(self.user_ids)

    def _score(self, user_idx: np.ndarray) -> np.ndarray:
        cf = _row_normalize(self.cf._score(user_idx))
        content = _row_normalize(self.content._score(user_idx))
        return self.alpha * cf + (1 - self.alpha) * content

    def params(self) -> dict[str, Any]:
        return {
            "alpha": self.alpha,
            "n_neighbors": self.n_neighbors,
            "recency_half_life_h": self.recency_half_life_h,
        }
