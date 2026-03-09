import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from io import BytesIO
import plotly.express as px

# 1. ESTILO E CONFIGURAÇÃO
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #f4f7f6; }
    .main-header {
        color: #003366; font-size: 24px; font-weight: 800; text-align: center;
        padding: 10px; border-bottom: 4px solid #003366; margin-bottom: 20px;
    }
    .ft-card {
        background: white; border-radius: 10px; padding: 15px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; border-top: 5px solid #003366;
    }
    .ft-icon { font-size: 30px; margin-bottom: 5px; }
    .ft-label { font-size: 12px; font-weight: 700; color: #666; }
    .ft-value { font-size: 18px; font-weight: 800; color: #003366; }
    .azul { color: #007bff; }
    .vermelho { color: #dc3545; }
    .ouro { color: #ffc107; }
    .verde { color: #28a745; }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# 2. FUNÇÕES DE DADOS
def buscar_arquivos():
    if not os.path.exists(DADOS_DIR): return []
    caminhos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    lista = []
    for c in caminhos:
        n = os.path.basename(c)
        p = n.replace(".csv", "").split("_")
        if len(p) >= 6:
            try:
                dt = datetime.strptime(p[2], "%Y%m%d").date()
                lista.append({
                    "nome": n, "caminho": c, "data": dt,
                    "ano": str(dt.year), "mes": dt.strftime("%m"),
                    "data_f": dt.strftime("%d/%m/%Y"), "hora": f"{p[3][:2]}:{p[3][2:]}",
                    "operacao": p[4], "modelo": p[5]
                })
            except: continue
    return sorted(lista, key=lambda x: (x['data'], x['hora']), reverse=True)

def carregar_csv(caminho):
    try:
        df = pd.read_csv(caminho, sep=";", engine="python")
        if len(df.columns) < 5: df = pd.read_csv(caminho, sep=",")
        df.columns = ["Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]
        return df
    except: return pd.DataFrame()

# 3. SIDEBAR COM SEQUÊNCIA SOLICITADA
arquivos = buscar_arquivos()
with st.sidebar:
    st.image("https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png", use_container_width=True)
    f_modelo = st.selectbox("📦 Modelo", ["Todos"] + sorted(list({a['modelo'] for a in arquivos})))
    f_op = st.text_input("🔢 Operação (OP)")
    f_ano = st.selectbox("📅 Ano", ["Todos"] + sorted(list({a['ano'] for a in arquivos}), reverse=True))
    f_mes = st.selectbox("📆 Mês", ["Todos"] + sorted(list({a['mes'] for a in arquivos})))

# Filtro
filtrados = [a for a in arquivos if 
             (f_modelo == "Todos" or a['modelo'] == f_modelo) and
             (f_ano == "Todos" or a['ano'] == f_ano) and
             (f_mes == "Todos" or a['mes'] == f_mes) and
             (f_op.upper() in a['operacao'].upper())]

# 4. PAINEL PRINCIPAL
st.markdown("<div class='main-header'>MAQUINAS DE TESTE FROMTHERM</div>", unsafe_allow_html=True)

if filtrados:
    atual = filtrados[0]
    dados = carregar_csv(atual['caminho'])
    if not dados.empty:
        v = dados.iloc[-1]
        st.markdown(f"<p style='text-align:center'>Lendo: {atual['modelo']} | OP: {atual['operacao']}</p>", unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        # Coluna 1
        c1.markdown(f"<div class='ft-card'><i class='bi bi-thermometer-half azul ft-icon'></i><div class='ft-label'>T-Ambiente</div><div class='ft-value'>{v['Ambiente']}°C</div></div>", unsafe_allow_html=True)
        c1.markdown(f"<div class='ft-card'><i class='bi bi-bolt ouro ft-icon'></i><div class='ft-label'>Tensão</div><div class='ft-value'>{v['Tensão']}V</div></div>", unsafe_allow_html=True)
        c1.markdown(f"<div class='ft-card'><i class='bi bi-sun vermelho ft-icon'></i><div class='ft-label'>kW Aquec.</div><div class='ft-value'>{v['kW Aquecimento']}kW</div></div>", unsafe_allow_html=True)
        # Coluna 2
        c2.markdown(f"<div class='ft-card'><i class='bi bi-arrow-down-circle azul ft-icon'></i><div class='ft-label'>T-Entrada</div><div class='ft-value'>{v['Entrada']}°C</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='ft-card'><i class='bi bi-activity azul ft-icon'></i><div class='ft-label'>Corrente</div><div class='ft-value'>{v['Corrente']}A</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='ft-card'><i class='bi bi-plug-fill ouro ft-icon'></i><div class='ft-label'>kW Consumo</div><div class='ft-value'>{v['kW Consumo']}kW</div></div>", unsafe_allow_html=True)
        # Coluna 3
        c3.markdown(f"<div class='ft-card'><i class='bi bi-arrow-up-circle vermelho ft-icon'></i><div class='ft-label'>T-Saída</div><div class='ft-value'>{v['Saída']}°C</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='ft-card'><i class='bi bi-fire vermelho ft-icon'></i><div class='ft-label'>kcal/h</div><div class='ft-value'>{v['kcal/h']}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='ft-card'><i class='bi bi-speedometer2 verde ft-icon'></i><div class='ft-label'>COP</div><div class='ft-value'>{v['COP']}</div></div>", unsafe_allow_html=True)
        # Coluna 4
        c4.markdown(f"<div class='ft-card'><i class='bi bi-triangle ouro ft-icon'></i><div class='ft-label'>DIF (ΔT)</div><div class='ft-value'>{v['ΔT']}°C</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='ft-card'><i class='bi bi-waves azul ft-icon'></i><div class='ft-label'>Vazão</div><div class='ft-value'>{v['Vazão']}L/h</div></div>", unsafe_allow_html=True)

# 5. ABAS
tab1, tab2 = st.tabs(["📄 Histórico", "📊 Gráfico"])
with tab1:
    for a in filtrados[:10]:
        with st.expander(f"{a['modelo']} - OP {a['operacao']} ({a['data_f']})"):
            df_ex = carregar_csv(a['caminho'])
            st.dataframe(df_ex, use_container_width=True)
with tab2:
    if filtrados:
        df_g = carregar_csv(filtrados[0]['caminho'])
        sel = st.multiselect("Dados:", ["Ambiente","Entrada","Saída","COP","kW Consumo"], default=["Entrada","Saída"])
        if sel:
            st.plotly_chart(px.line(df_g, x="Time", y=sel), use_container_width=True)