"""App Streamlit — recomendações personalizadas de notícias (aula FIAP Fase 5 MLOps).

As recomendações são PRÉ-CALCULADAS por um Job no Databricks (inferência batch com o modelo
``@champion`` do Unity Catalog). O app só lê a tabela gold — padrão comum em recsys.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from data_access import DataSource, get_source

st.set_page_config(page_title="Recomendação de notícias", page_icon="📰", layout="wide")


def _secrets() -> dict[str, Any] | None:
    try:
        return dict(st.secrets.get("databricks", {}))
    except Exception:  # noqa: BLE001 — sem secrets.toml
        return None


@st.cache_resource(show_spinner="Conectando ao Lakehouse...")
def source() -> tuple[DataSource, str | None]:
    return get_source(_secrets())


@st.cache_data(ttl=600, show_spinner=False)
def load(kind: str, user_id: str = "") -> pd.DataFrame:
    src, _ = source()
    if kind == "users":
        return src.users()
    if kind == "history":
        return src.history(user_id)
    if kind == "recs":
        return src.recommendations(user_id)
    return src.model_metrics()


def article_card(row: pd.Series, caption: str) -> None:
    with st.container(border=True):
        if isinstance(row.get("image_url"), str) and row["image_url"]:
            st.image(row["image_url"], width="stretch")
        st.markdown(f"**[{row['title']}]({row['url']})**")
        st.caption(caption)


src, warning = source()
st.title("📰 Recomendação de notícias")
st.caption(
    f"Fonte: **{src.name}** · matérias reais do sitemap do O Globo · "
    "usuários e cliques **sintéticos**"
)
if warning:
    st.info(warning)

tab_recs, tab_model = st.tabs(["Recomendações", "Modelo"])

with tab_recs:
    users = load("users")
    if users.empty:
        st.warning("Nenhum usuário com recomendações ainda — rode o Job no Databricks.")
        st.stop()
    labels = {r.user_id: f"{r.user_id} · persona {r.persona}" for r in users.itertuples()}
    user_id = st.selectbox("Usuário", list(labels), format_func=labels.get)

    history, recs = load("history", user_id), load("recs", user_id)
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.subheader("Leu recentemente")
        if not history.empty:
            mix = history["section"].value_counts(normalize=True).rename("leituras")
            st.bar_chart(mix, horizontal=True, height=180)
        for _, row in history.iterrows():
            st.markdown(f"- [{row['title']}]({row['url']}) · `{row['section']}`")
    with right:
        st.subheader("Recomendado para você")
        if recs.empty:
            st.write("Sem recomendações para este usuário.")
        else:
            version = recs["model_version"].iloc[0]
            st.caption(
                f"modelo `@champion` versão **{version}** · "
                f"gerado em {recs['generated_at'].iloc[0]}"
            )
            rows = [recs.iloc[i : i + 3] for i in range(0, len(recs), 3)]  # 3 cards por linha
            for chunk in rows:
                for col, (_, row) in zip(st.columns(3), chunk.iterrows(), strict=False):
                    with col:
                        caption = f"#{row['rank']} · {row['section']} · score {row['score']:.3f}"
                        article_card(row, caption)

with tab_model:
    st.subheader("Comparação dos candidatos (avaliação offline)")
    metrics = load("metrics")
    if metrics.empty:
        st.write("Sem métricas registradas.")
    else:
        latest = metrics[metrics["evaluated_at"] == metrics["evaluated_at"].max()]
        table = latest.pivot_table(
            index="candidate", columns="metric", values="value", aggfunc="last"
        )
        keep = [
            c
            for c in [
                "ndcg_at_k",
                "precision_at_k",
                "recall_at_k",
                "hit_rate_at_k",
                "catalog_coverage",
                "cold_hit_rate_at_k",
            ]
            if c in table
        ]
        st.dataframe(table[keep].sort_values("ndcg_at_k", ascending=False).style.format("{:.4f}"))
        st.caption(
            "O vencedor só vira `@champion` se superar o campeão atual em NDCG@10 (quality gate)."
        )
        trend = metrics[(metrics["metric"] == "ndcg_at_k") & (metrics["promoted"])]
        if trend["evaluated_at"].nunique() > 1:
            st.subheader("NDCG@10 do campeão ao longo do tempo")
            st.line_chart(trend.set_index("evaluated_at")["value"])
