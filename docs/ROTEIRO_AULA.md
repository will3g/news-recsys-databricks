# Roteiro da aula — Recomendação de notícias com MLOps no Databricks

**Duração:** ~120 min. **Material:** [slides](https://claude.ai/artifact/8P9wuUu92SM3jFR2dNNuKt) (privado; compartilhe pelo menu Share), notebooks exportados (com outputs), app Streamlit,
repositório no GitHub (aba Actions).

| Bloco | Tempo | Material | Mensagem central |
|---|---|---|---|
| 1. Problema e arquitetura | 15 min | slides 1–6 | recsys é dado + modelo + operação |
| 2. Tour Databricks | 10 min | notebook 00 + UI | onde cada coisa mora |
| 3. Dados: bronze e eventos sintéticos | 15 min | notebooks 01–02 | ingestão desacoplada, `MERGE`, personas |
| 4. Treino e comparação | 20 min | notebook 03 + Experiments | baseline primeiro; MLflow guarda tudo |
| 5. Gate e registro | 15 min | notebook 04 + Catalog | `@champion`, rollback por alias |
| 6. Inferência e app | 15 min | notebook 05 + Streamlit | batch → tabela → app |
| 7. Monitoramento | 10 min | notebook 06 | cobertura e drift (PSI) |
| 8. CI/CD e Terraform | 15 min | GitHub Actions + `infra/github` + slides | quem gerencia o quê |
| 9. Fechamento | 5 min | slide final | o ciclo completo + próximos passos |

## Falas-chave por bloco

1. "Todo portal tem 'recomendado para você'. Hoje construímos um — e, principalmente, o que mantém ele funcionando sozinho."
2. "Dado, código, modelo e agenda no mesmo lugar, com o mesmo controle de acesso."
3. "O GitHub busca o dado porque a Free Edition não tem internet: limitação vira desenho." · "Não temos cliques reais; simulamos — e só esta etapa mudaria em produção."
4. "Se o modelo sofisticado não ganha da popularidade, ele não se paga." · "Abram Experiments: cada candidato é uma linha comparável." · "CF não vê matéria nova — olhem a coluna 'fria' zerada; o híbrido resolve."
5. "O app nunca usa 'a última versão'. Usa `@champion`. Rollback é mover um ponteiro."
6. "Recomendação pronta antes do usuário chegar: o app só faz um SELECT."
7. "Modelo bom hoje pode virar bolha amanhã: monitoramos diversidade, não só acurácia."
8. "Terraform cuida da plataforma (aqui, o GitHub); o Bundle cuida do projeto no Databricks; o CI garante que nada quebrado chegue na main."

## Demonstrações ao vivo (curtas)

- App: trocar entre um usuário *torcedor* e um *investidor*.
- Notebook 04: mostrar a decisão do gate; no Catalog, a tag `gate_decision` das versões.
- GitHub: abrir um PR trivial → CI roda `ruff`/`pytest` → merge → `cd.yml` faz deploy.
- (Se der tempo) `Run workflow` no `ingest.yml` e acompanhar o Job disparar no Databricks.

## Exercícios para os alunos

1. Adicionar um candidato `svd(n_components=64)` em `training.DEFAULT_CANDIDATES` e ver se ele vira campeão.
2. Mudar `noise` da simulação para 0.5: o que acontece com o NDCG de cada modelo? E com o PSI?
3. Criar uma persona nova em `simulation.PERSONAS` e verificar no app.
4. Mudar a métrica de promoção para `cold_hit_rate_at_k`: qual candidato vira campeão? Faz sentido para o negócio?
