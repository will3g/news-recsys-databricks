# Roteiro da aula (~90 min)

Fio condutor: **"o modelo se re-treina sozinho todo dia e não pode piorar"**.
Material: diagramas de [`ARQUITETURA.md`](ARQUITETURA.md), os 3 notebooks (com resultados) e o app.

| Bloco | Tempo | Material | Mensagem |
|---|---|---|---|
| 1. Problema e arquitetura | 15 min | diagrama 1 | um recomendador é dado + modelo + operação |
| 2. Dados | 15 min | `01_dados` + Catalog | matérias reais, cliques sintéticos, tudo com endereço no catálogo |
| 3. Treino e gate | 25 min | diagrama 2 + `02_treino` + Experiments | baseline primeiro; o MLflow guarda tudo; só promove se for melhor |
| 4. Recomendações e app | 15 min | `03_recomendacoes` + app | batch → tabela → app |
| 5. Automação | 15 min | diagrama 3 + GitHub Actions + `job.yml` | CI, deploy e cron; Terraform cuida do GitHub |
| 6. Fechamento | 5 min | diagrama 1 | o ciclo completo |

## Falas-chave

1. "Todo portal tem 'recomendado para você'. Hoje o foco é o que mantém isso funcionando sozinho."
2. "Não temos cliques reais, então simulamos. Com dados reais, só este notebook mudaria."
3. "Se o modelo sofisticado não ganha da popularidade, ele não se paga." · "O item-CF não vê
   matéria nova — olhem a coluna de matérias frias zerada."
4. "O app nunca usa 'a última versão'. Usa `@champion`. Rollback é mover um ponteiro."
5. "O GitHub busca o dado porque o Databricks Free Edition não tem internet."

## Demonstrações

- **App:** trocar entre um leitor *torcedor* e um *investidor*.
- **Gate:** rodar o Job de novo → o NDCG empata e o modelo **não** é promovido.
- **GitHub:** abrir um PR → o CI roda → merge → o `cd.yml` publica.

## Exercícios

1. Mudar `alpha` no `score_hibrido` (0,2 · 0,6): o que acontece com o NDCG e com as matérias frias?
2. Criar uma persona nova em `PERSONAS` e procurar um leitor dela no app.
3. Trocar a métrica do gate de NDCG para `hit_fria_10`: quem vira campeão? Faz sentido para o negócio?
