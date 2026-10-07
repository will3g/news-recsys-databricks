from news_recsys.config import Settings


def test_settings_helpers(monkeypatch) -> None:
    s = Settings(_env_file=None)
    assert s.table("bronze_articles") == "workspace.news_recsys.bronze_articles"
    assert s.volume_path("x.json") == "/Volumes/workspace/news_recsys/raw/x.json"
    assert s.model_fqn == "workspace.news_recsys.news_recommender"
    assert s.with_overrides(schema_name="", n_users="50").n_users == 50
    monkeypatch.setenv("DATABRICKS_SCHEMA", "news_recsys_dev")
    assert Settings(_env_file=None).schema_name == "news_recsys_dev"
