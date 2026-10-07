"""Gera notebooks/*.ipynb a partir de scripts/nb/nbNN_*.py (sem outputs).

Uso: python -m scripts.build_notebooks [--only 03]

Depois de rodar os notebooks no Databricks, `make export-notebooks` sobrescreve os .ipynb
COM outputs — a partir daí, os arquivos exportados são a fonte da verdade para a aula.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import nbformat
from nbformat.v4 import new_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"

NOTEBOOKS: dict[str, str] = {
    "00": "00_tour_databricks",
    "01": "01_ingestao_bronze",
    "02": "02_eventos_sinteticos",
    "03": "03_treino_mlflow",
    "04": "04_avaliacao_registro",
    "05": "05_inferencia_batch",
    "06": "06_monitoramento",
}


def build_one(number: str, name: str) -> Path:
    module = importlib.import_module(f"scripts.nb.nb{name}")
    nb = new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    nb.cells = module.cells(ROOT)
    nbformat.validate(nb)
    path = OUT / f"{name}.ipynb"
    nbformat.write(nb, path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="números dos notebooks (ex.: 00 03)")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    selected = args.only or list(NOTEBOOKS)
    for number in selected:
        path = build_one(number, NOTEBOOKS[number])
        n_cells = len(nbformat.read(path, as_version=4).cells)
        print(f"{path.relative_to(ROOT)}  ({n_cells} células)")


if __name__ == "__main__":
    main()
