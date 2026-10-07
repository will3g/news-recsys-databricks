"""Quality gate champion/challenger + helpers do Unity Catalog (imports lazy)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    reason: str
    candidate_value: float
    champion_value: float | None


def decide_promotion(
    candidate_metrics: dict[str, float],
    champion_metrics: dict[str, float] | None,
    metric: str = "ndcg_at_k",
    min_improvement: float = 0.0,
) -> PromotionDecision:
    """O desafiante só vira campeão se for MELHOR que o atual (com margem opcional).

    É a regra que impede um retreino ruim (dados estranhos, bug) de chegar ao app.
    """
    if metric not in candidate_metrics:
        raise KeyError(f"métrica {metric!r} ausente nas métricas do candidato")
    cand = float(candidate_metrics[metric])
    if champion_metrics is None or metric not in champion_metrics:
        return PromotionDecision(
            True, "não há campeão: o primeiro modelo vira champion", cand, None
        )
    champ = float(champion_metrics[metric])
    if cand > champ + min_improvement:
        return PromotionDecision(True, f"{metric} {cand:.4f} > campeão {champ:.4f}", cand, champ)
    return PromotionDecision(
        False,
        f"{metric} {cand:.4f} não supera campeão {champ:.4f} (+{min_improvement})",
        cand,
        champ,
    )


def champion_metrics(model_fqn: str, alias: str = "champion") -> dict[str, float] | None:
    """Métricas da run que gerou a versão ``@champion`` (None se ainda não existe)."""
    from mlflow import MlflowClient

    client = MlflowClient(registry_uri="databricks-uc")
    try:
        version = client.get_model_version_by_alias(model_fqn, alias)
    except Exception:  # noqa: BLE001 — modelo/alias inexistente
        return None
    if not version.run_id:
        return None
    return dict(client.get_run(version.run_id).data.metrics)


def set_champion(model_fqn: str, version: str | int, alias: str = "champion") -> Any:
    from mlflow import MlflowClient

    client = MlflowClient(registry_uri="databricks-uc")
    client.set_registered_model_alias(model_fqn, alias, str(version))
    return client.get_model_version_by_alias(model_fqn, alias)
