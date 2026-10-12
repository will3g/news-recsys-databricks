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
| Jobs & Pipelines → `[dev ...] news-recsys-dev` (ou `news-recsys-qa` / `news-recsys-prod`) | as 3 tasks e o histórico de execuções |
| ... → clique numa execução → clique na task | o notebook **com os resultados** daquela execução |
| Experiments → `news_recsys_dev` (um por ambiente) | runs dos 3 modelos (selecione e clique em *Compare*) |

**Três ambientes, um workspace:** `dev` (o seu, pelo `make`), `qa` (merge na `develop`) e
`prod` (merge na `main`). Cada um tem schema, Job, modelo e experimento próprios
(`news_recsys_<ambiente>`). Qualquer comando do `make` aceita `TARGET=qa` ou `TARGET=prod`.

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
   ```
4. Vai em **SQL Editor**:
   ```
   WITH lidas AS (
    SELECT u.persona, a.section, count(*) AS n
    FROM workspace.news_recsys_dev.silver_clicks c
    JOIN workspace.news_recsys_dev.silver_users u USING (user_id)
    JOIN workspace.news_recsys_dev.bronze_articles a USING (url)
    GROUP BY ALL
   ),
   recomendadas AS (
     SELECT u.persona, g.section, count(*) AS n
     FROM workspace.news_recsys_dev.gold_recommendations g
     JOIN workspace.news_recsys_dev.silver_users u USING (user_id)
     GROUP BY ALL
   )
   SELECT persona, section,
         round(100 * coalesce(l.n, 0) / sum(l.n) OVER (PARTITION BY persona), 1) AS pct_lidas,
         round(100 * coalesce(r.n, 0) / sum(r.n) OVER (PARTITION BY persona), 1) AS pct_recomendadas
   FROM lidas l
   FULL JOIN recomendadas r USING (persona, section)
   QUALIFY pct_lidas >= 5 OR pct_recomendadas >= 5
   ORDER BY persona, pct_lidas DESC
   ```
5. Volta para o **terminal** e executa:
   ```
   make install && make app
   ```

Alunos com **Windows**: peça que instalem o WSL antes da aula
(`wsl --install -d Ubuntu-24.04` no PowerShell como administrador).

## 3. Checklist da véspera

- [ ] `make run` terminou verde (3 tasks).
- [ ] O modelo tem o alias `@champion` (Catalog → `news_recommender`).
- [ ] A última execução do Job abre as 3 tasks com os resultados.
- [ ] `make app` mostra as recomendações.
- [ ] Abas abertas: Catalog, Jobs, Experiments, app, GitHub Actions.

**Recomeçar do zero** (antes de um ensaio ou depois da aula): `make db-destroy` (pede
confirmação; apaga Job, notebooks, tabelas, Volume, modelo e experimento do ambiente dev) e
depois `make setup deploy run`.

**Plano B:** o app funciona sem Databricks (amostra) e a última execução do Job fica no
histórico por 60 dias. Sem internet, sobram o app e os diagramas.

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
- **"NDCG de 0,09 não é baixo?"** Em recomendação é comum: cada pessoa lê poucas das ~3.100
  matérias. Compare com o baseline (0,001) e com o item-CF (0,037).
- **"Por que batch e não API?"** Recomendação de home muda pouco em minutos; batch é barato e
  o app só faz um `SELECT`.
- **"Por que o Terraform não cria o Databricks?"** Na Free Edition o workspace já vem pronto;
  o Job é do Asset Bundle. O Terraform cuida do GitHub.
- **"É LGPD-safe?"** Aqui sim (dados sintéticos). Com cliques reais: consentimento,
  minimização e retenção.
