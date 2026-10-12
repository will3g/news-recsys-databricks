# Guia do professor — Databricks do zero para esta aula

Este guia é para quem **não usa Databricks no dia a dia** e precisa conduzir a aula com
segurança. Leia uma vez inteiro; na véspera, siga só o **Checklist do ensaio**.

---

## 1. O que você precisa saber (e o que pode dizer "não sei, vamos ver juntos")

**Precisa saber explicar:**
- O que é o Unity Catalog (`catálogo.schema.tabela`) e um Volume (pasta de arquivos governada).
- Que uma tabela Delta guarda histórico (`DESCRIBE HISTORY`) e aceita `MERGE`.
- Que o MLflow registra **runs** (parâmetros + métricas + artefatos) e o Unity Catalog guarda
  **versões** de modelo com **aliases** (`@champion`).
- Que um **Job** encadeia notebooks como tasks e o **Asset Bundle** descreve o Job em YAML.
- Que a Free Edition é serverless: ninguém cria máquina.

**Pode responder "fora do escopo":** Spark tuning, clusters clássicos, Photon, Delta Live
Tables, Feature Store, Model Serving em tempo real, Lakehouse Monitoring, governança avançada.

## 2. Glossário de bolso

| Termo | Explicação em uma linha |
|---|---|
| Workspace | o "site" do Databricks da sua conta (pastas, notebooks, jobs) |
| Unity Catalog (UC) | catálogo único de dados e modelos, com permissões |
| Catálogo / schema | `workspace` (padrão da Free Edition) / `news_recsys_dev` (o nosso) |
| Volume | pasta de arquivos dentro de um schema: `/Volumes/workspace/news_recsys_dev/raw/` |
| Delta | formato de tabela (Parquet + log de transações): ACID, histórico, `MERGE` |
| Serverless | compute gerenciado; o notebook "conecta" sozinho |
| Notebook task | um notebook executado como passo de um Job |
| Task values | variáveis passadas entre tasks (`dbutils.jobs.taskValues`) — usamos para a versão do modelo |
| Widget | parâmetro de notebook (`dbutils.widgets`) = parâmetro do Job |
| MLflow run | um treino registrado (params, métricas, artefatos) |
| Registered model | modelo no UC (`workspace.<schema>.news_recommender`) com versões 1, 2, 3... |
| Alias | apelido móvel para uma versão (`@champion`) |
| Asset Bundle (DAB) | `databricks.yml`: IaC do projeto; `bundle deploy` publica tudo |
| Target | ambiente do bundle (`dev` = sua cópia com prefixo; `prod` = oficial) |
| SQL warehouse | compute para consultas SQL — o app Streamlit usa um |
| PAT | Personal Access Token: senha de API (CLI, GitHub Actions, Streamlit) |

## 3. Mapa da interface (menu lateral)

| Menu | O que mostrar | O que dizer |
|---|---|---|
| **Workspace** → Users → você → `.bundle/news-recsys-databricks/dev/files` | notebooks e `src/` publicados pelo bundle | "isto veio do Git com um comando" |
| **Catalog** → `workspace` → `news_recsys_dev` | tabelas bronze/silver/gold, Volume `raw`, modelo `news_recommender` | "tudo tem endereço e dono" |
| Catalog → tabela → aba **History** | versões do Delta | "auditoria grátis" |
| Catalog → `news_recommender` | versões, alias `@champion`, tags `gate_decision` | "o app usa o alias, não a versão" |
| **Jobs & Pipelines** → `[dev ...] news-recsys-pipeline` | DAG das 6 tasks, execuções, logs | "isso roda sozinho todo dia" |
| **Experiments** → `news_recsys_...` | runs pai/filhas, comparar (selecionar runs → *Compare*) | "planilha automática de treinos" |
| **SQL Warehouses** | o *Serverless Starter Warehouse* | "é por aqui que o app lê" |

## 4. Setup inicial (uma vez, ~30 min)

1. **Conta:** <https://www.databricks.com/learn/free-edition> → login com Google/Microsoft/e-mail.
2. **Token:** avatar (canto superior direito) → **Settings** → **Developer** → **Access tokens** →
   *Generate new token* (comentário `aula-fiap`, validade 90 dias). Copie o `dapi...`.
3. **Terminal**, na pasta do projeto:
   ```bash
   make doctor                  # confere as ferramentas (macOS, Linux ou Windows/WSL)
   make install                 # ambiente Python local
   make db-install              # CLI do Databricks (script oficial; não faz nada se já existir)
   make db-configure            # cole a URL do workspace e o token
   make db-check                # deve mostrar seu e-mail e o SQL warehouse
   make bundle-validate
   make bundle-deploy           # publica notebooks + job no target dev
   ```
4. **Primeira execução completa** (≈5–10 min): `make bundle-run`. Acompanhe em
   *Jobs & Pipelines*. Ao final, `@champion` = versão 1.
5. **Notebooks com output para a aula:** abra cada notebook em
   `Workspace → .bundle/.../dev/files/notebooks`, clique **Run all** (00 → 06, nesta ordem),
   depois `make export-notebooks` (traz os `.ipynb` com resultados para o repositório).
6. **SQL warehouse para o app:** *SQL Warehouses* → *Serverless Starter Warehouse* →
   *Connection details* → copie **Server hostname** e **HTTP path**.
7. **App local contra o Lakehouse:** copie `app/.streamlit/secrets.toml.example` para
   `app/.streamlit/secrets.toml`, preencha (schema `news_recsys_dev` para testar) e `make app`.
8. **GitHub + Streamlit Cloud:** siga o README (Terraform → push → CI/CD → Streamlit Cloud com
   `schema = "news_recsys"`, que é o target `prod`).

### Alunos com Windows

Peça na aula anterior (ou por e-mail) para instalarem o **WSL2 com Ubuntu** antes:
`wsl --install -d Ubuntu-24.04` no PowerShell como administrador. É a causa nº 1 de aluno
travado no primeiro dia. Dentro do WSL, `make doctor` mostra exatamente o que falta. Quem não
puder usar WSL: `winget install Databricks.DatabricksCLI` e comandos manuais (README).

## 5. Checklist do ensaio (véspera, 20 min)

- [ ] `make db-check` funciona (token não expirou).
- [ ] Última execução do Job em *Jobs & Pipelines* está verde.
- [ ] Modelo tem `@champion` (Catalog → `news_recommender`).
- [ ] Notebooks exportados abrem no VS Code com gráficos (`make validate-notebooks` mostra outputs > 0).
- [ ] App no Streamlit Cloud abre e mostra "Fonte: Lakehouse" (se mostrar "amostra local", veja §7).
- [ ] Abas abertas: Catalog, Jobs, Experiments, notebook 03, app, GitHub Actions.
- [ ] Rode **uma** célula leve ao vivo para "acordar" o serverless (ex.: notebook 00, célula do `spark.range`).

## 6. O que rodar ao vivo × o que só mostrar

| Seguro ao vivo (segundos) | Só mostrar o output gravado |
|---|---|
| notebook 00 (tour), contagens de tabelas | Job completo (minutos) |
| notebook 02: simulação e mapa de calor | primeira criação de schema/volume |
| notebook 03: a célula de comparação (se o cluster estiver quente) | `log_model` + registro (≈1 min) |
| notebook 04: a célula da decisão do gate | deploy do bundle / Terraform |
| app Streamlit trocando de usuário | Streamlit Cloud rebuild |

**Truque didático do gate:** rode o Job de novo com o mesmo `seed` → a versão nova empata e
**não** é promovida (tag `gate_decision = rejected`). Mostra o quality gate funcionando.

## 7. Se algo der errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `Error: default auth: cannot configure default credentials` | CLI sem token | `make db-configure` |
| `PipError ... 403 Forbidden ... Server Side Encryption` na 1ª célula | `%pip` no Job serverless (falha ao salvar o snapshot do ambiente) | já tratado: a célula 1 só instala se faltar pacote; o Job usa o `environments` do bundle |
| `make: command not found` (Windows) | rodando no PowerShell/CMD | abrir o terminal do Ubuntu (WSL) |
| `Target path ... already exists` na instalação da CLI | CLI já instalada em outro caminho | `databricks --version`; se funcionar, pode seguir |
| `/usr/local/bin is not writable` | instalação da CLI sem permissão | `sudo make db-install` |
| `401/403` no CLI, Actions ou app | PAT expirou | gerar novo token; atualizar `~/.databrickscfg`, `TF_VAR_databricks_token` + `make tf-apply`, secrets do Streamlit |
| Notebook: `src/ não encontrado` | notebook aberto fora da pasta do bundle | abrir pelo caminho `.bundle/.../files/notebooks` |
| `TABLE_OR_VIEW_NOT_FOUND silver_*` | notebooks fora de ordem | rodar 01 → 02 antes do 03 |
| `get_model_version_by_alias` falha no 05 | nunca houve promoção | rodar o 04 (o primeiro modelo sempre é promovido) |
| App mostra "amostra local" | secrets ausentes ou warehouse parado/schema errado | conferir secrets; abrir o warehouse; `schema` correto |
| App demora ~10 s na 1ª consulta | warehouse "acordando" | normal; cache de 10 min depois |
| `ingest.yml` falha em `fs cp` | Volume não existe | rodar o job uma vez ou `make bundle-run` |
| Job ok mas métricas iguais todo dia | mesmo `seed` e catálogo | esperado; mude `seed` no Job para mostrar variação |

**Plano B universal:** os notebooks exportados (com outputs) e o app em modo amostra (`make app`)
funcionam sem Databricks. A aula não depende de nada estar no ar.

## 8. Perguntas prováveis dos alunos

**"Os dados são falsos, então o modelo serve pra quê?"** — O pipeline é o produto da aula.
Trocar `silver_interactions` por eventos reais não muda nenhuma outra etapa. E as métricas
mostram que o modelo recupera o padrão escondido (personas) melhor que o baseline.

**"Por que não Spark ML / ALS?"** — Volume pequeno; scikit-learn no driver é mais simples e o
suporte a Spark ML no serverless é limitado. Em escala, troca-se o `models/svd.py` por ALS.

**"Por que batch e não uma API?"** — Recomendação de home muda pouco em minutos; batch é barato
e o app só lê uma tabela. Tempo real entra quando o contexto imediato importa.

**"E matéria nova, sem cliques?"** — *Cold start*: CF e SVD não recomendam (0% na métrica
`cold_hit_rate_at_k`). O modelo de **conteúdo** usa título + editoria, que existem desde o
primeiro minuto; o **híbrido** (`α·CF + (1−α)·conteúdo`) junta os dois e é o campeão.
α maior favorece matérias com histórico, α menor favorece as novas: é uma decisão de negócio
medida no MLflow. Usuário novo, sem histórico, recebe popularidade com recência.

**"Por que o Terraform não cria o Databricks?"** — Na Free Edition não há API de conta;
workspace e catálogo já vêm prontos. O IaC do projeto no Databricks é o Asset Bundle. O
Terraform gerencia o que faltava: o GitHub (repo, secrets, proteção da branch).

**"Precision@10 de 0,11 não é baixo?"** — Em recsys é comum: o usuário lê poucas das centenas
de matérias. Compare sempre com o baseline (0,017) — o ganho relativo é o que importa.

**"Por que o híbrido com α=0,4 e não o de conteúdo puro, que acerta mais matérias frias?"** —
Porque o objetivo de promoção é o NDCG geral; o conteúdo puro perde o sinal "quem leu X leu Y".
Se o negócio priorizar notícia fresca, troque a métrica de promoção ou baixe o α.

**"Isso é LGPD-safe?"** — Usuários são sintéticos; em produção, clickstream é dado pessoal
(consentimento, minimização, retenção). Boa discussão para a turma.
