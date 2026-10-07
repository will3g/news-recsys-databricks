"""Configuração central (variáveis de ambiente, .env ou widgets do Databricks)."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Unity Catalog -------------------------------------------------------------
    catalog: str = Field(
        default="workspace", validation_alias=AliasChoices("DATABRICKS_CATALOG", "catalog")
    )
    schema_name: str = Field(
        default="news_recsys",
        validation_alias=AliasChoices("DATABRICKS_SCHEMA", "schema_name", "schema"),
    )
    volume: str = Field(default="raw", validation_alias=AliasChoices("DATABRICKS_VOLUME", "volume"))
    model_name: str = "news_recommender"

    # --- Dados -----------------------------------------------------------------------
    sitemap_url: str = "https://oglobo.globo.com/sitemap/oglobo/news.xml"

    # --- Simulação de usuários ---------------------------------------------------
    n_users: int = 300
    mean_clicks_per_user: float = 18.0
    seed: int = 42

    # --- Treino / avaliação ------------------------------------------------------------
    k: int = 10
    test_fraction: float = 0.2
    svd_components: int = 24
    promotion_metric: str = "ndcg_at_k"
    min_improvement: float = 0.0

    def table(self, name: str) -> str:
        return f"{self.catalog}.{self.schema_name}.{name}"

    def volume_path(self, filename: str = "") -> str:
        base = f"/Volumes/{self.catalog}/{self.schema_name}/{self.volume}"
        return f"{base}/{filename}" if filename else base

    @property
    def model_fqn(self) -> str:
        return self.table(self.model_name)

    def with_overrides(self, **overrides: Any) -> Settings:
        """Cópia validada aplicando só overrides não vazios (widgets chegam como string)."""
        clean = {k: v for k, v in overrides.items() if v not in (None, "")}
        return Settings(**{**self.model_dump(), **clean})
