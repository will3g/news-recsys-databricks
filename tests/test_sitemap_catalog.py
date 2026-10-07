from pathlib import Path

from news_recsys.ingestion.catalog import (
    article_id_from_url,
    build_records,
    load_catalog,
    merge_records,
    save_catalog,
)
from news_recsys.ingestion.sitemap import ArticleMeta, parse_sitemap


def test_parse_sitemap(sample_sitemap_xml: str) -> None:
    metas = parse_sitemap(sample_sitemap_xml)
    assert len(metas) == 2
    assert metas[0].image_url and metas[1].image_url is None


def test_article_id_is_stable_and_ignores_query() -> None:
    url = "https://oglobo.globo.com/economia/noticia/x.ghtml"
    assert article_id_from_url(url) == article_id_from_url(url + "?utm=1")
    assert article_id_from_url(url).startswith("a_") and len(article_id_from_url(url)) == 14


def test_build_records_adds_section_and_drops_sponsored() -> None:
    metas = [
        ArticleMeta("https://oglobo.globo.com/economia/noticia/a.ghtml", "A", "2026-10-07"),
        ArticleMeta("https://oglobo.globo.com/patrocinado/dino/noticia/b.ghtml", "B", "2026-10-07"),
        ArticleMeta("https://oglobo.globo.com/rio/noticia/c.ghtml", "", "2026-10-07"),
    ]
    records = build_records(metas, now="t0")
    assert [r["section"] for r in records] == ["economia"]
    assert records[0]["first_seen_at"] == "t0"


def test_merge_keeps_first_seen_and_save_load(tmp_path: Path) -> None:
    old = [{"article_id": "x", "published_at": "1", "title": "velho", "first_seen_at": "d1"}]
    new = [
        {"article_id": "x", "published_at": "1", "title": "novo", "first_seen_at": "d2"},
        {"article_id": "y", "published_at": "2", "title": "outro", "first_seen_at": "d2"},
    ]
    merged = merge_records(old, new)
    assert [r["article_id"] for r in merged] == ["x", "y"]
    assert merged[0]["title"] == "novo" and merged[0]["first_seen_at"] == "d1"
    path = tmp_path / "c.json"
    assert save_catalog(merged, path) == 2
    assert load_catalog(path) == merged
    assert load_catalog(tmp_path / "nao_existe.json") == []
