"""Recomendação de notícias com MLOps no Databricks (aula FIAP Pós-Tech, Fase 5).

Regra do pacote: nenhum módulo importa pyspark/mlflow/databricks no nível de módulo — exceto
``pyfunc_model.py`` (ele *é* o modelo logado). Assim os testes rodam localmente, sem Databricks.
"""

__version__ = "0.1.0"
