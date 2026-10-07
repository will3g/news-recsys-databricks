import pandas as pd
import pytest

from news_recsys.evaluation.metrics import (
    evaluate_recommendations,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from news_recsys.evaluation.split import temporal_split


def test_temporal_split_keeps_latest_for_test(toy_clicks) -> None:
    train, test = temporal_split(toy_clicks, test_fraction=0.3, min_events=3)
    assert set(test["article_id"]) == {"a2", "a5"}  # último clique de u1 e u3
    assert set(test["user_id"]) == {"u1", "u3"}  # u2/u4 têm só 2 eventos
    assert len(train) + len(test) == len(toy_clicks)
    last_train = train.groupby("user_id")["event_ts"].max()
    first_test = test.groupby("user_id")["event_ts"].min()
    assert (last_train[first_test.index] <= first_test).all()
    with pytest.raises(ValueError):
        temporal_split(toy_clicks, test_fraction=1.0)


def test_metric_values() -> None:
    rec, rel = ["a", "b", "c"], {"b", "z"}
    assert precision_at_k(rec, rel, 3) == pytest.approx(1 / 3)
    assert recall_at_k(rec, rel, 3) == 0.5
    assert hit_rate_at_k(rec, rel, 1) == 0.0 and hit_rate_at_k(rec, rel, 2) == 1.0
    assert ndcg_at_k(["b"], {"b"}, 1) == 1.0
    assert ndcg_at_k(["x", "b"], {"b"}, 2) == pytest.approx(0.6309, abs=1e-4)
    assert recall_at_k(rec, set(), 3) == 0.0 and ndcg_at_k(rec, set(), 3) == 0.0


def test_evaluate_recommendations_and_coverage() -> None:
    recs = pd.DataFrame(
        {
            "user_id": ["u1", "u1", "u2", "u2"],
            "rank": [1, 2, 1, 2],
            "article_id": ["a", "b", "a", "c"],
            "score": [1, 0.5, 1, 0.5],
        }
    )
    test = pd.DataFrame({"user_id": ["u1", "u2"], "article_id": ["b", "z"]})
    m = evaluate_recommendations(recs, test, k=2, catalog_size=10)
    assert m["hit_rate_at_k"] == 0.5 and m["precision_at_k"] == 0.25
    assert m["catalog_coverage"] == 0.3 and m["n_users_eval"] == 2


def test_cold_item_metrics() -> None:
    from news_recsys.evaluation.metrics import cold_items_of

    train = pd.DataFrame({"user_id": ["u1"], "article_id": ["a"]})
    articles = pd.DataFrame({"article_id": ["a", "b", "c"]})
    cold = cold_items_of(train, articles)
    assert cold == {"b", "c"}
    recs = pd.DataFrame(
        {
            "user_id": ["u1", "u1", "u2", "u2"],
            "rank": [1, 2, 1, 2],
            "article_id": ["b", "a", "a", "a"],
            "score": [1, 1, 1, 1],
        }
    )
    test = pd.DataFrame({"user_id": ["u1", "u2"], "article_id": ["b", "c"]})
    m = evaluate_recommendations(recs, test, k=2, catalog_size=3, cold_items=cold)
    assert m["cold_hit_rate_at_k"] == 0.5  # u1 acertou a fria "b"; u2 não recebeu "c"
    assert m["cold_share_of_recs"] == 0.25
    assert "cold_hit_rate_at_k" not in evaluate_recommendations(recs, test, k=2, catalog_size=3)
