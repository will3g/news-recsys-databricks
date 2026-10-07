"""Modelos de recomendação: popularidade (baseline), item-item CF e fatoração de matriz (SVD)."""

from news_recsys.models.base import Recommender
from news_recsys.models.item_cf import ItemCFRecommender
from news_recsys.models.popularity import PopularityRecommender
from news_recsys.models.svd import SVDRecommender

MODEL_REGISTRY: dict[str, type[Recommender]] = {
    "popularidade": PopularityRecommender,
    "item_cf": ItemCFRecommender,
    "svd": SVDRecommender,
}

__all__ = [
    "MODEL_REGISTRY",
    "ItemCFRecommender",
    "PopularityRecommender",
    "Recommender",
    "SVDRecommender",
]
