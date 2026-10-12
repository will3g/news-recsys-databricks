# Arquitetura em Mermaid

Diagramas para conduzir a aula explicando o fluxo. O GitHub e o VS Code (extensão
*Markdown Preview Mermaid Support*) renderizam direto; para editar visualmente, cole no
<https://mermaid.live> (Actions → *Export* → PNG/SVG) ou importe no draw.io
(*Arrange → Insert → Advanced → Mermaid*).

Ordem sugerida na aula: **1 → 2 → 3 → 4**.

---

## 1. Visão geral (o sistema inteiro)

```mermaid
flowchart TB
    SM[("Sitemap O Globo")]

    subgraph GH["GitHub Actions"]
        direction LR
        CI["ci.yml<br/>testes no PR"]
        CD["cd.yml<br/>deploy prod"]
        ING["ingest.yml<br/>cron 06:00"]
    end

    subgraph DBX["Databricks Free Edition"]
        VOL[("Volume raw")]
        subgraph JOB["Job: 6 tasks (Asset Bundle)"]
            direction TB
            T1["01 bronze<br/>MERGE matérias"]
            T2["02 silver<br/>cliques sintéticos"]
            T3["03 treino<br/>5 modelos"]
            T4{"04 gate<br/>melhor que<br/>@champion?"}
            T5["05 inferência<br/>batch top-10"]
            T6["06 monitoramento<br/>cobertura · PSI"]
        end
        MLF[("MLflow<br/>runs")]
        UC[("Unity Catalog<br/>versões +<br/>@champion")]
        GOLD[("tabela gold<br/>recomendações")]
    end

    APP["App Streamlit<br/>Community Cloud"]

    %% Passo 0: acontece a cada merge na main, não todo dia
    CI -. "0a · CI verde libera o merge" .-> CD
    CD -. "0b · publica Job + código" .-> JOB

    %% Passos 1 a 15: o ciclo diário
    SM -- "1 · baixa o sitemap" --> ING
    ING -- "2 · envia o JSON" --> VOL
    ING -. "3 · dispara o Job" .-> T1
    VOL -- "4 · lê os JSONs" --> T1
    T1 -- "5" --> T2
    T2 -- "6" --> T3
    T3 -- "7 · loga as runs" --> MLF
    T3 -- "8 · registra versão N" --> UC
    T3 -- "9" --> T4
    T4 -- "10 · promove se for melhor" --> UC
    T4 -- "11" --> T5
    UC -- "12 · carrega @champion" --> T5
    T5 -- "13 · grava top-10" --> GOLD
    T5 -- "14" --> T6
    GOLD -- "15 · SELECT via SQL warehouse" --> APP

    classDef github fill:#24292f,stroke:#24292f,color:#ffffff
    classDef dbx fill:#ffe9e0,stroke:#ff3621,color:#1b1b1b
    classDef store fill:#fff7ed,stroke:#c2410c,color:#1b1b1b
    classDef app fill:#ffe4e6,stroke:#e11d48,color:#1b1b1b
    classDef gate fill:#fde68a,stroke:#b45309,color:#1b1b1b
    class ING,CI,CD github
    class T1,T2,T3,T5,T6 dbx
    class T4 gate
    class VOL,MLF,UC,GOLD,SM store
    class APP app
```

**Passo a passo (siga os números das setas):**

| # | Quem | O que acontece |
|---|---|---|
| 0a · 0b | GitHub Actions | *(só quando há merge na main)* CI verde → `cd.yml` publica Job e código no Databricks |
| 1 | `ingest.yml` | às 06:00 baixa o sitemap do O Globo (a Free Edition não tem internet de saída) |
| 2 | `ingest.yml` | envia o JSON para o Volume `raw/catalog/` |
| 3 | `ingest.yml` | dispara o Job (`bundle run`) |
| 4 | task 01 | lê os JSONs e faz `MERGE` na `bronze_articles` |
| 5 | task 02 | gera usuários e cliques **sintéticos** (silver) |
| 6 | task 03 | treina 8 candidatos (5 famílias de modelo) |
| 7 | task 03 | cada candidato vira uma run no MLflow |
| 8 | task 03 | o vencedor é registrado como **versão N** no Unity Catalog |
| 9–10 | task 04 | gate: se N supera o `@champion`, o alias passa para N |
| 11–12 | task 05 | carrega o `@champion` (novo ou o antigo) |
| 13 | task 05 | grava o top-10 de cada usuário na tabela gold |
| 14 | task 06 | mede cobertura e PSI (monitoramento) |
| 15 | app | o Streamlit faz um `SELECT` na gold via SQL warehouse |

**Como contar em uma frase:** o GitHub busca o dado e dispara o Job (1–3); o Job transforma e
treina (4–8), o gate decide (9–10), a inferência batch grava a gold (11–13) e o app só faz um
`SELECT` (15).

---

## 2. Treino e promoção (o coração do MLOps)

```mermaid
flowchart TB
    D[("silver_interactions<br/>+ catálogo")] -- "1" --> S["Split temporal<br/>80% treino · 20% teste"]

    S -- "2" --> P["Popularidade<br/>(baseline)"]
    S -- "2" --> CF["Item-item CF"]
    S -- "2" --> SVD["SVD"]
    S -- "2" --> CT["Conteúdo<br/>TF-IDF título + editoria"]
    S -- "2" --> HY["Híbrido<br/>α·CF + (1−α)·conteúdo"]

    P & CF & SVD & CT & HY -- "3" --> M["Métricas @10<br/>NDCG · HitRate · cobertura · acerto em matérias frias"]
    M -- "4" --> R["MLflow: 1 run por candidato"]
    R -- "5" --> W["Vencedor (maior NDCG)<br/>re-treina com 100% dos dados"]
    W -- "6" --> V["Unity Catalog: versão N"]
    V -- "7" --> G{"NDCG(N) ><br/>NDCG(@champion)?"}
    G -- "8 · sim" --> C["alias @champion → N<br/>tag gate_decision = promoted"]
    G -- "8 · não" --> K["mantém campeão<br/>tag gate_decision = rejected"]
    C -- "9" --> B["Inferência batch usa @champion"]
    K -- "9" --> B

    classDef gate fill:#fde68a,stroke:#b45309,color:#1b1b1b
    classDef win fill:#dcfce7,stroke:#15803d,color:#1b1b1b
    classDef lose fill:#f1f5f9,stroke:#64748b,color:#1b1b1b
    class G gate
    class C win
    class K lose
```

**Passo a passo:** 1 separa treino/teste pelo tempo · 2 treina os candidatos em paralelo ·
3 mede todos no mesmo teste · 4 registra no MLflow · 5 escolhe pelo NDCG e re-treina com tudo ·
6 registra a versão N · 7–8 quality gate · 9 a inferência sempre usa o `@champion`.

**Números locais (07/10/2026):** híbrido α=0,4 venceu com NDCG@10 = 0,212 (popularidade:
0,035). CF e SVD acertam **0%** das matérias sem clique; o híbrido acerta 20%.

---

## 3. Um dia na vida do pipeline

```mermaid
sequenceDiagram
    autonumber
    participant GA as GitHub Actions
    participant V as Volume (raw)
    participant J as Job Databricks
    participant M as MLflow / Unity Catalog
    participant G as Tabela gold
    participant A as App Streamlit

    Note over GA: 06:00 (cron)
    GA->>GA: baixa o sitemap → JSON
    GA->>V: databricks fs cp
    GA->>J: bundle run recsys_pipeline
    J->>J: 01 bronze (MERGE) · 02 eventos sintéticos
    J->>M: 03 treina 8 candidatos, registra versão N
    J->>M: 04 compara N × @champion
    alt N é melhor
        M-->>M: @champion → N
    else N empata ou piora
        M-->>M: mantém @champion
    end
    J->>M: 05 carrega @champion
    J->>G: grava top-10 por usuário (+ model_version)
    J->>J: 06 monitoramento (cobertura, PSI)
    A->>G: SELECT ... WHERE user_id = ?
    G-->>A: recomendações + versão do modelo
```

---

## 4. Quem gerencia o quê

```mermaid
flowchart TB
    subgraph TF["Terraform (infra/github)"]
        direction LR
        R1["Repositório"] ~~~ R2["Secrets"] ~~~ R3["Environment prod"] ~~~ R4["Proteção da main"]
    end
    GA["GitHub Actions"]
    subgraph DAB["Asset Bundle (databricks.yml)"]
        direction LR
        B1["Job de 6 tasks"] ~~~ B2["Notebooks + src/"] ~~~ B3["Targets dev / prod"]
    end
    subgraph ML["MLflow + Unity Catalog"]
        direction LR
        M1["Runs e métricas"] ~~~ M2["Versões"] ~~~ M3["@champion"]
    end
    subgraph ST["Streamlit Cloud (configurado pela UI)"]
        direction LR
        S1["App público"] ~~~ S2["Secrets do warehouse"]
    end

    TF -- "1 · cria repo e secrets usados por" --> GA
    GA -- "2 · bundle deploy / run" --> DAB
    DAB -- "3 · o treino gera" --> ML
    ML -- "4 · @champion → tabela gold → lida por" --> ST

    classDef tf fill:#ede9fe,stroke:#7c3aed,color:#1b1b1b
    classDef dab fill:#ffe9e0,stroke:#ff3621,color:#1b1b1b
    classDef ml fill:#e0f2fe,stroke:#0369a1,color:#1b1b1b
    classDef st fill:#ffe4e6,stroke:#e11d48,color:#1b1b1b
    classDef gh fill:#24292f,stroke:#24292f,color:#ffffff
    class R1,R2,R3,R4 tf
    class B1,B2,B3 dab
    class M1,M2,M3 ml
    class S1,S2 st
    class GA gh
```

**Por que o Terraform não cria o Databricks?** Na Free Edition não há API de conta: workspace,
catálogo e storage já vêm prontos. O IaC do projeto no Databricks é o Asset Bundle; o
Terraform cuida do que sobrou — o GitHub.
