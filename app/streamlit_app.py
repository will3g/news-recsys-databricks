"""App Streamlit: mostra as recomendações que o Job do Databricks gravou na tabela gold.

Com secrets do Databricks (Streamlit Cloud ou app/.streamlit/secrets.toml) lê o Lakehouse;
sem secrets, lê a amostra em app/sample_data/.
"""

from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer

st.set_page_config(page_title="Recomendação de notícias", page_icon="📰", layout="wide")
AMOSTRA = Path(__file__).parent / "sample_data"


def texto(titulo: str) -> str:
    return titulo.replace("$", r"\$")  # "R$ 10" não pode virar fórmula no Markdown


def cards(materias: pd.DataFrame) -> None:
    for linha in range(0, len(materias), 3):
        for coluna, m in zip(st.columns(3), materias.iloc[linha : linha + 3].itertuples()):
            with coluna, st.container(border=True):
                if m.image_url:
                    st.image(m.image_url, width="stretch")
                st.markdown(f"**[{texto(m.title)}]({m.url})**")
                st.caption(m.section)


@st.cache_data(ttl=600)
def carregar(consulta: str, arquivo: str) -> pd.DataFrame:
    """Roda a consulta no SQL warehouse; sem secrets (ou com erro), lê o parquet de amostra."""
    try:
        from databricks import sql

        cfg = st.secrets["databricks"]
        with sql.connect(
            server_hostname=cfg["server_hostname"],
            http_path=cfg["http_path"],
            access_token=cfg["access_token"],
        ) as conn:
            return pd.read_sql(consulta.format(schema=cfg["schema"]), conn)
    except Exception:
        return pd.read_parquet(AMOSTRA / f"{arquivo}.parquet")


S = "workspace.{schema}"
usuarios = carregar(f"SELECT * FROM {S}.silver_users", "silver_users")
recs = carregar(f"SELECT * FROM {S}.gold_recommendations", "gold_recommendations")
historico = carregar(
    f"SELECT c.*, a.title, a.section FROM {S}.silver_clicks c JOIN {S}.bronze_articles a USING (url)",
    "historico",
)
metricas = carregar(f"SELECT * FROM {S}.model_metrics", "model_metrics")
materias = carregar(
    f"SELECT url, title, section, image_url, published_at FROM {S}.bronze_articles", "bronze_articles"
)

st.title("📰 Recomendação de notícias")
st.caption("Matérias reais do O Globo · leitores e cliques sintéticos · modelo treinado no Databricks")

aba_recs, aba_perfil, aba_modelo = st.tabs(["Recomendações", "Monte seu perfil", "Modelo"])

with aba_recs:
    rotulos = {u.user_id: f"{u.user_id} · {u.persona}" for u in usuarios.itertuples()}
    usuario = st.selectbox("Leitor", sorted(set(recs["user_id"])), format_func=rotulos.get)
    esquerda, direita = st.columns([1, 2], gap="large")

    with esquerda:
        st.subheader("Leu")
        lidas = historico[historico["user_id"] == usuario].sort_values("event_ts", ascending=False)
        st.bar_chart(lidas["section"].value_counts(), horizontal=True, height=200)
        for m in lidas.head(8).itertuples():
            st.markdown(f"- [{texto(m.title)}]({m.url}) · `{m.section}`")

    with direita:
        st.subheader("Recomendado")
        top = recs[recs["user_id"] == usuario].sort_values("rank")
        st.caption(f"modelo @champion versão {top['model_version'].iloc[0]}")
        cards(top)

with aba_perfil:
    st.caption("Leitor novo (sem cliques): recomendação calculada na hora pelo conteúdo + recência, "
               "como a parte de conteúdo do modelo híbrido.")
    materias = materias.sort_values("published_at", ascending=False).reset_index(drop=True)
    lidas = st.multiselect("Matérias que você leu", materias.index, format_func=materias["title"].get)
    if lidas:
        T = TfidfVectorizer().fit_transform(materias["title"] + " " + materias["section"])
        publicada = pd.to_datetime(materias["published_at"], utc=True, format="mixed")
        idade_h = (publicada.max() - publicada).dt.total_seconds().to_numpy() / 3600
        score = (T @ T[lidas].mean(axis=0).T).A1 * 0.5 ** (idade_h / 24)  # parecida × recente
        score[lidas] = 0  # não recomenda o que já leu
        cards(materias.iloc[score.argsort()[::-1][:9]])

with aba_modelo:
    st.subheader("Treinos registrados (tabela model_metrics)")
    st.dataframe(metricas.sort_values("avaliado_em", ascending=False), hide_index=True)
    st.caption("O vencedor só vira @champion se o NDCG@10 dele superar o do campeão atual.")
