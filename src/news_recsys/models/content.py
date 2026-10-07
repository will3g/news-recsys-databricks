"""Recomendação por conteúdo: perfil do usuário (TF-IDF do que ele leu) × matérias.

Resolve o *cold start de matéria*: uma notícia publicada há 5 minutos não tem cliques, mas tem
título e editoria — então já pode ser recomendada para quem lê coisas parecidas.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from news_recsys.models.base import Recommender

_STOPWORDS_TEXT = (
    "a ao aos as à às com como da das de do dos e é em entre era essa esse esta este foi há "
    "isso já la mais mas na nas no nos não o os ou para pela pelas pelo pelos por qual que se "
    "sem ser seu sua são sobre também tem um uma vai veja diz após contra até"
)
PT_STOPWORDS: list[str] = _STOPWORDS_TEXT.split()


def article_text(articles: pd.DataFrame) -> pd.Series:
    """Título + editoria + subeditoria (os tokens de editoria pesam como palavras do texto)."""
    empty = pd.Series("", index=articles.index)
    title = articles["title"].fillna("") if "title" in articles else empty
    section = "sec_" + articles["section"].fillna("").str.replace("-", "_")
    sub = articles["subsection"] if "subsection" in articles else articles["section"]
    subsection = "sub_" + sub.fillna("").str.replace(r"[/-]", "_", regex=True)
    return title + " " + section + " " + section + " " + subsection


def recency_weights(articles: pd.DataFrame, half_life_h: float | None) -> np.ndarray:
    """1.0 para a matéria mais nova, decaindo pela meia-vida (None = sem decaimento)."""
    if not half_life_h:
        return np.ones(len(articles))
    published = pd.to_datetime(articles["published_at"], utc=True, format="mixed", errors="coerce")
    age_h = ((published.max() - published).dt.total_seconds() / 3600).fillna(1e6).to_numpy()
    return 0.5 ** (np.clip(age_h, 0, None) / half_life_h)


class ContentRecommender(Recommender):
    name = "conteudo"

    def __init__(self, recency_half_life_h: float | None = 24.0, max_features: int = 5000) -> None:
        super().__init__()
        self.recency_half_life_h = recency_half_life_h
        self.max_features = max_features
        self.V: sparse.csr_matrix | None = None
        self.recency_: np.ndarray = np.array([])

    def _fit(self, interactions: pd.DataFrame, articles: pd.DataFrame) -> None:
        vectorizer = TfidfVectorizer(
            stop_words=PT_STOPWORDS,
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=self.max_features,
            strip_accents=None,
        )
        self.V = normalize(vectorizer.fit_transform(article_text(articles)))  # matérias × termos
        self.vocabulary_size_ = len(vectorizer.vocabulary_)
        self.recency_ = recency_weights(articles, self.recency_half_life_h)

    def _score(self, user_idx: np.ndarray) -> np.ndarray:
        assert self.X is not None and self.V is not None
        profiles = normalize(self.X[user_idx] @ self.V)  # média do que o usuário leu
        similarity = (profiles @ self.V.T).toarray()  # cosseno perfil × matéria
        return similarity * self.recency_

    def params(self) -> dict[str, Any]:
        return {"recency_half_life_h": self.recency_half_life_h, "max_features": self.max_features}
