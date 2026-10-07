"""Wrapper MLflow (pyfunc) do recomendador — o artefato registrado no Unity Catalog.

Único módulo que importa MLflow no topo: ele É o modelo. Os testes não o importam.
Entrada: DataFrame com ``user_id`` (e opcionalmente ``k``). Saída: user_id, rank, article_id, score.
"""

from __future__ import annotations

from typing import Any

import mlflow
import pandas as pd

from news_recsys.models.base import RECS_COLUMNS, Recommender

DEFAULT_K = 10


class NewsRecommenderModel(mlflow.pyfunc.PythonModel):
    def __init__(self, recommender: Recommender, k: int = DEFAULT_K) -> None:
        self.recommender = recommender
        self.k = k

    def predict(
        self, context: Any, model_input: pd.DataFrame, params: dict[str, Any] | None = None
    ) -> pd.DataFrame:
        k = int((params or {}).get("k", self.k))
        users = model_input["user_id"].astype(str).tolist()
        recs = self.recommender.recommend(users, k=k)
        return recs[RECS_COLUMNS]


def log_recommender(
    recommender: Recommender,
    *,
    code_path: str,
    sample_users: list[str],
    registered_model_name: str | None = None,
    k: int = DEFAULT_K,
) -> Any:
    """Loga o modelo com assinatura e exemplo; registra no UC se ``registered_model_name``."""
    from mlflow.models import infer_signature

    wrapper = NewsRecommenderModel(recommender, k=k)
    example = pd.DataFrame({"user_id": sample_users[:3]})
    output = wrapper.predict(None, example)
    signature = infer_signature(example, output, params={"k": k})
    return mlflow.pyfunc.log_model(
        name="news_recommender",
        python_model=wrapper,
        code_paths=[code_path],
        signature=signature,
        input_example=example,
        registered_model_name=registered_model_name,
        pip_requirements=["pandas", "numpy", "scipy", "scikit-learn", "pydantic-settings"],
    )
