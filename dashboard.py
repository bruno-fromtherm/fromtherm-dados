import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import plotly.express as px

# 1. CONFIGURAÇÃO E CSS (Remoção do "0" e Estilo Fromtherm)
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

st.markdown("""
    <style>
    /* Remover elementos estranhos do topo */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stAppViewContainer"] > div:first-child span { display: none !important; }

    .stApp { background-color: #f8f9fa; }
    .main-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-card {
        background: #ffffff;
        border-left: 5px solid #003366;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-title { color: #666; font-size: 0.8rem; font-weight: bold; margin-bottom: 5px; }
    .metric-value { color: #003366; font-size: 1.2rem; font-weight: 800; }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# 2. FUNÇÕES DE DADOS E ARQUIVOS
def formatar_nome_arquivo(info, extensao):
    data_f = info['data'].strftime("%d-%m-%Y") if info['data'] else "00-00-00"
    hora_f = (info['hora'] or "00-00").replace(":", "-")
    return f"Maquina_{info['modelo']}_OP{info['operacao']}_{data_f}_{hora_f}hs.{extensao}"

@st.cache_data(ttl=10)
def listar_arquivos():
    if not os.path.exists(DADOS_DIR): return []
    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    lista = []
    for f in arquivos:
        n = os.path.basename(f)
        p = n.replace(".csv", "").split("_")
        if len(p) >= 6:
            dt = datetime.strptime(p[2], "%Y%m%d").date()
            lista.append({
                "nome": n, "caminho": f, "linha": p[1], "data": dt,
                "ano": dt.year, "mes": dt.month, "hora": f"{p[3][:2]}:{p[3][2:]}",
                "operacao": p[4], "modelo": p[5]
            })
    return lista

def carregar_dados(caminho):
    df = pd.read_csv(caminho, sep=";", engine="python") if ";" in open(caminho).read() else pd.read_csv(caminho)
    df.columns = ["Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]
    return df

# 3. INTERFACE PRINCIPAL
info_arquivos = listar_arquivos()
if not info_arquivos:
    st.error("Dados não encontrados.")
    st.stop()

# Sidebar com Logo e Filtros
st.sidebar.image("https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png")
st.sidebar.header("🔍 Filtros de Busca")
f_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + sorted(list({a['modelo'] for a in info_arquivos})))
f_ano = st.sidebar.selectbox("Ano", ["Todos"] + sorted(list({str(a['ano']) for a in info_arquivos})))
f_op = st.sidebar.text_input("Operação (OP)")

# Filtragem Dinâmica
filtrados = [a for a in info_arquivos if 
             (f_modelo == "Todos" or a['modelo'] == f_modelo) and 
             (f_ano == "Todos" or str(a['ano']) == f_ano) and 
             (f_op.upper() in a['operacao'].upper())]

# 4. DASHBOARD DE ÚLTIMA LEITURA (Topo)
recente = max(info_arquivos, key=lambda x: (x['data'], x['hora']))
df_u = carregar_dados(recente['caminho']).iloc[-1]

st.markdown(f"### 🚀 Painel de Performance - {recente['modelo']} (OP: {recente['operacao']})")
st.caption(f"Última atualização: {recente['data'].strftime('%d/%m/%Y')} às {recente['hora']}")

c1, c2, c3, c4, c5, c6 = st.columns(6)
metrics = [
    ("Ambiente", df_u['Ambiente'], "°C"), ("Entrada", df_u['Entrada'], "°C"), ("Saída", df_u['Saída'], "°C"),
    ("DIF (ΔT)", df_u['ΔT'], "°C"), ("Tensão", df_u['Tensão'], "V"), ("Corrente", df_u['Corrente'], "A")
]
for i, (l, v, u) in enumerate(metrics):
    with [c1, c2, c3, c4, c5, c6][i]:
        st.markdown(f"<div class='metric-card'><div class='metric-title'>{l}</div><div class='metric-value'>{v}{u}</div></div>", unsafe_allow_html=True)

c7, c8, c9, c10, c11 = st.columns(5)
metrics2 = [
    ("kcal/h", df_u['kcal/h'], ""), ("Vazão", df_u['Vazão'], "L/h"), ("kW Aquec.", df_u['kW Aquecimento'], "kW"),
    ("kW Consu.", df_u['kW Consumo'], "kW"), ("COP", df_u['COP'], "")
]
for i, (l, v, u) in enumerate(metrics2):
    with [c7, c8, c9, c10, c11][i]:
        st.markdown(f"<div class='metric-card'><div class='metric-title'>{l}</div><div class='metric-value'>{v}{u}</div></div>", unsafe_allow_html=True)

st.divider()

# 5. ABAS
tab1, tab2 = st.tabs(["📄 Históricos Disponíveis", "📊 Crie Seu Gráfico"])

with tab1:
    for arq in filtrados[:10]: # Limitar visíveis por performance
        with st.expander(f"➔ {arq['modelo']} | OP: {arq['operacao']} | Data: {arq['data'].strftime('%d/%m/%Y')} - {arq['hora']}"):
            df_hist = carregar_dados(arq['caminho'])
            st.dataframe(df_hist, use_container_width=True)

            # Botões de Download com nome dinâmico
            col_d1, col_d2 = st.columns(2)
            nome_ex = formatar_nome_arquivo(arq, "xlsx")
            nome_pdf = formatar_nome_arquivo(arq, "pdf")

            output = BytesIO()
            df_hist.to_excel(output, index=False)
            col_d1.download_button("📥 Baixar Excel", output.getvalue(), nome_ex)
            col_d2.button("📥 Gerar PDF (Visualizar)", key=arq['nome'])

with tab2:
    st.subheader("Gráfico Customizado")
    col_g1, col_g2 = st.columns(2)
    sel_mod = col_g1.selectbox("Selecione o Modelo", sorted(list({a['modelo'] for a in info_arquivos})), key="mod_g")
    op_list = [a['operacao'] for a in info_arquivos if a['modelo'] == sel_mod]
    sel_op = col_g2.selectbox("Selecione a Operação", op_list, key="op_g")

    escolhido = next(a for a in info_arquivos if a['modelo'] == sel_mod and a['operacao'] == sel_op)
    df_g = carregar_dados(escolhido['caminho'])

    # Escalas Fixas (conforme solicitado)
    escalas = {
        "Ambiente": 50, "Entrada": 100, "Saída": 100, "ΔT": 10, "Tensão": 400,
        "Corrente": 100, "kcal/h": 60000, "Vazão": 20000, "kW Aquecimento": 100,
        "kW Consumo": 50, "COP": 20
    }

    vars_g = st.multiselect("Escolha as variáveis para o gráfico:", list(escalas.keys()), default=["Entrada", "Saída"])

    if vars_g:
        fig = px.line(df_g, x="Time", y=vars_g, title=f"Teste {sel_mod} - OP {sel_op}")
        fig.update_layout(hovermode="x unified", legend_orientation="h", yaxis_range=[0, max([escalas[v] for v in vars_g])])
        st.plotly_chart(fig, use_container_width=True)
        st.info("Para compartilhar: Use o ícone de câmera no topo do gráfico para baixar e enviar no WhatsApp.")