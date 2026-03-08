import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import plotly.express as px

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")  # Título da aba do navegador

# =========================
#  CSS GLOBAL (correção do "0", cards com animação suave)
# =========================
st.markdown(
    """
    <style>
    /* REMOÇÃO TENTATIVA DO "0" TEIMOSO (mas sem exagero) */
    div[data-testid="stAppViewContainer"] > div:first-child span {
        font-size: 0px !important;
        color: transparent !important;
    }

    /* Estilo dos cards de métricas */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd; /* Cor padrão da borda */
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd; /* Cor padrão do ícone */
        animation: ft-pulse 1.5s ease-in-out infinite; /* Animação de pulso suave para todos */
    }
    .ft-card-icon.red {
        color: #dc3545; /* Cor vermelha para T-Saída */
    }
    .ft-card-content {
        display: flex;
        flex-direction: column;
    }
    .ft-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #444444;
        margin: 0;
        padding: 0;
    }
    .ft-card-value {
        font-size: 18px;
        font-weight: 700;
        color: #111111;
        margin: 0;
        padding: 0;
    }

    /* Animação de pulso suave (única para todos os ícones) */
    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 0.9; }
        50%  { transform: scale(1.05); opacity: 1; }
        100% { transform: scale(1);   opacity: 0.9; }
    }
    </style>

    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Teste de Máquinas Fromtherm")  # Título principal do dashboard

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_20260303_2140_OP1234_FT185.csv
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        linha = ""
        data = None
        ano = None
        mes = None
        hora = ""
        operacao = ""
        modelo = ""

        try:
            partes = nome.replace(".csv", "").split("_")
            # esperado: historico_L1_20260303_2140_OP1234_FT185.csv
            if len(partes) >= 6:
                linha = partes[1]             # L1
                data_str = partes[2]          # 20260303
                hora_str = partes[3]          # 2140
                operacao = partes[4]          # OP1234
                modelo = partes[5]            # FT185 ou similar

                data = datetime.strptime(data_str, "%Y%m%d").date()
                ano = data.year
                mes = data.month
                hora = f"{hora_str[:2]}:{hora_str[2:]}"
        except Exception:
            pass

        info_arquivos.append(
            {
                "nome_arquivo": nome,
                "caminho": caminho,
                "linha": linha,
                "data": data,
                "ano": ano,
                "mes": mes,
                "hora": hora,
                "operacao": operacao,
                "modelo": modelo,
            }
        )

    return info_arquivos


# --- Função para carregar um CSV (ponto e vírgula ou vírgula) ---
def carregar_csv_caminho(caminho: str) -> pd.DataFrame:
    try:
        return pd.read_csv(caminho, sep=";", engine="python")
    except Exception:
        return pd.read_csv(caminho, sep=",", engine="python")


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo .csv de histórico encontrado na pasta '{DADOS_DIR}'.")
    st.info("Verifique se os arquivos estão sendo salvos corretamente no diretório configurado.")
else:
    # --- Determinar o arquivo mais recente (por data + hora) ---
    arquivos_validos = [a for a in todos_arquivos_info if a["data"] is not None]
    if arquivos_validos:
        arquivo_mais_recente = max(
            arquivos_validos, key=lambda x: (x["data"], x["hora"])
        )

        st.markdown("## Última Leitura Registrada")

        try:
            df_ultimo = carregar_csv_caminho(arquivo_mais_recente["caminho"])
            if df_ultimo.empty:
                st.info("O arquivo mais recente está vazio.")
            else:
                df_ultimo.columns = [
                    "Date",
                    "Time",
                    "Ambiente",
                    "Entrada",
                    "Saída",
                    "ΔT",
                    "Tensão",
                    "Corrente",
                    "kcal/h",
                    "Vazão",
                    "kW Aquecimento",
                    "kW Consumo",
                    "COP",
                ]

                ultima_linha = df_ultimo.iloc[-1]

                col_info_geral, _, _ = st.columns([2, 1, 1])
                with col_info_geral:
                    st.markdown(
                        f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
                        f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
                        f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y') if arquivo_mais_recente['data'] else 'N/D'} | "
                        f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
                    )

                col1, col2, col3 = st.columns(3)

                # --- Coluna 1 ---
                with col1:
                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-thermometer-half ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">T-Ambiente (°C)</p>
                                <p class="ft-card-value">{ultima_linha['Ambiente']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-arrow-down-circle ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">T-Entrada (°C)</p>
                                <p class="ft-card-value">{ultima_linha['Entrada']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # DIF com ícone de diferencial de temperatura (seta para cima e para baixo)
                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-arrow-down-up ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">DIF (ΔT) (°C)</p>
                                <p class="ft-card-value">{ultima_linha['ΔT']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # --- Coluna 2 ---
                with col2:
                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-lightning-charge ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">Tensão (V)</p>
                                <p class="ft-card-value">{ultima_linha['Tensão']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-plug ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">Corrente (A)</p>
                                <p class="ft-card-value">{ultima_linha['Corrente']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-fire ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">kcal/h</p>
                                <p class="ft-card-value">{ultima_linha['kcal/h']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # --- Coluna 3 ---
                with col3:
                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-water ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">Vazão</p>
                                <p class="ft-card-value">{ultima_linha['Vazão']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-graph-up-arrow ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">kW Aquecimento</p>
                                <p class="ft-card-value">{ultima_linha['kW Aquecimento']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-lightbulb ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">kW Consumo</p>
                                <p class="ft-card-value">{ultima_linha['kW Consumo']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="bi bi-speedometer ft-card-icon"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">COP</p>
                                <p class="ft-card-value">{ultima_linha['COP']}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("---")

        except Exception as e:
            st.error(f"Não foi possível gerar o painel da última leitura: {e}")
            st.info("Verifique se o formato do CSV está conforme o padrão esperado.")

    # ----------------------------------------------------------------------
    # DAQUI PRA BAIXO: SEU CÓDIGO ORIGINAL DE HISTÓRICOS, TABELAS, PDFs, GRÁFICOS
    # ----------------------------------------------------------------------
    # (estou assumindo que o restante do arquivo está exatamente como você colou;
    #  se faltar alguma parte abaixo, é só colar de volta do seu backup original)
    # ... resto do código de abas, históricos, download de CSV/PDF e gráficos ...