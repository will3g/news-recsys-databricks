import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from data_access import SampleSource, get_source, has_databricks_secrets  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "app" / "sample_data"
pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="rode `make train-local` antes")


def test_sample_source_contract() -> None:
    src = SampleSource()
    users = src.users()
    assert {"user_id", "persona"} <= set(users.columns) and len(users) > 0
    user = users["user_id"].iloc[0]
    recs = src.recommendations(user)
    assert list(recs["rank"]) == list(range(1, len(recs) + 1))
    assert {"title", "url", "section", "model_version", "generated_at"} <= set(recs.columns)
    history = src.history(user, limit=3)
    assert len(history) <= 3 and history["event_ts"].is_monotonic_decreasing
    assert not set(history["article_id"]) & set(recs["article_id"])  # não recomenda o que já leu
    assert {"candidate", "metric", "value", "promoted"} <= set(src.model_metrics().columns)


def test_get_source_falls_back_without_secrets() -> None:
    assert not has_databricks_secrets(None)
    assert not has_databricks_secrets(
        {"server_hostname": "x", "http_path": "", "access_token": "t"}
    )
    src, warning = get_source({})
    assert isinstance(src, SampleSource) and warning


def test_get_source_falls_back_when_connection_fails(monkeypatch) -> None:
    import data_access

    class Boom:
        def __init__(self, cfg):
            raise ConnectionError("offline")

    monkeypatch.setattr(data_access, "DatabricksSource", Boom)
    src, warning = get_source({"server_hostname": "h", "http_path": "p", "access_token": "t"})
    assert isinstance(src, SampleSource) and "ConnectionError" in warning
