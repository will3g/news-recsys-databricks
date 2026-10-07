"""Notebook 03 — Treino de 3 modelos com MLflow e registro no Unity Catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.nb._common import (
    BOOTSTRAP_CELL,
    LOAD_SILVER_CELL,
    MLFLOW_CELL,
    PIP_CELL,
    code,
    header,
    md,
    source_cell,
)


def cells(root: Path) -> list[Any]:
    return [
        header("03", "Treino com MLflow", "Popularidade × colaborativo × SVD × conteúdo × híbrido"),
        md(
            """
            ## Cinco jeitos de recomendar

            | Modelo | Ideia | Pergunta que responde |
            |---|---|---|
            | **Popularidade** (baseline) | o que todo mundo está lendo agora | "o que está bombando?" |
            | **Item-item CF** | quem leu X também leu Y (cosseno entre colunas da matriz usuário×matéria) | "parecido com o que você leu" |
            | **Fatoração de matriz (SVD)** | usuários e matérias num espaço de *gostos latentes* | "gente com seu gosto leu..." |
            | **Conteúdo (TF-IDF)** | perfil do usuário = títulos/editorias que leu; compara com cada matéria | "assunto parecido" — inclusive matéria nova |
            | **Híbrido** | `α · CF + (1 − α) · conteúdo` | o melhor dos dois |

            O baseline é obrigatório: **se o modelo sofisticado não ganha da popularidade, ele não
            se paga.** Todos treinam no mesmo split e são medidos com as mesmas métricas.
            """
        ),
        md(
            """
            ## Como avaliar um recomendador (offline)

            - **Split temporal**: para cada usuário, os 20% cliques mais recentes viram teste.
              Nunca aleatório — em produção o modelo sempre prevê o *futuro*.
            - **Precision@10**: dos 10 recomendados, quantos ele leu?
            - **Recall@10**: do que ele leu, quanto estava nos 10?
            - **NDCG@10**: como o Recall, mas acertar no **topo** da lista vale mais. ← *métrica de promoção*
            - **HitRate@10**: acertou pelo menos um?
            - **Cobertura**: que fração do catálogo aparece em alguma recomendação (diversidade).
            - **HitRate@10 em matérias frias**: entre quem leu alguma matéria *sem clique no treino*,
              quantos a receberam? Mede o **cold start** — o problema central em notícia.
            """
        ),
        PIP_CELL,
        BOOTSTRAP_CELL,
        MLFLOW_CELL,
        LOAD_SILVER_CELL,
        md("### `models/base.py` — o contrato comum"),
        source_cell("src/news_recsys/models/base.py", root),
        md("### `models/popularity.py`, `models/item_cf.py`, `models/svd.py`"),
        source_cell("src/news_recsys/models/popularity.py", root),
        source_cell("src/news_recsys/models/item_cf.py", root),
        source_cell("src/news_recsys/models/svd.py", root),
        md("### `models/content.py` e `models/hybrid.py` — a resposta ao *cold start*"),
        source_cell("src/news_recsys/models/content.py", root),
        source_cell("src/news_recsys/models/hybrid.py", root),
        md("### `evaluation/split.py`, `evaluation/metrics.py` e `training.py`"),
        source_cell("src/news_recsys/evaluation/metrics.py", root),
        source_cell("src/news_recsys/training.py", root),
        md(
            """
            ### Execução: treinando os candidatos — uma *run* do MLflow para cada

            Uma run "pai" agrupa o treino do dia; cada candidato vira uma run "filha" com seus
            parâmetros e métricas. Depois abra **Experiments** no menu e compare lado a lado.
            """
        ),
        code(
            """
            from datetime import UTC, datetime

            from news_recsys.training import DEFAULT_CANDIDATES, best_candidate, refit_full, train_candidates

            run_name = f"treino-{datetime.now(UTC):%Y%m%d-%H%M}"
            parent = mlflow.start_run(run_name=run_name)
            mlflow.log_params({"n_users": settings.n_users, "seed": settings.seed, "n_articles": len(articles), "n_clicks": len(clicks), "k": settings.k})

            results = train_candidates(clicks, articles, DEFAULT_CANDIDATES, k=settings.k, test_fraction=settings.test_fraction)
            for r in results:
                with mlflow.start_run(run_name=r.label, nested=True):
                    mlflow.log_param("model", r.name)
                    mlflow.log_params(r.params)
                    mlflow.log_metrics(r.metrics)

            comparison = pd.DataFrame([{"candidato": r.label, **r.metrics} for r in results]).set_index("candidato")
            comparison.drop(columns="n_users_eval").sort_values("ndcg_at_k", ascending=False).round(4)
            """
        ),
        md("### Visualizando a comparação"),
        code(
            """
            import matplotlib.pyplot as plt

            ax = comparison[["ndcg_at_k", "hit_rate_at_k", "cold_hit_rate_at_k"]].sort_values("ndcg_at_k").plot.barh(figsize=(9, 5))
            ax.set_title("Candidatos — avaliação offline (@10)")
            ax.set_xlabel("valor")
            plt.tight_layout()
            display(ax.figure)
            """
        ),
        md(
            """
            ### Execução: o vencedor é re-treinado com TODOS os dados e registrado

            Escolhemos pelo NDCG@10, re-treinamos com todos os cliques (o teste era só para medir)
            e logamos como **modelo MLflow (pyfunc)** com assinatura e exemplo de entrada.
            `registered_model_name` cria uma **nova versão** no Unity Catalog — que ainda **não**
            é a campeã: quem decide é o notebook 04.
            """
        ),
        source_cell("src/news_recsys/pyfunc_model.py", root),
        code(
            """
            from news_recsys.pyfunc_model import log_recommender

            best = best_candidate(results, settings.promotion_metric)
            production_model = refit_full(best, clicks, articles)

            mlflow.log_param("winner", best.label)
            mlflow.log_metrics(best.metrics)  # métricas do vencedor na run pai (usadas pelo quality gate)
            model_info = log_recommender(
                production_model,
                code_path=str(SRC / "news_recsys"),
                sample_users=users["user_id"].tolist(),
                registered_model_name=settings.model_fqn,
                k=settings.k,
            )
            run_id = parent.info.run_id
            mlflow.end_run()

            version = str(model_info.registered_model_version)
            print(f"vencedor: {best.label}  |  NDCG@10 = {best.metrics['ndcg_at_k']:.4f}")
            print(f"registrado: {settings.model_fqn} versão {version}  (run {run_id})")

            # Passa a versão para a próxima task do Job (04_avaliacao_registro)
            dbutils.jobs.taskValues.set(key="model_version", value=version)
            dbutils.jobs.taskValues.set(key="run_id", value=run_id)
            """
        ),
        md("### Execução: o modelo registrado funciona fora deste notebook?"),
        code(
            """
            loaded = mlflow.pyfunc.load_model(f"models:/{settings.model_fqn}/{version}")
            loaded.predict(pd.DataFrame({"user_id": users["user_id"].head(2)})).merge(
                articles[["article_id", "section", "title"]], on="article_id"
            )
            """
        ),
        md(
            """
            ### Leitura do resultado: o *cold start* em números

            - **CF e SVD acertam 0% das matérias frias**: só recomendam o que já foi clicado.
            - **Conteúdo** acerta as frias (título e editoria existem desde o primeiro minuto),
              mas perde o sinal fino de "quem leu X leu Y".
            - **Híbrido** junta os dois. O **α** é um *trade-off*: α alto = mais CF (melhor em
              matérias com histórico), α baixo = mais conteúdo (melhor em matérias novas). O MLflow
              escolhe pelo NDCG; a coluna `cold_hit_rate_at_k` mostra o custo de cada escolha.
            - Usuário novo (sem histórico) continua recebendo popularidade com bônus de recência.
            """
        ),
        md(
            """
            ### O que percebemos?

            - O baseline perde feio — personalização **vale a pena** (com estes dados).
            - O híbrido vence no geral **e** recomenda matérias novas: o melhor modelo é o que cobre o problema do negócio, não o mais sofisticado.
            - O MLflow guardou tudo: parâmetros, métricas, o artefato e de onde ele veio (*lineage*).
            - Registrar ≠ publicar: a versão nova espera o *quality gate*.

            **Próximo:** `04_avaliacao_registro`.
            """
        ),
    ]
