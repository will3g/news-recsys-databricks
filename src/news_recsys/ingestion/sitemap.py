"""Parser do sitemap de notícias (Google News Sitemap) do O Globo.

Copiado do projeto da aula anterior (mlops-rag-databricks) — mesmo formato de entrada.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

NAMESPACES: dict[str, str] = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
}


@dataclass(frozen=True)
class ArticleMeta:
    url: str
    title: str
    published_at: str
    image_url: str | None = None


def parse_sitemap(xml_content: str | bytes) -> list[ArticleMeta]:
    """Extrai url/título/data/imagem de cada ``<url>``; ignora entradas sem ``<loc>``."""
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")
    root = ET.fromstring(xml_content)

    metas: list[ArticleMeta] = []
    for url_el in root.findall("sm:url", NAMESPACES):
        loc = (url_el.findtext("sm:loc", default="", namespaces=NAMESPACES) or "").strip()
        if not loc:
            continue
        title = (
            url_el.findtext("news:news/news:title", default="", namespaces=NAMESPACES) or ""
        ).strip()
        published_at = (
            url_el.findtext("news:news/news:publication_date", default="", namespaces=NAMESPACES)
            or ""
        ).strip()
        image = url_el.findtext("image:image/image:loc", default=None, namespaces=NAMESPACES)
        metas.append(
            ArticleMeta(
                url=loc,
                title=title,
                published_at=published_at,
                image_url=image.strip() if image else None,
            )
        )
    return metas
