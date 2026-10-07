"""Filtragem colaborativa item-item: "quem leu X também leu Y" (similaridade de cosseno)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.preprocessing import normalize

from news_recsys.models.base import Recommender


class ItemCFRecommender(Recommender):
    name = "item_cf"

    def __init__(self, n_neighbors: int = 50) -> None:
        super().__init__()
        self.n_neighbors = n_neighbors
        self.S: sparse.csr_matrix | None = None

    def _fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> None:
        assert self.X is not None
        Xn = normalize(self.X.tocsc(), norm="l2", axis=0)  # cada matéria vira um vetor unitário
        S = (Xn.T @ Xn).tocsr()
        S.setdiag(0)
        S.eliminate_zeros()
        self.S = self._prune(S, self.n_neighbors)

    @staticmethod
    def _prune(S: sparse.csr_matrix, n: int) -> sparse.csr_matrix:
        """Mantém só os ``n`` vizinhos mais parecidos de cada matéria."""
        S = S.tolil()
        for i, (cols, vals) in enumerate(zip(S.rows, S.data, strict=True)):
            if len(vals) > n:
                keep = np.argsort(vals)[::-1][:n]
                S.rows[i] = [cols[j] for j in sorted(keep)]
                S.data[i] = [vals[j] for j in sorted(keep)]
        return S.tocsr()

    def _score(self, user_idx: np.ndarray) -> np.ndarray:
        assert self.X is not None and self.S is not None
        return (self.X[user_idx] @ self.S).toarray()

    def params(self) -> dict[str, Any]:
        return {"n_neighbors": self.n_neighbors}
