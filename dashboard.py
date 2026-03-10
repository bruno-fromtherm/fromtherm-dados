import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from io import StringIO
import re

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# --- CSS para fundo branco e visual limpo ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    .main > div {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    h1 { color: #003366 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Pasta de dados ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# --- 1. Função para listar e extrair info dos nomes dos arquivos ---
@st.cache_data(ttl=10)
def listar_arquivos_csv():
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        # Regex ajustada para capturar: DATA, HORA, OP e MODELO
        # Exemplo: historico_L1_20240308_0939_OP987_FTA987BR.csv
        match = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([A-Z0-9]+)", nome)

        if match:
            ano_str, mes_str, dia_str, hora_str, op, modelo = match.groups()
            info_arquivos.append({
                "nome_arquivo": nome,
                "caminho": caminho,
                "ano": int(ano_str),
                "data_completa": f"{dia_str}/{mes_str}/{ano_str}",
                "op": op,
                "modelo": modelo
            })
    return info_arquivos

# --- 2. Função para ler o CSV "bagunçado" e organizar ---
@st.cache_data
def carregar_dados_limpos(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        linhas_processadas = []
        for linha in linhas:
            l = linha.strip()
            # Remove as barras '|' e limpa espaços
            if l.startswith('|'):
                partes = [p.strip() for p in l.split('|') if p.strip()]
                # Pula linhas que são apenas divisórias como |---|---|
                if all(c == '-' for c in partes[0]): continue
                linhas_processadas.append(",".join(partes))
        
        # Converte para DataFrame
        csv_limpo = "\n".join(linhas_processadas)
        df = pd.read_csv(StringIO(csv_limpo))
        return df
    except Exception as e:
        return pd.DataFrame()

# --- INTERFACE ---
st.sidebar.image("https://fromtherm.com.br", use_column_width=True)
st.title("Máquina de Teste Fromtherm")

arquivos = listar_arquivos_csv()

if not arquivos:
    st.error(f"Nenhum arquivo encontrado em: {DADOS_DIR}")
else:
    df_lista = pd.DataFrame(arquivos)

    # --- FILTROS EM CASCATA ---
    st.sidebar.header("Filtros de Produção")
    
    # 1. Filtro de Modelo
    lista_modelos = sorted(df_lista['modelo'].unique())
    mod_sel = st.sidebar.selectbox("Selecione o Modelo", ["-"] + lista_modelos)

    if mod_sel != "-":
        # 2. Filtro de Ano (apenas do modelo selecionado)
        df_filtro_ano = df_lista[df_lista['modelo'] == mod_sel]
        lista_anos = sorted(df_filtro_ano['ano'].unique(), reverse=True)
        ano_sel = st.sidebar.selectbox("Selecione o Ano", ["-"] + lista_anos)

        if ano_sel != "-":
            # 3. Filtro de OP (apenas do modelo e ano selecionados)
            df_filtro_op = df_filtro_ano[df_filtro_ano['ano'] == ano_sel]
            lista_ops = sorted(df_filtro_op['op'].unique())
            op_sel = st.sidebar.selectbox("Selecione a OP", lista_ops)

            # Botão para carregar
            if st.sidebar.button("Visualizar Dados"):
                caminho_final = df_filtro_op[df_filtro_op['op'] == op_sel]['caminho'].values[0]
                
                st.subheader(f"📊 Dados da {op_sel} - Modelo {mod_sel}")
                df_final = carregar_dados_limpos(caminho_final)
                
                if not df_final.empty:
                    # Exibição estilo Excel
                    st.dataframe(df_final, use_container_width=True, hide_index=True)
                    
                    # Botão de Download
                    csv = df_final.to_csv(index=False).encode('utf-8')
                    st.download_button("Baixar Planilha Excel (CSV)", csv, f"{op_sel}.csv", "text/csv")
                else:
                    st.error("Erro ao formatar os dados deste arquivo.")
        else:
            st.info("Aguardando seleção do Ano...")
    else:
        st.info("Selecione um **Modelo de Máquina** na barra lateral para começar.")

# Rodapé informando arquivos disponíveis no sistema
with st.expander("Ver todos os arquivos brutos no sistema"):
    st.write(df_lista[['modelo', 'ano', 'op', 'nome_arquivo']])
