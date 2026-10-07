"""Fatoração de matriz (TruncatedSVD): usuários e matérias num espaço de "gostos" latentes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD

from news_recsys.models.base import Recommender


class SVDRecommender(Recommender):
    name = "svd"

    def __init__(self, n_components: int = 24, random_state: int = 42) -> None:
        super().__init__()
        self.n_components = n_components
        self.random_state = random_state
        self.user_factors_: np.ndarray = np.array([])
        self.item_factors_: np.ndarray = np.array([])

    def _fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> None:
        assert self.X is not None
        n_comp = max(1, min(self.n_components, min(self.X.shape) - 1))
        svd = TruncatedSVD(n_components=n_comp, random_state=self.random_state)
        self.user_factors_ = svd.fit_transform(self.X)  # U·Σ
        self.item_factors_ = svd.components_  # Vᵀ
        self.explained_variance_ = float(svd.explained_variance_ratio_.sum())

    def _score(self, user_idx: np.ndarray) -> np.ndarray:
        return self.user_factors_[user_idx] @ self.item_factors_

    def params(self) -> dict[str, Any]:
        return {"n_components": self.n_components, "random_state": self.random_state}
