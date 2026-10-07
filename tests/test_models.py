import numpy as np
import pandas as pd
import pytest

from news_recsys.models import (
    MODEL_REGISTRY,
    ItemCFRecommender,
    PopularityRecommender,
    SVDRecommender,
)
from news_recsys.models.base import RECS_COLUMNS, NotFittedError


@pytest.mark.parametrize("name", list(MODEL_REGISTRY))
def test_recommend_contract(name: str, toy_articles, toy_clicks) -> None:
    model = MODEL_REGISTRY[name]().fit(toy_clicks, toy_articles)
    recs = model.recommend(["u2", "u4"], k=3)
    assert list(recs.columns) == RECS_COLUMNS
    assert recs.groupby("user_id")["rank"].apply(list).to_dict() == {
        "u2": [1, 2, 3],
        "u4": [1, 2, 3],
    }
    seen = set(zip(toy_clicks["user_id"], toy_clicks["article_id"], strict=True))
    assert not any((u, a) in seen for u, a in zip(recs["user_id"], recs["article_id"], strict=True))
    assert recs.groupby("user_id")["score"].apply(lambda s: s.is_monotonic_decreasing).all()


@pytest.mark.parametrize("cls", [ItemCFRecommender, SVDRecommender])
def test_personalized_models_learn_the_pattern(cls, toy_articles, toy_clicks) -> None:
    model = cls(**({"n_components": 2} if cls is SVDRecommender else {})).fit(
        toy_clicks, toy_articles
    )
    top = model.recommend(["u2", "u4"], k=1).set_index("user_id")["article_id"]
    assert top["u2"] == "a2"  # quem leu a0/a1 (economia) deve receber a2
    assert top["u4"] == "a5"  # quem leu a3/a4 (esportes) deve receber a5


def test_cold_start_user_gets_popular_items(toy_articles, toy_clicks) -> None:
    model = ItemCFRecommender().fit(toy_clicks, toy_articles)
    recs = model.recommend(["novo_usuario"], k=2)
    assert len(recs) == 2 and set(recs["article_id"]) <= {"a0", "a1", "a3", "a4"}


def test_popularity_recency_decay(toy_articles, toy_clicks) -> None:
    pure = PopularityRecommender(recency_half_life_h=None).fit(toy_clicks, toy_articles)
    decayed = PopularityRecommender(recency_half_life_h=1.0).fit(toy_clicks, toy_articles)
    assert pure.recommend(["x"], k=1)["article_id"][0] in {"a0", "a1", "a3", "a4"}
    assert decayed.recommend(["x"], k=1)["article_id"][0] == "a4"  # mais recente entre os populares
    assert decayed.params() == {"recency_half_life_h": 1.0}


def test_not_fitted_and_k_larger_than_catalog(toy_articles, toy_clicks) -> None:
    with pytest.raises(NotFittedError):
        SVDRecommender().recommend(["u1"])
    recs = PopularityRecommender().fit(toy_clicks, toy_articles).recommend(["u1"], k=50)
    assert len(recs) == 3  # 6 matérias - 3 já lidas


def test_unknown_articles_in_clicks_are_ignored(toy_articles, toy_clicks) -> None:
    extra = pd.concat(
        [
            toy_clicks,
            pd.DataFrame(
                [
                    {
                        "user_id": "u9",
                        "article_id": "zzz",
                        "event_ts": pd.Timestamp("2026-10-07", tz="UTC"),
                    }
                ]
            ),
        ]
    )
    model = SVDRecommender(n_components=2).fit(extra, toy_articles)
    assert "u9" not in model.user_ids
    assert np.isfinite(model.item_factors_).all()


def _articles_with_new_item(toy_articles):
    """Adiciona a6: matéria nova de economia, publicada depois de tudo e SEM cliques."""
    new = toy_articles.iloc[[0]].copy()
    new["article_id"] = "a6"
    new["title"] = "Matéria nova de economia"
    new["published_at"] = "2026-10-07T09:00:00-03:00"
    return pd.concat([toy_articles, new], ignore_index=True)


def test_content_recommends_cold_item(toy_articles, toy_clicks) -> None:
    from news_recsys.models import ContentRecommender

    arts = _articles_with_new_item(toy_articles)
    cf_top = ItemCFRecommender().fit(toy_clicks, arts).recommend(["u1"], k=1)["article_id"][0]
    content_top = ContentRecommender().fit(toy_clicks, arts).recommend(["u1"], k=1)["article_id"][0]
    assert cf_top != "a6"  # CF não enxerga matéria sem clique
    assert content_top == "a6"  # conteúdo enxerga: mesma editoria e mais recente


def test_hybrid_alpha_extremes_and_validation(toy_articles, toy_clicks) -> None:
    from news_recsys.models import HybridRecommender

    arts = _articles_with_new_item(toy_articles)
    only_content = HybridRecommender(alpha=0.0).fit(toy_clicks, arts)
    assert only_content.recommend(["u1"], k=1)["article_id"][0] == "a6"
    only_cf = HybridRecommender(alpha=1.0).fit(toy_clicks, arts)
    assert only_cf.recommend(["u2"], k=1)["article_id"][0] == "a2"
    assert only_cf.params()["alpha"] == 1.0
    with pytest.raises(ValueError):
        HybridRecommender(alpha=1.5)
