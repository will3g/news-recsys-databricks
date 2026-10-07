import pandas as pd

from news_recsys.simulation import PERSONAS, SimulationConfig, simulate


def _articles(n: int = 60) -> pd.DataFrame:
    sections = ["economia", "esportes", "politica", "cultura"]
    return pd.DataFrame(
        {
            "article_id": [f"a{i}" for i in range(n)],
            "section": [sections[i % 4] for i in range(n)],
            "subsection": [sections[i % 4] for i in range(n)],
            "published_at": pd.date_range("2026-10-06", periods=n, freq="45min", tz="UTC").astype(
                str
            ),
        }
    )


def test_simulation_is_deterministic_and_valid() -> None:
    arts = _articles()
    cfg = SimulationConfig(n_users=24, mean_clicks_per_user=8, seed=7)
    users1, clicks1 = simulate(arts, cfg)
    users2, clicks2 = simulate(arts, cfg)
    pd.testing.assert_frame_equal(clicks1, clicks2)
    assert len(users1) == 24 and set(users1["persona"]) <= set(PERSONAS)
    assert clicks1["article_id"].isin(arts["article_id"]).all()
    assert not clicks1.duplicated(["user_id", "article_id"]).any()  # sem releitura
    assert (clicks1.groupby("user_id").size() >= 1).all()


def test_personas_shape_the_clicks() -> None:
    arts = _articles(120)
    _, clicks = simulate(
        arts, SimulationConfig(n_users=40, mean_clicks_per_user=15, noise=0.0, seed=3)
    )
    section = arts.set_index("article_id")["section"]
    torcedor = clicks[clicks["persona"] == "torcedor"]
    share = (torcedor["article_id"].map(section) == "esportes").mean()
    assert share > 0.5  # torcedor lê majoritariamente esportes


def test_clicks_happen_after_publication() -> None:
    arts = _articles()
    _, clicks = simulate(arts, SimulationConfig(n_users=10, seed=1))
    published = pd.to_datetime(arts.set_index("article_id")["published_at"], utc=True)
    assert (clicks["event_ts"] >= clicks["article_id"].map(published)).all()
