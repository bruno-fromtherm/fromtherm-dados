import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from io import BytesIO
import plotly.express as px

# -------- CONFIG BÁSICA --------
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# -------- AJUSTE VISUAL MÍNIMO (SEM MEXER MUITO) --------
st.markdown(
    """
    <style>
    /* por enquanto, não vamos brigar com o "0" */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        border-left: 4px solid #0d6efd;
    }
    .ft-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #6c757d;
        margin-bottom: 2px;
    }
    .ft-card-value {
        font-size: 20px;
        font-weight: 700;
        color: #343a40;
    }
    .ft-card-value.red {
        color: #dc3545;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------- FUNÇÕES AUXILIARES SIMPLES --------

def listar_arquivos_csv(pasta_base="./dados_brutos"):
    """
    Lista todos os CSVs na pasta base (e subpastas) e devolve
    uma lista de dicionários com:
      - caminho
      - nome_arquivo
      - data_modificacao (datetime)
    Não tenta interpretar nome, OP, modelo etc. ainda.
    """
    padrao = os.path.join(pasta_base, "**", "*.csv")
    caminhos = glob.glob(padrao, recursive=True)

    arquivos_info = []
    for caminho in caminhos:
        try:
            stat = os.stat(caminho)
            dt_mod = datetime.fromtimestamp(stat.st_mtime)
        except Exception:
            dt_mod = None

        arquivos_info.append(
            {
                "caminho": caminho,
                "nome_arquivo": os.path.basename(caminho),
                "data_modificacao": dt_mod,
            }
        )

    # ordena do mais recente para o mais antigo
    arquivos_info.sort(
        key=lambda x: x["data_modificacao"] if x["data_modificacao"] else datetime.min,
        reverse=True,
    )
    return arquivos_info


def carregar_csv_simples(caminho):
    """
    Lê o CSV de forma simples, tentando adivinhar o separador.
    NÃO renomeia colunas aqui, só retorna o DataFrame.
    """
    try:
        df = pd.read_csv(caminho, sep=";")
    except Exception:
        df = pd.read_csv(caminho)
    return df


def pegar_ultima_linha(df):
    if df is None or df.empty:
        return None
    return df.iloc[-1]


# -------- CARGA DE ARQUIVOS --------

pasta_dados = "./dados_brutos"
arquivos = listar_arquivos_csv(pasta_dados)

# guarda para reutilizar em outras partes
st.session_state["arquivos_csv"] = arquivos

# -------- TÍTULO --------
st.title("Máquina de Teste Fromtherm")

# -------- CARDS – ÚLTIMA LEITURA --------
ultima_linha = None
info_ultimo_arquivo = None

if arquivos:
    info_ultimo_arquivo = arquivos[0]  # mais recente
    df_ultimo = carregar_csv_simples(info_ultimo_arquivo["caminho"])
    ultima_linha = pegar_ultima_linha(df_ultimo)

col1, col2, col3 = st.columns(3)

def mostra_valor(df_row, coluna):
    if df_row is None:
        return "N/D"
    if coluna not in df_row.index:
        return "N/D"
    val = df_row[coluna]
    try:
        if pd.isna(val):
            return "N/D"
    except Exception:
        pass
    return f"{val}"

with col1:
    st.markdown("#### Última Leitura")
    st.markdown(
        f"""
        <div class="ft-card">
          <div>
            <div class="ft-card-title">T-Ambiente</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "Ambiente")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">kcal/h</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "kcal/h")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">kW Consumo</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "kW Consumo")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown("####")
    st.markdown(
        f"""
        <div class="ft-card">
          <div>
            <div class="ft-card-title">T-Entrada</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "Entrada")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">Tensão</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "Tensão")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">Vazão</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "Vazão")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">COP</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "COP")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown("####")
    st.markdown(
        f"""
        <div class="ft-card">
          <div>
            <div class="ft-card-title">T-Saída</div>
            <div class="ft-card-value red">{mostra_valor(ultima_linha, "Saída")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">Corrente</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "Corrente")}</div>
          </div>
        </div>
        <div class="ft-card">
          <div>
            <div class="ft-card-title">kW Aquecimento</div>
            <div class="ft-card-value">{mostra_valor(ultima_linha, "kW Aquecimento")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if info_ultimo_arquivo:
    st.caption(f"Último arquivo lido: {info_ultimo_arquivo['nome_arquivo']}")

st.markdown("---")

# -------- HISTÓRICOS DISPONÍVEIS (APENAS LISTA SIMPLES) --------

st.subheader("Históricos Disponíveis")

if not arquivos:
    st.info("Nenhum arquivo CSV encontrado na pasta de dados.")
else:
    for arq in arquivos:
        with st.expander(arq["nome_arquivo"], expanded=False):
            st.write(f"Caminho: {arq['caminho']}")
            st.write(f"Data modificação: {arq['data_modificacao']}")