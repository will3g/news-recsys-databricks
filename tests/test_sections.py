import pytest

from news_recsys.features.sections import is_recommendable, section_from_url, subsection_from_url

BASE = "https://oglobo.globo.com"


@pytest.mark.parametrize(
    ("path", "section", "subsection"),
    [
        ("/economia/noticia/2026/10/07/x.ghtml", "economia", "economia"),
        ("/esportes/futebol/noticia/2026/10/07/x.ghtml", "esportes", "esportes/futebol"),
        ("/politica/eleicoes-2026/noticia/x.ghtml", "politica", "politica/eleicoes-2026"),
        ("/apuracao-eleicoes-2026/x.ghtml", "politica", "politica"),
        ("/blogs/lauro-jardim/post/2026/10/x.ghtml", "blogs", "blogs/lauro-jardim"),
        ("/algo-novo/noticia/x.ghtml", "outros", "outros"),
        ("/", "outros", "outros"),
    ],
)
def test_section_and_subsection(path: str, section: str, subsection: str) -> None:
    assert section_from_url(BASE + path) == section
    assert subsection_from_url(BASE + path) == subsection


def test_sponsored_is_not_recommendable() -> None:
    assert not is_recommendable("patrocinado")
    assert is_recommendable("economia")
