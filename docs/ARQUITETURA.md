# Arquitetura

Siga os números das setas. O GitHub e o VS Code renderizam o Mermaid; para editar, use
<https://mermaid.live>.

## 1. Visão geral

```mermaid
flowchart TB
    SM[("Sitemap O Globo")]

    subgraph GH["GitHub"]
        direction LR
        CI["ci.yml<br/>lint no PR"]
        CD["cd.yml<br/>deploy"]
        ING["ingest.yml<br/>06:00"]
    end

    subgraph DBX["Databricks Free Edition"]
        VOL[("Volume raw")]
        subgraph JOB["Job news-recsys (3 tasks)"]
            direction TB
            N1["01_dados<br/>matérias + cliques<br/>+ o dado mudou?"]
            N2{"02_treino<br/>3 modelos + gate"}
            N3["03_recomendacoes<br/>top-10 + monitoramento"]
        end
        MLF[("MLflow")]
        UC[("Unity Catalog<br/>@champion")]
        GOLD[("gold_recommendations")]
    end

    APP["App Streamlit"]

    CI -. "0a · CI verde libera o merge" .-> CD
    CD -. "0b · publica o Job" .-> JOB
    SM -- "1 · baixa o sitemap" --> ING
    ING -- "2 · envia o XML" --> VOL
    ING -. "3 · roda o Job" .-> N1
    VOL -- "4 · lê" --> N1
    N1 -- "5" --> N2
    N2 -- "6 · runs" --> MLF
    N2 -- "7 · promove se for melhor" --> UC
    N2 -- "8" --> N3
    UC -- "9 · carrega @champion" --> N3
    N3 -- "10 · grava top-10" --> GOLD
    GOLD -- "11 · SELECT" --> APP
```

| # | O que acontece |
|---|---|
| 0a · 0b | (só quando há merge na `main`) CI verde → `cd.yml` publica o Job |
| 1–3 | todo dia o GitHub baixa o sitemap, envia ao Volume e roda o Job |
| 4–5 | `01_dados` lê os XMLs, limpa (lista curta + filtro de template), compara com a carga anterior (`data_monitoring`), grava as matérias e simula os cliques |
| 6–7 | `02_treino` compara 3 modelos no MLflow; o vencedor só vira `@champion` se for melhor |
| 8–10 | `03_recomendacoes` usa o `@champion` e grava o top-10 de cada leitor |
| 11 | o app lê a tabela gold |

## 2. Treino e quality gate (`02_treino`)

```mermaid
flowchart TB
    D[("silver_clicks")] -- "1 · split temporal 80/20" --> M1["Popularidade"] & M2["Item-CF"] & M3["Híbrido"]
    M1 & M2 & M3 -- "2 · NDCG@10 · HitRate · matérias frias" --> R["MLflow: 1 run por modelo"]
    R -- "3 · maior NDCG" --> W["vencedor re-treinado<br/>com todos os cliques"]
    W -- "4" --> V["Unity Catalog: versão N"]
    V --> G{"5 · NDCG(N) ><br/>NDCG(@champion)?"}
    G -- "sim" --> C["@champion = N"]
    G -- "não" --> K["mantém o campeão"]
```

Resultado com o snapshot de 03 a 12/10/2026 (3.101 matérias): **híbrido NDCG@10 = 0,090** ·
item-CF 0,037 · popularidade 0,001. Só o híbrido acerta matérias novas (33%; os outros, 0%).

## 3. Ambientes e esteira

```mermaid
flowchart LR
    DEV["dev<br/>make setup deploy run<br/>news_recsys_dev"]
    F["feature/*"] -- "1 · PR + CI" --> D["develop"]
    D -- "2 · cd.yml" --> QA["QA<br/>news_recsys_qa<br/>app: branch develop"]
    D -- "3 · PR + CI" --> M["main"]
    M -- "4 · cd.yml" --> PROD["PROD<br/>news_recsys_prod<br/>app: branch main"]
    ING["ingest.yml<br/>06:00"] -- "5 · todo dia" --> PROD
```

| # | O que acontece |
|---|---|
| — | **dev**: cada pessoa testa no seu ambiente isolado, pelo `make` |
| 1–2 | PR para `develop` roda o CI (`test` + plano do Terraform); o merge roda o CD: `infra` → `databricks` (Job em **QA**) → `streamlit` |
| 3–4 | QA ok → PR `develop` → `main`; o merge publica e roda o Job em **PROD** |
| 5 | o ingest diário só alimenta PROD |

Os três ambientes estão no **mesmo workspace** (a Free Edition só tem um), separados por schema
e pasta. Em empresa, cada ambiente costuma ter o seu workspace.

## 4. Quem gerencia o quê

```mermaid
flowchart LR
    MAN["make gh-repo / gh-secrets<br/>(manual, 1x)"] -- "0 · repo + secrets" --> GA["GitHub Actions<br/>ci.yml · cd.yml"]
    GA -- "1 · job infra" --> TF["Terraform (state no Volume)<br/>environments qa/prod · URLs das apps · proteção das branches"]
    GA -- "2 · bundle deploy / run" --> DAB["Asset Bundle<br/>Job de 3 tasks"]
    DAB -- "3 · treino" --> ML["MLflow + Unity Catalog<br/>versões e @champion"]
    ML -- "4 · tabela gold" --> ST["Streamlit Cloud<br/>2 apps: develop e main<br/>(configurado pela UI)"]
```

## Decisões

1. **Código dentro dos notebooks:** é o que se mostra em aula. Além disso, neste workspace o
   Job falha ao importar `.py` de arquivos do workspace (erro de leitura do storage).
2. **Limpeza: automático detecta, pessoa decide:** uma lista curta de seções que não são notícia +
   filtro automático de títulos de template; editoria nova ou mudança de 5 p.p. vira alerta em
   `data_monitoring`, e quem muda a regra é uma pessoa.
3. **Cliques sintéticos:** não existe clickstream público; só a etapa `01_dados` mudaria em produção.
4. **Inferência batch:** o top-10 fica pronto numa tabela; o app só faz `SELECT`.
5. **Alias `@champion`:** app e inferência nunca usam "a última versão"; rollback = mover o alias.
6. **Ingestão no GitHub Actions:** o Databricks Free Edition não acessa a internet.
7. **dev / QA / PROD por schema:** o mesmo código, o `TARGET` escolhe o ambiente; QA roda o Job
   inteiro antes de PROD (teste de ponta a ponta).
8. **Bootstrap manual, resto pela esteira:** repositório e secrets são criados uma vez pelo
   `make` (a esteira não cria as próprias credenciais); o Terraform roda no job `infra` do `cd.yml`
   com o state num Volume do Databricks, sem tokens no state.
9. **Terraform só para o GitHub:** na Free Edition o workspace já vem pronto; o Job é do Asset Bundle.
