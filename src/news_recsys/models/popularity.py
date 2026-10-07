"""Baseline: as matérias mais clicadas (com bônus de recência). Todo recsys começa aqui."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from news_recsys.models.base import Recommender


class PopularityRecommender(Recommender):
    name = "popularidade"

    def __init__(self, recency_half_life_h: float | None = 24.0) -> None:
        super().__init__()
        self.recency_half_life_h = recency_half_life_h
        self._scores = np.array([])

    def _fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> None:
        scores = self.popularity_.astype(float)
        if self.recency_half_life_h:
            published = pd.to_datetime(
                articles["published_at"], utc=True, format="mixed", errors="coerce"
            )
            ref = published.max()
            age_h = ((ref - published).dt.total_seconds() / 3600).fillna(1e6).to_numpy()
            scores = scores * 0.5 ** (np.clip(age_h, 0, None) / self.recency_half_life_h)
        self._scores = scores

    def _cold_start_scores(self) -> np.ndarray:
        return self._scores.astype(float)

    def _score(self, user_idx: np.ndarray) -> np.ndarray:
        return np.tile(self._scores, (len(user_idx), 1))

    def params(self) -> dict[str, Any]:
        return {"recency_half_life_h": self.recency_half_life_h}
