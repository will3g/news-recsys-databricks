"""Camada de dados do app: Lakehouse (SQL warehouse) ou amostra local (parquet).

O app nunca sabe de onde vem o dado — mesma interface, fonte diferente. Se os secrets do
Databricks não existirem (ou a conexão falhar), cai para ``sample_data/`` e a demo continua.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

SAMPLE_DIR = Path(__file__).parent / "sample_data"
REQUIRED_SECRETS = ("server_hostname", "http_path", "access_token")


class DataSource(Protocol):
    name: str

    def users(self) -> pd.DataFrame: ...

    def history(self, user_id: str, limit: int = 10) -> pd.DataFrame: ...

    def recommendations(self, user_id: str) -> pd.DataFrame: ...

    def model_metrics(self) -> pd.DataFrame: ...


class SampleSource:
    """Lê os parquets gerados por ``make train-local``."""

    name = "amostra local (sample_data)"

    def __init__(self, directory: Path = SAMPLE_DIR) -> None:
        self.dir = Path(directory)

    def _read(self, name: str) -> pd.DataFrame:
        return pd.read_parquet(self.dir / f"{name}.parquet")

    def users(self) -> pd.DataFrame:
        return self._read("users").sort_values("user_id").reset_index(drop=True)

    def history(self, user_id: str, limit: int = 10) -> pd.DataFrame:
        df = self._read("interactions")
        df = df[df["user_id"] == user_id].sort_values("event_ts", ascending=False)
        return df.head(limit).reset_index(drop=True)

    def recommendations(self, user_id: str) -> pd.DataFrame:
        df = self._read("recommendations")
        return df[df["user_id"] == user_id].sort_values("rank").reset_index(drop=True)

    def model_metrics(self) -> pd.DataFrame:
        return self._read("model_metrics")


class DatabricksSource:
    """Consulta as tabelas gold/silver via Databricks SQL warehouse."""

    def __init__(self, cfg: Mapping[str, Any]) -> None:
        from databricks import sql  # lazy: só no app com secrets

        self._sql = sql
        self.cfg = dict(cfg)
        self.prefix = (
            f"{self.cfg.get('catalog', 'workspace')}.{self.cfg.get('schema', 'news_recsys')}"
        )
        self.name = f"Lakehouse ({self.prefix})"

    def _query(self, statement: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with (
            self._sql.connect(
                server_hostname=self.cfg["server_hostname"],
                http_path=self.cfg["http_path"],
                access_token=self.cfg["access_token"],
            ) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(statement, params or {})
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
        return pd.DataFrame([tuple(r) for r in rows], columns=cols)

    def users(self) -> pd.DataFrame:
        return self._query(
            f"SELECT DISTINCT r.user_id, u.persona FROM {self.prefix}.gold_user_recommendations r "
            f"JOIN {self.prefix}.silver_users u USING (user_id) ORDER BY r.user_id"
        )

    def history(self, user_id: str, limit: int = 10) -> pd.DataFrame:
        return self._query(
            f"SELECT i.user_id, i.article_id, i.event_ts, a.title, a.url, a.section, a.image_url "
            f"FROM {self.prefix}.silver_interactions i JOIN {self.prefix}.bronze_articles a "
            f"USING (article_id) WHERE i.user_id = :user_id "
            f"ORDER BY i.event_ts DESC LIMIT {int(limit)}",
            {"user_id": user_id},
        )

    def recommendations(self, user_id: str) -> pd.DataFrame:
        return self._query(
            f"SELECT * FROM {self.prefix}.gold_user_recommendations "
            f"WHERE user_id = :user_id ORDER BY rank",
            {"user_id": user_id},
        )

    def model_metrics(self) -> pd.DataFrame:
        return self._query(f"SELECT * FROM {self.prefix}.model_metrics ORDER BY evaluated_at")


def has_databricks_secrets(secrets: Mapping[str, Any] | None) -> bool:
    return bool(secrets) and all(secrets.get(k) for k in REQUIRED_SECRETS)  # type: ignore[union-attr]


def get_source(secrets: Mapping[str, Any] | None) -> tuple[DataSource, str | None]:
    """Fonte de dados + aviso (quando caiu para a amostra)."""
    if not has_databricks_secrets(secrets):
        return SampleSource(), "Sem secrets do Databricks: exibindo a amostra local."
    try:
        source = DatabricksSource(secrets or {})
        source.users()  # teste de conexão
        return source, None
    except Exception as exc:  # noqa: BLE001
        return (
            SampleSource(),
            f"Lakehouse indisponível ({type(exc).__name__}): exibindo a amostra local.",
        )
