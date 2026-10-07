"""Importar o pacote (exceto pyfunc_model) não pode puxar SDKs pesados."""

import subprocess
import sys

FORBIDDEN = ["pyspark", "mlflow", "databricks"]
MODULES = [
    "news_recsys.config",
    "news_recsys.ingestion.catalog",
    "news_recsys.simulation",
    "news_recsys.models",
    "news_recsys.training",
    "news_recsys.registry",
    "news_recsys.monitoring",
]


def test_no_heavy_sdk_imported_at_module_level() -> None:
    code = (
        "import importlib, sys\n"
        f"for m in {MODULES!r}: importlib.import_module(m)\n"
        f"print(','.join(m for m in {FORBIDDEN!r} if m in sys.modules))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == ""
