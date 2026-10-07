"""Editoria (section) e subeditoria a partir da URL da matéria.

Ex.: ``https://oglobo.globo.com/esportes/futebol/noticia/...`` → section ``esportes``,
subsection ``esportes/futebol``.
"""

from __future__ import annotations

from urllib.parse import urlparse

KNOWN_SECTIONS: frozenset[str] = frozenset(
    {
        "blogs",
        "brasil",
        "ciencia",
        "cultura",
        "economia",
        "ela",
        "esportes",
        "mundo",
        "opiniao",
        "patrocinado",
        "politica",
        "rio",
        "saude",
        "tecnologia",
    }
)
# Seções "satélite" mapeadas para a editoria principal
SECTION_ALIASES: dict[str, str] = {
    "apuracao-eleicoes-2026": "politica",
    "play": "cultura",
    "rioshow": "cultura",
}
# Conteúdo patrocinado não entra no catálogo recomendável
NON_RECOMMENDABLE: frozenset[str] = frozenset({"patrocinado"})
OTHER = "outros"
_STOP_SEGMENTS = {"noticia", "post", "coluna", "video", "podcast"}


def _segments(url: str) -> list[str]:
    return [s for s in urlparse(url).path.split("/") if s]


def section_from_url(url: str) -> str:
    segments = _segments(url)
    if not segments:
        return OTHER
    first = segments[0].lower()
    first = SECTION_ALIASES.get(first, first)
    return first if first in KNOWN_SECTIONS else OTHER


def subsection_from_url(url: str) -> str:
    """``<section>/<segundo segmento>`` quando é subeditoria; senão só a section."""
    section = section_from_url(url)
    segments = _segments(url)
    if len(segments) < 2:
        return section
    second = segments[1].lower()
    if second in _STOP_SEGMENTS or second.isdigit() or second.endswith(".ghtml"):
        return section
    return f"{section}/{second}"


def is_recommendable(section: str) -> bool:
    return section not in NON_RECOMMENDABLE
