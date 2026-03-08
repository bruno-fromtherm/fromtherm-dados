import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import plotly.express as px

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# =========================
#  CSS GLOBAL
# =========================
st.markdown(
    """
    <style>
    .stApp { background-color: #f4f6f9; }
    .main > div {
        background-color: #ffffff;
        padding: 10px 25px 40px 25px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-top: 5px;
    }
    h1 { color: #003366 !important; font-weight: 800 !important; }
    
    /* Estilos dos Cards Customizados */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd;
        animation: ft-pulse 1.5s ease-in-out infinite;
    }
    .ft-card-content { display: flex; flex-direction: column; }
    .ft-card-title { font-size: 13px; font-weight: 600; color: #444444; margin: 0; }
    .ft-card-value { font-size: 18px; font-weight: 700; color: #111111; margin: 0; }

    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 0.9; }
        50%  { transform: scale(1.10); opacity: 1; }
        100% { transform: scale(1);   opacity: 0.9; }
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net">
    """,
    unsafe_allow_html=True,
)

# --- Sidebar ---
LOGO_URL = "https://fromtherm.com.br"
st.sidebar.image(LOGO_URL, use_container_width=True)
st.sidebar.title("FromTherm")

# --- Título ---
st.title("Máquina de Teste Fromtherm")

# --- Pasta de dados ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=10)
def listar_arquivos_csv():
    if not os.path.exists(DADOS_DIR):
        return []
    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []
    for caminho in arquivos:
        nome = os.path.basename(caminho)
        try:
            partes = nome.replace(".csv", "").split("_")
            if len(partes) >= 6:
                data = datetime.strptime(partes[2], "%Y%m%d").date()
                info_arquivos.append({
                    "nome_arquivo": nome, "caminho": caminho, "linha": partes[1],
                    "data": data, "ano": data.year, "mes": data.month,
                    "hora": f"{partes[3][:2]}:{partes[3][2:]}",
                    "operacao": partes[4], "modelo": partes[5]
                })
        except: pass
    return info_arquivos

def carregar_csv_caminho(caminho):
    try:
        df = pd.read_csv(caminho, sep=";", engine="python")
        if len(df.columns) < 5: raise Exception
    except:
        df = pd.read_csv(caminho, sep=",", engine="python")
    
    df.columns = ["Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", 
                  "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]
    
    # Converter colunas para numérico (trata vírgula decimal)
    cols_num = ["Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "Vazão", "COP", "kW Consumo"]
    for col in cols_num:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
    return df

# --- Lógica Principal ---
arquivos = listar_arquivos_csv()

if not arquivos:
    st.warning("Nenhum arquivo encontrado em: " + DADOS_DIR)
    st.stop()

# Arquivo mais recente
arquivo_atual = max(arquivos, key=lambda x: (x["data"], x["hora"]))

try:
    df_dados = carregar_csv_caminho(arquivo_atual["caminho"])
    ultima = df_dados.iloc[-1]

    # Cabeçalho de Info
    st.info(f"**Modelo:** {arquivo_atual['modelo']} | **OP:** {arquivo_atual['operacao']} | **Data:** {arquivo_atual['data'].strftime('%d/%m/%Y')} | **Hora:** {arquivo_atual['hora']}")

    col1, col2, col3 = st.columns(3)

    with col1:
        # T-Ambiente
        st.markdown(f'<div class="ft-card"><i class="bi bi-thermometer-half ft-card-icon"></i><div class="ft-card-content"><p class="ft-card-title">T-Ambiente (°C)</p><p class="ft-card-value">{ultima["Ambiente"]}</p></div></div>', unsafe_allow_html=True)
        # T-Entrada
        st.markdown(f'<div class="ft-card"><i class="bi bi-arrow-down-circle ft-card-icon"></i><div class="ft-card-content"><p class="ft-card-title">T-Entrada (°C)</p><p class="ft-card-value">{ultima["Entrada"]}</p></div></div>', unsafe_allow_html=True)
        # T-Saída (VERMELHO)
        st.markdown(f'<div class="ft-card" style="border-left-color: #dc3545;"><i class="bi bi-arrow-up-circle ft-card-icon" style="color: #dc3545;"></i><div class="ft-card-content"><p class="ft-card-title">T-Saída (°C)</p><p class="ft-card-value">{ultima["Saída"]}</p></div></div>', unsafe_allow_html=True)

    with col2:
        # COP (Verde)
        st.markdown(f'<div class="ft-card" style="border-left-color: #198754;"><i class="bi bi-lightning-charge ft-card-icon" style="color: #198754;"></i><div class="ft-card-content"><p class="ft-card-title">COP</p><p class="ft-card-value">{ultima["COP"]}</p></div></div>', unsafe_allow_html=True)
        # Vazão
        st.markdown(f'<div class="ft-card" style="border-left-color: #0dcaf0;"><i class="bi bi-water ft-card-icon" style="color: #0dcaf0;"></i><div class="ft-card-content"><p class="ft-card-title">Vazão (L/h)</p><p class="ft-card-value">{ultima["Vazão"]}</p></div></div>', unsafe_allow_html=True)
        # Delta T
        st.markdown(f'<div class="ft-card"><i class="bi bi-moisture ft-card-icon"></i><div class="ft-card-content"><p class="ft-card-title">ΔT (°C)</p><p class="ft-card-value">{ultima["ΔT"]}</p></div></div>', unsafe_allow_html=True)

    with col3:
        # Tensão (Amarelo)
        st.markdown(f'<div class="ft-card" style="border-left-color: #ffc107;"><i class="bi bi-cpu ft-card-icon" style="color: #ffc107;"></i><div class="ft-card-content"><p class="ft-card-title">Tensão (V)</p><p class="ft-card-value">{ultima["Tensão"]}</p></div></div>', unsafe_allow_html=True)
        # Corrente
        st.markdown(f'<div class="ft-card" style="border-left-color: #ffc107;"><i class="bi bi-activity ft-card-icon" style="color: #ffc107;"></i><div class="ft-card-content"><p class="ft-card-title">Corrente (A)</p><p class="ft-card-value">{ultima["Corrente"]}</p></div></div>', unsafe_allow_html=True)
        # Consumo
        st.markdown(f'<div class="ft-card" style="border-left-color: #ffc107;"><i class="bi bi-speedometer2 ft-card-icon" style="color: #ffc107;"></i><div class="ft-card-content"><p class="ft-card-title">kW Consumo</p><p class="ft-card-value">{ultima["kW Consumo"]}</p></div></div>', unsafe_allow_html=True)

    # --- Gráfico ---
    st.markdown("### Histórico de Temperaturas")
    fig = px.line(df_dados, x="Time", y=["Entrada", "Saída", "Ambiente"],
                 color_discrete_map={"Entrada": "#0d6efd", "Saída": "#dc3545", "Ambiente": "#6c757d"},
                 template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
