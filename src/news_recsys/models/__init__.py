"""Modelos: popularidade (baseline), item-item CF, SVD, conteúdo (TF-IDF) e híbrido."""

from news_recsys.models.base import Recommender
from news_recsys.models.content import ContentRecommender
from news_recsys.models.hybrid import HybridRecommender
from news_recsys.models.item_cf import ItemCFRecommender
from news_recsys.models.popularity import PopularityRecommender
from news_recsys.models.svd import SVDRecommender

MODEL_REGISTRY: dict[str, type[Recommender]] = {
    "popularidade": PopularityRecommender,
    "item_cf": ItemCFRecommender,
    "svd": SVDRecommender,
    "conteudo": ContentRecommender,
    "hibrido": HybridRecommender,
}

__all__ = [
    "MODEL_REGISTRY",
    "ContentRecommender",
    "HybridRecommender",
    "ItemCFRecommender",
    "PopularityRecommender",
    "Recommender",
    "SVDRecommender",
]
