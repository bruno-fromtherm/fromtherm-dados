import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re
import plotly.express as px
from io import BytesIO

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(layout="wide", page_title="Fromtherm - Teste de Máquinas", page_icon="🔥")

# Injeção de CSS para Estilo e Cards
st.markdown("""
    <style>
    .main-header { color: #003366; font-size: 24px; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .ft-card {
        background: white; border-radius: 10px; padding: 15px; text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-top: 5px solid #003366; margin-bottom: 10px;
    }
    .ft-label { font-size: 11px; font-weight: 700; color: #666; text-transform: uppercase; }
    .ft-value { font-size: 18px; font-weight: 800; color: #003366; }
    </style>
""", unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=5)
def buscar_arquivos():
    if not os.path.exists(DADOS_DIR): return []
    caminhos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    infos = []
    for c in caminhos:
        n = os.path.basename(c)
        pts = n.replace(".csv", "").split("_")
        if len(pts) >= 4:
            try:
                # pts[2] = data (YYYYMMDD), pts[3] = hora (HHMM)
                data_str = pts[2]
                hora_str = pts[3]
                data_obj = datetime.strptime(data_str, "%Y%m%d").date()
                infos.append({
                    'caminho': c, 'nome': n, 'data': data_obj, 'ano': str(data_obj.year),
                    'mes': data_obj.strftime("%m"), 'dia': data_obj.strftime("%d/%m/%Y"),
                    'hora': f"{hora_str[:2]}:{hora_str[2:]}", 
                    'op': pts[4] if len(pts) > 4 else "N/D",
                    'modelo': pts[5] if len(pts) > 5 else "N/D"
                })
            except: continue
    return sorted(infos, key=lambda x: (x['data'], x['hora']), reverse=True)

def carregar_dados(caminho):
    try:
        df = pd.read_csv(caminho, sep='|', skiprows=[1], skipinitialspace=True, engine='python').iloc[:, 1:-1]
        df.columns = df.columns.str.strip().str.lower()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

# 3. INTERFACE PRINCIPAL
st.markdown("<div class='main-header'>FROMTHERM - Engenharia de Climatização</div>", unsafe_allow_html=True)
arquivos = buscar_arquivos()

with st.sidebar:
    st.header("🔍 Filtros")
    f_ano = st.multiselect("Ano", sorted(list(set(x['ano'] for x in arquivos))))
    f_mes = st.multiselect("Mês", sorted(list(set(x['mes'] for x in arquivos))))
    f_modelo = st.text_input("Modelo da Máquina").upper()
    
    filtrados = [x for x in arquivos if 
                 (not f_ano or x['ano'] in f_ano) and 
                 (not f_mes or x['mes'] in f_mes) and 
                 (f_modelo in x['modelo'].upper())]

    escolha = st.selectbox("Históricos Disponíveis", filtrados, 
                          format_func=lambda x: f"{x['modelo']} - OP: {x['op']} ({x['dia']})")

if escolha:
    df = carregar_dados(escolha['caminho'])
    if not df.empty:
        ultima = df.iloc[-1]
        nome_export = f"Maquina_{escolha['modelo']}_OP{escolha['op']}_{escolha['dia'].replace('/','-')}_{escolha['hora'].replace(':','h')}hs"

        tab1, tab2 = st.tabs(["📊 Dashboard", "📈 Crie Seu Gráfico"])

        with tab1:
            st.subheader(f"📍 Última Leitura: {escolha['modelo']} | OP: {escolha['op']}")
            cols = st.columns(4)
            metrias = [
                ("T-Ambiente", "ambiente"), ("T-Entrada", "entrada"), ("T-Saída", "saida"), ("DIF", "dif"),
                ("Tensão", "tensao"), ("Corrente", "corrente"), ("kcal/h", "kacl/h"), ("Vazão", "vazao"),
                ("kW Aquec.", "kw aquecimento"), ("kW Consumo", "kw consumo"), ("COP", "cop")
            ]
            for i, (label, col_df) in enumerate(metrias):
                val = ultima.get(col_df, 0)
                cols[i % 4].markdown(f"<div class='ft-card'><div class='ft-label'>{label}</div><div class='ft-value'>{val:.2f}</div></div>", unsafe_allow_html=True)
            
            st.divider()
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Baixar Excel (CSV)", data=df.to_csv().encode('utf-8'), file_name=f"{nome_export}.csv")

        with tab2:
            st.subheader("🎨 Construtor de Gráficos")
            vars_disponiveis = {col: col for col in df.columns}
            selecionados = st.multiselect("Escolha as variáveis:", list(vars_disponiveis.keys()), default=[df.columns[1], df.columns[2]])
            if selecionados:
                fig = px.line(df, y=selecionados, title=f"Análise: {escolha['modelo']}")
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aguardando seleção de arquivo nos filtros laterais.")
