"""Valida notebooks/*.ipynb (nbformat) e conta células com outputs.

Uso: python -m scripts.validate_notebooks [--require-outputs]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-outputs", action="store_true")
    args = parser.parse_args()

    ok = True
    print(f"{'notebook':44s} {'células':>8s} {'código':>7s} {'c/ output':>10s}")
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        nb = nbformat.read(path, as_version=4)
        try:
            nbformat.validate(nb)
        except nbformat.ValidationError as exc:
            ok = False
            print(f"{path.name:44s} INVÁLIDO: {exc}")
            continue
        code_cells = [c for c in nb.cells if c.cell_type == "code"]
        with_outputs = [c for c in code_cells if c.get("outputs")]
        print(f"{path.name:44s} {len(nb.cells):8d} {len(code_cells):7d} {len(with_outputs):10d}")
        if args.require_outputs and not with_outputs:
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
