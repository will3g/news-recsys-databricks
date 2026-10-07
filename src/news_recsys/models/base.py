"""Base comum dos recomendadores: índices, matriz usuário×matéria e o ``recommend`` top-k."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

RECS_COLUMNS = ["user_id", "rank", "article_id", "score"]


class NotFittedError(RuntimeError):
    """``recommend`` chamado antes de ``fit``."""


class Recommender(ABC):
    """Contrato: ``fit(cliques, catálogo)`` → ``recommend(usuários, k)``.

    O catálogo inteiro é candidato (inclusive matérias novas, sem cliques). Matérias já lidas
    pelo usuário não são recomendadas de novo. Usuários desconhecidos recebem o *fallback* de
    popularidade — o "cold start" de usuário.
    """

    name: str = "base"

    def __init__(self) -> None:
        self.item_ids: np.ndarray = np.array([], dtype=object)
        self.user_ids: np.ndarray = np.array([], dtype=object)
        self._item_index: dict[str, int] = {}
        self._user_index: dict[str, int] = {}
        self.X: sparse.csr_matrix | None = None
        self.popularity_: np.ndarray = np.array([])
        self.fitted_ = False

    # --- API pública ------------------------------------------------------------------
    def fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> Recommender:
        self.item_ids = articles["article_id"].astype(str).to_numpy()
        self._item_index = {a: i for i, a in enumerate(self.item_ids)}
        known = interactions[interactions["article_id"].isin(self._item_index)]
        self.user_ids = np.array(sorted(known["user_id"].astype(str).unique()), dtype=object)
        self._user_index = {u: i for i, u in enumerate(self.user_ids)}

        rows = known["user_id"].map(self._user_index).to_numpy()
        cols = known["article_id"].map(self._item_index).to_numpy()
        data = np.ones(len(known), dtype=np.float32)
        self.X = sparse.csr_matrix(
            (data, (rows, cols)), shape=(len(self.user_ids), len(self.item_ids))
        )
        self.X.sum_duplicates()
        counts = np.asarray(self.X.sum(axis=0)).ravel()
        self.popularity_ = counts / counts.max() if counts.max() > 0 else counts
        self._fit(known, articles)
        self.fitted_ = True
        return self

    def recommend(
        self, user_ids: Sequence[str], k: int = 10, exclude_seen: bool = True
    ) -> pd.DataFrame:
        if not self.fitted_ or self.X is None:
            raise NotFittedError(f"{self.name}: chame fit() antes de recommend()")
        users = [str(u) for u in user_ids]
        known = [u for u in users if u in self._user_index]
        rows: list[dict[str, Any]] = []

        if known:
            idx = np.array([self._user_index[u] for u in known])
            scores = np.asarray(self._score(idx), dtype=float)
            scores = scores + 1e-6 * self.popularity_  # desempate (e fallback) por popularidade
            if exclude_seen:
                seen = self.X[idx].toarray() > 0
                scores[seen] = -np.inf
            for u, row in zip(known, scores, strict=True):
                rows.extend(self._top_k(u, row, k))

        cold_scores = self._cold_start_scores()
        for u in users:
            if u not in self._user_index:
                rows.extend(self._top_k(u, cold_scores, k))

        out = pd.DataFrame(rows, columns=RECS_COLUMNS)
        order = {u: i for i, u in enumerate(users)}
        out["_o"] = out["user_id"].map(order)
        return out.sort_values(["_o", "rank"]).drop(columns="_o").reset_index(drop=True)

    def params(self) -> dict[str, Any]:
        """Hiperparâmetros (logados no MLflow)."""
        return {}

    # --- Para as subclasses ------------------------------------------------------------
    def _fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> None:  # noqa: B027
        """Treino específico do modelo (opcional)."""

    def _cold_start_scores(self) -> np.ndarray:
        """Scores para usuários sem histórico (cold start): popularidade."""
        return self.popularity_.astype(float)

    @abstractmethod
    def _score(self, user_idx: np.ndarray) -> np.ndarray:
        """Matriz (n_usuários × n_matérias) de scores."""

    # --- Internos -------------------------------------------------------------------------
    def _top_k(self, user_id: str, scores: np.ndarray, k: int) -> list[dict[str, Any]]:
        finite = np.isfinite(scores)
        k_eff = min(k, int(finite.sum()))
        if k_eff == 0:
            return []
        candidates = np.where(finite)[0]
        part = candidates[np.argpartition(-scores[candidates], k_eff - 1)[:k_eff]]
        best = part[np.argsort(-scores[part], kind="stable")]
        return [
            {
                "user_id": user_id,
                "rank": r,
                "article_id": str(self.item_ids[i]),
                "score": float(scores[i]),
            }
            for r, i in enumerate(best, start=1)
        ]
