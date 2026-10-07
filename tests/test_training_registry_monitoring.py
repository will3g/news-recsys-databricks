import pandas as pd
import pytest

from news_recsys.monitoring import PSI_ALERT, distribution, psi, recs_report, report_to_records
from news_recsys.registry import decide_promotion
from news_recsys.simulation import SimulationConfig, simulate
from news_recsys.training import best_candidate, build_model, refit_full, train_candidates


def _catalog(n: int = 80) -> pd.DataFrame:
    sections = ["economia", "esportes", "politica", "cultura"]
    return pd.DataFrame(
        {
            "article_id": [f"a{i}" for i in range(n)],
            "section": [sections[i % 4] for i in range(n)],
            "subsection": [sections[i % 4] for i in range(n)],
            "published_at": pd.date_range("2026-10-06", periods=n, freq="30min", tz="UTC").astype(
                str
            ),
        }
    )


def test_train_candidates_personalized_beats_popularity() -> None:
    arts = _catalog()
    _, clicks = simulate(arts, SimulationConfig(n_users=80, mean_clicks_per_user=12, seed=5))
    results = train_candidates(clicks, arts, k=10)
    by_name = {r.label: r.metrics["ndcg_at_k"] for r in results}
    best = best_candidate(results)
    assert best.name != "popularidade", by_name
    assert "svd(n_components=16)" in by_name
    full = refit_full(best, clicks, arts)
    assert full.fitted_ and len(full.user_ids) == clicks["user_id"].nunique()
    with pytest.raises(KeyError):
        build_model("xgboost", {})


def test_promotion_gate() -> None:
    first = decide_promotion({"ndcg_at_k": 0.1}, None)
    assert first.promote and first.champion_value is None
    better = decide_promotion({"ndcg_at_k": 0.2}, {"ndcg_at_k": 0.1})
    assert better.promote
    worse = decide_promotion({"ndcg_at_k": 0.1}, {"ndcg_at_k": 0.2})
    assert not worse.promote and "não supera" in worse.reason
    margin = decide_promotion({"ndcg_at_k": 0.205}, {"ndcg_at_k": 0.2}, min_improvement=0.01)
    assert not margin.promote
    with pytest.raises(KeyError):
        decide_promotion({}, None)


def test_psi_and_report() -> None:
    same = distribution(["a", "b", "a", "b"])
    assert psi(same, same) == pytest.approx(0.0, abs=1e-6)
    shifted = distribution(["a"] * 9 + ["b"])
    assert psi(same, shifted) > PSI_ALERT

    arts = pd.DataFrame({"article_id": ["x", "y", "z"], "section": ["eco", "eco", "esp"]})
    recs = pd.DataFrame(
        {"user_id": ["u", "u"], "rank": [1, 2], "article_id": ["x", "z"], "score": [1, 1]}
    )
    reads = pd.DataFrame({"user_id": ["u", "u"], "article_id": ["x", "z"]})
    report = recs_report(recs, reads, arts)
    assert report["catalog_coverage"] == pytest.approx(2 / 3)
    assert report["psi_sections_recs_vs_reads"] == pytest.approx(0.0, abs=1e-6)
    records = report_to_records(report, model_version="3", generated_at="t")
    assert records[0]["model_version"] == "3" and {r["metric"] for r in records} == set(report)
