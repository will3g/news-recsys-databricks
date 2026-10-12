# Guia do professor

Para quem não usa Databricks no dia a dia. Leia uma vez; na véspera, faça só o **checklist**.

## 1. O mínimo de Databricks

| Termo | Em uma linha |
|---|---|
| Workspace | o "site" do Databricks da sua conta |
| Unity Catalog | catálogo de dados e modelos: `workspace.news_recsys_dev.tabela` |
| Volume | pasta de arquivos dentro do catálogo (`/Volumes/workspace/news_recsys_dev/raw/`) |
| Delta | formato das tabelas (Parquet + histórico de versões) |
| Serverless | o compute liga sozinho; ninguém cria máquina |
| Job | notebooks encadeados como tasks, com agenda e histórico |
| Asset Bundle | `databricks.yml`: o Job descrito em código; `make deploy` publica |
| MLflow run | um treino registrado (parâmetros + métricas + modelo) |
| Versão / alias | cada registro do modelo vira versão 1, 2, 3...; `@champion` aponta para a que está em uso |

**Onde clicar (menu da esquerda):**

| Menu | O que mostrar |
|---|---|
| Workspace → `.bundle/news-recsys-databricks/dev/files/notebooks` | os 3 notebooks publicados |
| Catalog → `workspace` → `news_recsys_dev` | tabelas, Volume `raw` e o modelo `news_recommender` (aliases) |
| Jobs & Pipelines → `[dev ...] news-recsys` | as 3 tasks e o histórico de execuções |
| Experiments → `news_recsys` | runs dos 3 modelos (selecione e clique em *Compare*) |

## 2. Preparação (uma vez, ~20 min)

1. Conta Free Edition: <https://www.databricks.com/learn/free-edition>.
2. Token: avatar → **Settings** → **Developer** → **Access tokens** → *Generate new token*.
3. No terminal, na pasta do projeto:
   ```bash
   make doctor
   make db-install
   make db-configure      # URL do workspace + token
   make setup
   make deploy
   make run               # ~5 min; acompanhe em Jobs & Pipelines
   make export-notebooks  # notebooks com os resultados, para mostrar em aula
   make install && make app
   ```

Alunos com **Windows**: peça que instalem o WSL antes da aula
(`wsl --install -d Ubuntu-24.04` no PowerShell como administrador).

## 3. Checklist da véspera

- [ ] `make run` terminou verde (3 tasks).
- [ ] O modelo tem o alias `@champion` (Catalog → `news_recommender`).
- [ ] Notebooks exportados abrem com os resultados.
- [ ] `make app` mostra as recomendações.
- [ ] Abas abertas: Catalog, Jobs, Experiments, app, GitHub Actions.

**Plano B:** os notebooks exportados já têm todos os resultados e o app funciona sem
Databricks (amostra). A aula não depende de nada estar no ar.

## 4. Se algo der errado

| Sintoma | O que fazer |
|---|---|
| `cannot configure default credentials` | `make db-configure` |
| `401`/`403` no CLI ou no app | o token expirou: gere outro |
| `no such directory ... /raw/sitemaps` | `make setup` |
| `get_model_version_by_alias` falha no 03 | rode o 02 antes (o primeiro modelo sempre vira campeão) |
| `OSError: Input/output error` lendo arquivo do workspace | não importe `.py` do workspace no Job; por isso o código está nos notebooks |
| `make: command not found` (Windows) | abra o terminal do Ubuntu (WSL) |

## 5. Perguntas prováveis

- **"Os dados são falsos?"** As matérias são reais; os cliques são simulados. Com dados
  reais, só o `01_dados` mudaria.
- **"Por que o híbrido ganha?"** O item-CF só recomenda o que já foi clicado; matéria nova
  (sem clique) fica de fora. O híbrido usa também título, editoria e recência.
- **"NDCG de 0,23 não é baixo?"** Em recomendação é comum: cada pessoa lê poucas das ~700
  matérias. Compare com o baseline (0,02).
- **"Por que batch e não API?"** Recomendação de home muda pouco em minutos; batch é barato e
  o app só faz um `SELECT`.
- **"Por que o Terraform não cria o Databricks?"** Na Free Edition o workspace já vem pronto;
  o Job é do Asset Bundle. O Terraform cuida do GitHub.
- **"É LGPD-safe?"** Aqui sim (dados sintéticos). Com cliques reais: consentimento,
  minimização e retenção.
