"""Fixtures pequenas e determinísticas — nenhum teste depende de rede ou do Databricks."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("MPLBACKEND", "Agg")
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_sitemap_xml() -> str:
    return (FIXTURES / "sitemap_sample.xml").read_text(encoding="utf-8")


@pytest.fixture
def toy_articles() -> pd.DataFrame:
    """6 matérias em 2 editorias, publicadas de hora em hora."""
    rows = []
    for i, section in enumerate(["economia"] * 3 + ["esportes"] * 3):
        rows.append(
            {
                "article_id": f"a{i}",
                "url": f"https://oglobo.globo.com/{section}/noticia/2026/10/07/m{i}.ghtml",
                "title": f"Matéria {i}",
                "section": section,
                "subsection": section,
                "published_at": f"2026-10-07T0{i}:00:00-03:00",
                "image_url": None,
                "first_seen_at": "2026-10-07T12:00:00+00:00",
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def toy_clicks() -> pd.DataFrame:
    """u1/u2 leem economia, u3/u4 leem esportes — o padrão que os modelos devem aprender."""
    data = [
        ("u1", "a0", 1), ("u1", "a1", 2), ("u1", "a2", 3),
        ("u2", "a0", 1), ("u2", "a1", 2),
        ("u3", "a3", 1), ("u3", "a4", 2), ("u3", "a5", 3),
        ("u4", "a3", 1), ("u4", "a4", 2),
    ]  # fmt: skip
    base = pd.Timestamp("2026-10-07T10:00:00Z")
    return pd.DataFrame(
        [
            {"user_id": u, "article_id": a, "event_ts": base + pd.Timedelta(minutes=m)}
            for u, a, m in data
        ]
    )
