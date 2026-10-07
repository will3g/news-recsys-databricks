"""Catálogo de matérias: sitemap → registros com id estável e editoria."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from news_recsys.features.sections import (
    is_recommendable,
    section_from_url,
    subsection_from_url,
)
from news_recsys.ingestion.sitemap import ArticleMeta, parse_sitemap

USER_AGENT = "Mozilla/5.0 (compatible; news-recsys-aula/0.1)"
ARTICLE_FIELDS = (
    "article_id",
    "url",
    "title",
    "section",
    "subsection",
    "published_at",
    "image_url",
    "first_seen_at",
)


def article_id_from_url(url: str) -> str:
    """Id curto e estável (a URL é a chave natural; o hash só encurta)."""
    clean = url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return "a_" + hashlib.sha1(clean.encode("utf-8")).hexdigest()[:12]  # noqa: S324


def to_record(meta: ArticleMeta, first_seen_at: str) -> dict[str, Any]:
    return {
        "article_id": article_id_from_url(meta.url),
        "url": meta.url,
        "title": meta.title,
        "section": section_from_url(meta.url),
        "subsection": subsection_from_url(meta.url),
        "published_at": meta.published_at,
        "image_url": meta.image_url,
        "first_seen_at": first_seen_at,
    }


def build_records(metas: Iterable[ArticleMeta], now: str | None = None) -> list[dict[str, Any]]:
    """Registros do catálogo — sem título ou patrocinados ficam de fora."""
    ts = now or datetime.now(UTC).isoformat(timespec="seconds")
    records = [to_record(m, ts) for m in metas if m.title]
    return [r for r in records if is_recommendable(r["section"])]


def fetch_sitemap(url: str, timeout: float = 20.0) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def merge_records(
    existing: Sequence[dict[str, Any]], new: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Une catálogos por ``article_id``; mantém o ``first_seen_at`` mais antigo."""
    merged: dict[str, dict[str, Any]] = {r["article_id"]: dict(r) for r in existing}
    for record in new:
        old = merged.get(record["article_id"])
        if old is None:
            merged[record["article_id"]] = dict(record)
        else:
            merged[record["article_id"]] = {**record, "first_seen_at": old["first_seen_at"]}
    return sorted(merged.values(), key=lambda r: (r["published_at"], r["article_id"]))


def load_catalog(path: Path) -> list[dict[str, Any]]:
    if not Path(path).exists():
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(payload["articles"] if isinstance(payload, dict) else payload)


def save_catalog(records: Sequence[dict[str, Any]], path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "oglobo-news-sitemap",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_articles": len(records),
        "articles": list(records),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(records)


def fetch_catalog(url: str, now: str | None = None) -> list[dict[str, Any]]:
    """Sitemap ao vivo → registros do catálogo."""
    return build_records(parse_sitemap(fetch_sitemap(url)), now=now)
