"""Usuários e cliques SINTÉTICOS sobre matérias reais.

Não temos clickstream do O Globo — então simulamos. Cada usuário tem uma *persona* (preferência
por editorias), um gosto fino por subeditorias e sofre viés de popularidade e de recência. O
resultado imita a estrutura de um log real de eventos (user, matéria, timestamp), e é com ele
que os modelos são treinados. Em produção esse dado viria do analytics (eventos de clique).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PERSONAS: dict[str, dict[str, float]] = {
    "politizado": {"politica": 0.55, "brasil": 0.15, "blogs": 0.15, "opiniao": 0.1, "mundo": 0.05},
    "investidor": {"economia": 0.6, "politica": 0.15, "mundo": 0.15, "blogs": 0.1},
    "torcedor": {"esportes": 0.7, "rio": 0.15, "cultura": 0.15},
    "carioca": {"rio": 0.45, "cultura": 0.2, "esportes": 0.15, "brasil": 0.2},
    "cultural": {"cultura": 0.45, "ela": 0.3, "saude": 0.15, "outros": 0.1},
    "globalista": {"mundo": 0.55, "economia": 0.2, "politica": 0.15, "ciencia": 0.1},
    "bem-estar": {"saude": 0.45, "ela": 0.3, "ciencia": 0.15, "cultura": 0.1},
    "generalista": {},  # sem preferência: segue a distribuição do catálogo
}


@dataclass(frozen=True)
class SimulationConfig:
    n_users: int = 300
    mean_clicks_per_user: float = 18.0
    min_clicks_per_user: int = 4
    section_weight: float = 3.0  # força da preferência por editoria
    subsection_weight: float = 2.0  # gosto fino (subeditorias favoritas)
    popularity_weight: float = 1.0
    recency_half_life_h: float = 12.0
    noise: float = 0.15  # cliques "aleatórios"
    seed: int = 42


def _parse_ts(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True, format="mixed", errors="coerce")


def make_users(articles: pd.DataFrame, cfg: SimulationConfig) -> pd.DataFrame:
    """Um usuário por linha: persona + pesos por editoria + 2 subeditorias favoritas."""
    rng = np.random.default_rng(cfg.seed)
    sections = sorted(articles["section"].unique())
    base_mix = articles["section"].value_counts(normalize=True).reindex(sections).fillna(0.0)
    names = list(PERSONAS)
    rows = []
    for i in range(cfg.n_users):
        persona = names[i % len(names)] if i < len(names) else str(rng.choice(names))
        prefs = PERSONAS[persona] or base_mix.to_dict()
        weights = np.array([prefs.get(s, 0.0) for s in sections]) + 0.01
        weights = rng.dirichlet(weights / weights.sum() * 20)  # cada usuário é um pouco diferente
        subs = articles.loc[articles["section"].isin(_top(sections, weights, 2)), "subsection"]
        favorites = list(subs.value_counts().index[:6])
        fav = (
            list(rng.choice(favorites, size=min(2, len(favorites)), replace=False))
            if favorites
            else []
        )
        rows.append(
            {
                "user_id": f"u_{i:04d}",
                "persona": persona,
                "section_prefs": dict(zip(sections, np.round(weights, 4).tolist(), strict=True)),
                "favorite_subsections": fav,
            }
        )
    return pd.DataFrame(rows)


def _top(items: list[str], weights: np.ndarray, n: int) -> list[str]:
    return [items[i] for i in np.argsort(weights)[::-1][:n]]


def simulate_clicks(
    articles: pd.DataFrame, users: pd.DataFrame, cfg: SimulationConfig
) -> pd.DataFrame:
    """Gera o log de cliques: user_id, article_id, event_ts (+ persona para análise)."""
    rng = np.random.default_rng(cfg.seed + 1)
    arts = articles.reset_index(drop=True).copy()
    published = _parse_ts(arts["published_at"])
    t0, t1 = published.min(), published.max()
    span_h = max((t1 - t0).total_seconds() / 3600, 1.0)
    pub_h = ((published - t0).dt.total_seconds() / 3600).to_numpy()

    popularity = rng.lognormal(mean=0.0, sigma=1.0, size=len(arts))  # "matéria que viralizou"
    section_idx = arts["section"].to_numpy()
    subsection_idx = arts["subsection"].to_numpy()

    events = []
    for user in users.itertuples(index=False):
        n_clicks = max(cfg.min_clicks_per_user, int(rng.poisson(cfg.mean_clicks_per_user)))
        sec_w = np.array([user.section_prefs.get(s, 0.0) for s in section_idx])
        sub_bonus = np.isin(subsection_idx, user.favorite_subsections).astype(float)
        # momentos de leitura espalhados pela janela do catálogo
        read_h = np.sort(rng.uniform(0, span_h + 6, size=n_clicks))
        seen: set[int] = set()
        for t in read_h:
            age = t - pub_h
            available = age >= 0
            if not available.any():
                continue
            recency = np.where(
                available, 0.5 ** (np.clip(age, 0, None) / cfg.recency_half_life_h), 0
            )
            score = (
                (sec_w**cfg.section_weight + 1e-6)
                * (1 + cfg.subsection_weight * sub_bonus)
                * popularity**cfg.popularity_weight
                * recency
            )
            score[list(seen)] = 0.0
            if score.sum() <= 0:
                continue
            probs = (1 - cfg.noise) * score / score.sum()
            probs += cfg.noise * available / available.sum()
            probs[list(seen)] = 0.0
            probs /= probs.sum()
            idx = int(rng.choice(len(arts), p=probs))
            seen.add(idx)
            events.append(
                {
                    "user_id": user.user_id,
                    "article_id": arts.at[idx, "article_id"],
                    "event_ts": t0 + pd.Timedelta(hours=float(t)),
                    "persona": user.persona,
                }
            )
    out = pd.DataFrame(events, columns=["user_id", "article_id", "event_ts", "persona"])
    return out.sort_values(["user_id", "event_ts"]).reset_index(drop=True)


def simulate(
    articles: pd.DataFrame, cfg: SimulationConfig | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Atalho: (usuários, cliques)."""
    cfg = cfg or SimulationConfig()
    users = make_users(articles, cfg)
    return users, simulate_clicks(articles, users, cfg)
