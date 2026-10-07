# Arquitetura

## Fluxo

```
            ┌──────────────────────── GitHub ────────────────────────┐
            │ ingest.yml (cron 06:00)  ci.yml (PR/push)  cd.yml (main)│
            └──────┬─────────────────────────┬──────────────────┬────┘
   sitemap O Globo │                         │ validate         │ bundle deploy -t prod
                   ▼                         ▼                  ▼
   ┌──────────────────────────── Databricks Free Edition (serverless) ───────────────────────────┐
   │ Volume raw/catalog/*.json                                                                    │
   │   └► 01 bronze_articles (MERGE)                                                              │
   │        └► 02 silver_catalog_window · silver_users · silver_interactions (SINTÉTICO)          │
   │             └► 03 treino: popularidade · item_cf · svd · conteúdo · híbrido ── MLflow runs   │
   │                  └► vencedor re-treinado ─► Unity Catalog: news_recommender vN               │
   │                       └► 04 gate: NDCG@10(vN) > NDCG@10(@champion)? ─► alias @champion      │
   │                            └► 05 inferência batch (@champion) ─► gold_user_recommendations   │
   │                                 └► 06 monitoramento ─► recs_monitoring · model_metrics       │
   └───────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                   │ SQL warehouse (databricks-sql-connector)
                                                   ▼
                                 App Streamlit (Community Cloud) ── fallback: app/sample_data
```

## Quem gerencia o quê (e por que o Terraform só cuida do GitHub)

| Camada | Ferramenta | Por quê |
|---|---|---|
| Repositório, secrets, environments, proteção da main | **Terraform** (`infra/github`) | configuração repetível e revisável do GitHub |
| Job, notebooks, código no workspace | **Databricks Asset Bundle** | IaC nativo do Databricks; deploy por target (dev/prod) |
| Schema, Volume, tabelas | Notebooks (`CREATE ... IF NOT EXISTS`) e o próprio Job | idempotente e visível na aula |
| Modelo e aliases | MLflow + Unity Catalog | ciclo de vida do modelo (não é infraestrutura) |
| App | Streamlit Community Cloud (UI) | não há API/provider Terraform |

Na Free Edition não há console nem API de conta: workspace, metastore, rede e storage já vêm
prontos — que é justamente o que o Terraform costuma provisionar em empresas.

## Decisões

1. **Cliques sintéticos** com personas e `seed`: não existe clickstream público; o formato
   (user, item, timestamp) é o mesmo de um log real, então só esta etapa mudaria em produção.
2. **scikit-learn/scipy no driver**, não Spark ML (ALS): volume pequeno e suporte a Spark ML
   no serverless não é garantido. Os dados entram/saem por Delta.
3. **Split temporal por usuário** (20% mais recentes = teste): evita vazamento do futuro.
4. **NDCG@10 como métrica de promoção**: valoriza acertos no topo da lista.
5. **Alias `@champion`** em vez de "última versão": rollback = mover o alias.
6. **Inferência batch** + tabela gold: latência mínima no app, custo baixo, modelo versionado
   em cada linha (`model_version`).
7. **Ingestão no GitHub Actions**: o Databricks Free Edition não tem internet de saída liberada.
8. **Híbrido CF + conteúdo para o cold start**: CF/SVD têm 0% de acerto em matérias sem clique;
   o termo de conteúdo (TF-IDF de título + editoria, com decaimento por recência) cobre as novas.
   α=0,4 maximiza o NDCG e mantém ~20% de acerto nas frias (varredura α ∈ 0,2–0,6, 2 seeds).
9. **App com fallback** para `sample_data`: a demo não depende do warehouse estar ligado.

## Tabelas (`workspace.<schema>`)

| Tabela | Grão | Escrita |
|---|---|---|
| `bronze_articles` | matéria | 01 — MERGE por `article_id` |
| `silver_catalog_window` | matéria na janela de 3 dias | 02 — overwrite |
| `silver_users` | usuário sintético (persona, preferências) | 02 — overwrite |
| `silver_interactions` | clique (user, article, event_ts) | 02 — overwrite |
| `model_metrics` | (execução, candidato, métrica) | 04 — append |
| `gold_user_recommendations` | (usuário, rank) + metadados + `model_version` | 05 — overwrite |
| `recs_monitoring` | (execução, métrica) | 06 — append |
