"""Monitoramento do recomendador: distribuição de editorias, PSI (drift) e cobertura."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

PSI_ALERT = 0.2  # regra de bolso: < 0.1 estável · 0.1–0.2 atenção · > 0.2 mudança relevante


def distribution(values: Sequence[str] | pd.Series) -> pd.Series:
    s = pd.Series(list(values), dtype="object")
    return s.value_counts(normalize=True).sort_index() if len(s) else pd.Series(dtype=float)


def psi(expected: pd.Series, actual: pd.Series, eps: float = 1e-4) -> float:
    """Population Stability Index entre duas distribuições categóricas."""
    cats = sorted(set(expected.index) | set(actual.index))
    e = expected.reindex(cats).fillna(0).to_numpy() + eps
    a = actual.reindex(cats).fillna(0).to_numpy() + eps
    e, a = e / e.sum(), a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))


def recs_report(
    recs: pd.DataFrame, interactions: pd.DataFrame, articles: pd.DataFrame
) -> dict[str, float]:
    """Compara o que recomendamos com o que os usuários consomem."""
    section = articles.set_index("article_id")["section"]
    rec_dist = distribution(recs["article_id"].map(section).dropna())
    read_dist = distribution(interactions["article_id"].map(section).dropna())
    n_catalog = len(articles)
    return {
        "n_users": float(recs["user_id"].nunique()),
        "n_recommendations": float(len(recs)),
        "catalog_coverage": recs["article_id"].nunique() / n_catalog if n_catalog else 0.0,
        "psi_sections_recs_vs_reads": psi(read_dist, rec_dist),
        "top_section_share": float(rec_dist.max()) if len(rec_dist) else 0.0,
    }


def report_to_records(
    report: dict[str, float], *, model_version: str, generated_at: str | None = None
) -> list[dict[str, Any]]:
    ts = generated_at or datetime.now(UTC).isoformat(timespec="seconds")
    return [
        {"generated_at": ts, "model_version": model_version, "metric": k, "value": float(v)}
        for k, v in report.items()
    ]
