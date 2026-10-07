"""Split temporal por usuário: os cliques mais recentes de cada um viram o conjunto de teste."""

from __future__ import annotations

import math

import pandas as pd


def temporal_split(
    interactions: pd.DataFrame, test_fraction: float = 0.2, min_events: int = 3
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (treino, teste). Usuários com menos de ``min_events`` ficam só no treino.

    Temporal (e não aleatório) porque em produção o modelo sempre prevê o *futuro* — um split
    aleatório vazaria informação e inflaria as métricas.
    """
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction deve estar entre 0 e 1")
    df = interactions.sort_values(["user_id", "event_ts"]).copy()
    df["_n"] = df.groupby("user_id")["article_id"].transform("size")
    df["_pos"] = df.groupby("user_id").cumcount()
    n_test = df["_n"].map(lambda n: math.ceil(n * test_fraction) if n >= min_events else 0)
    is_test = df["_pos"] >= df["_n"] - n_test
    cols = [c for c in interactions.columns]
    return (
        df.loc[~is_test, cols].reset_index(drop=True),
        df.loc[is_test, cols].reset_index(drop=True),
    )
