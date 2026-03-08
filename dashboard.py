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

# -------------------------------------------------
# Configurações da página
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS global (remove o “0” e estiliza os cards)
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* Esconde o “0” que aparece no menu de opções */
    button[title="View options"] {display:none !important;}
    /* Estilo dos cards */
    .ft-card {
        background:#fff;
        border-radius:12px;
        padding:14px 16px;
        box-shadow:0 2px 6px rgba(0,0,0,0.08);
        display:flex;
        align-items:center;
        margin-bottom:10px;
        border-left:4px solid #0d6efd;
    }
    .ft-card-icon {
        font-size:26px;
        margin-right:10px;
        color:#0d6efd;
        animation:ft-pulse 1.5s ease-in-out infinite;
    }
    .ft-card-icon.red {color:#dc3545;}
    .ft-card-content {display:flex;flex-direction:column;}
    .ft-card-title {font-size:13px;font-weight:600;color:#444;margin:0;}
    .ft-card-value {font-size:18px;font-weight:700;color:#111;margin:0;}
    @keyframes ft-pulse{
        0%{transform:scale(1);opacity:0.9;}
        50%{transform:scale(1.05);opacity:1;}
        100%{transform:scale(1);opacity:0.9;}
    }
    </style>
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Sidebar (logo + título)
# -------------------------------------------------
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# -------------------------------------------------
# Pasta onde os CSVs são armazenados
# -------------------------------------------------
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# -------------------------------------------------
# Funções auxiliares
# -------------------------------------------------
@st.cache_data(ttl=10)  # 10 s para refletir arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Retorna uma lista de dicionários com informações básicas de cada CSV.
    Se o nome não seguir o padrão esperado, os campos ‘modelo’, ‘operacao’,
    ‘data_arquivo’ e ‘hora_arquivo’ ficam como 'N/D'.
    """
    padrao = os.path.join(DADOS_DIR, "*.csv")
    caminhos = glob.glob(padrao)

    arquivos = []
    for caminho in sorted(caminhos, key=os.path.getmtime, reverse=True):
        nome = os.path.basename(caminho)

        # Tentativa simples de extrair modelo, OP, data e hora do nome
        # Exemplo esperado: historico_L1_20240308_1430_OP1234_FT185.csv
        modelo = operacao = data_str = hora_str = "N/D"
        try:
            partes = nome.split("_")
            modelo = partes[1] if len(partes) > 1 else "N/D"
            data_str = partes[2] if len(partes) > 2 else "N/D"
            hora_str = partes[3] if len(partes) > 3 else "N/D"
            operacao = partes[4].replace("OP", "") if len(partes) > 4 else "N/D"
        except Exception:
            pass

        # Formata data/hora para exibição (se possível)
        data_exib = "N/D"
        hora_exib = "N/D"
        try:
            data_exib = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")
        except Exception:
            pass
        try:
            hora_exib = f"{hora_str[:2]}:{hora_str[2:]}" if len(hora_str) == 4 else "N/D"
        except Exception:
            pass

        arquivos.append({
            "caminho": caminho,
            "nome_arquivo": nome,
            "modelo": modelo,
            "operacao": operacao,
            "data_arquivo": data_exib,
            "hora_arquivo": hora_exib,
            "data_modificacao": datetime.fromtimestamp(os.path.getmtime(caminho))
        })
    return arquivos

@st.cache_data
def carregar_csv_caminho(caminho):
    """Lê o CSV e garante que as colunas esperadas existam."""
    colunas_esperadas = [
        "Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT",
        "Tensão", "Corrente", "kcal/h", "Vazão",
        "kW Aquecimento", "kW Consumo", "COP"
    ]
    try:
        df = pd.read_csv(caminho, sep=";", decimal=",")
        # Renomeia colunas caso o CSV use nomes diferentes
        rename_map = {
            "Date": "Date", "Time": "Time",
            "Ambiente": "Ambiente", "Entrada": "Entrada", "Saída": "Saída",
            "DeltaT": "ΔT", "Delta_T": "ΔT", "ΔT": "ΔT",
            "Tensão": "Tensão", "Tensao": "Tensão",
            "Corrente": "Corrente",
            "kcal/h": "kcal/h", "Kcal_h": "kcal/h",
            "Vazão": "Vazão", "Vazao": "Vazão",
            "kW Aquecimento": "kW Aquecimento", "KWAquecimento": "kW Aquecimento",
            "kW Consumo": "kW Consumo", "KWConsumo": "kW Consumo",
            "COP": "COP"
        }
        df.rename(columns=rename_map, inplace=True)
        # Garante que todas as colunas esperadas existam (preenche com NaN se faltar)
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = pd.NA
        return df[colunas_esperadas]
    except Exception as e:
        st.error(f"Erro ao ler {os.path.basename(caminho)}: {e}")
        return pd.DataFrame(columns=colunas_esperadas)

def exibir_card(titulo, valor, unidade="", icone="bi bi-thermometer-half", cor_icone=""):
    """Renderiza um card de métrica usando HTML + CSS."""
    st.markdown(
        f"""
        <div class="ft-card">
            <i class="{icone} ft-card-icon {cor_icone}"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def mostra_valor(df, coluna, fmt="{:.2f}", unidade="", default="N/D"):
    """Retorna o último valor da coluna formatado ou o default."""
    if not df.empty and coluna in df.columns:
        val = df[coluna].iloc[-1]
        if pd.notna(val):
            return fmt.format(val) + f" {unidade}"
    return default

# -------------------------------------------------
# Carrega a lista de arquivos (cache para não recarregar a cada interação)
# -------------------------------------------------
if "todos_arquivos" not in st.session_state:
    st.session_state.todos_arquivos = listar_arquivos_csv()
todos_arquivos = st.session_state.todos_arquivos

# -------------------------------------------------
# Título principal
# -------------------------------------------------
st.title("Dashboard de Testes de Máquinas Fromtherm")

# -------------------------------------------------
# Última Leitura
# -------------------------------------------------
st.header("Última Leitura Registrada")
if not todos_arquivos:
    st.info("Nenhum arquivo CSV encontrado na pasta de dados.")
else:
    # O primeiro da lista já é o mais recente (ordenado por data de modificação)
    ultimo = todos_arquivos[0]
    df_ultimo = carregar_csv_caminho(ultimo["caminho"])

    st.markdown(
        f"**Modelo:** {ultimo['modelo']} | "
        f"**OP:** {ultimo['operacao']} | "
        f"**Data:** {ultimo['data_arquivo']} | "
        f"**Hora:** {ultimo['hora_arquivo']}"
    )

    # ---- Cards de métricas ----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        exibir_card("T‑Ambiente", mostra_valor(df_ultimo, "Ambiente", unidade="°C"),
                    icone="bi bi-thermometer-half")
    with col2:
        exibir_card("T‑Entrada", mostra_valor(df_ultimo, "Entrada", unidade="°C"),
                    icone="bi bi-arrow-down-circle")
    with col3:
        exibir_card("T‑Saída", mostra_valor(df_ultimo, "Saída", unidade="°C"),
                    icone="bi bi-arrow-up-circle", cor_icone="red")
    with col4:
        exibir_card("DIF", mostra_valor(df_ultimo, "ΔT", unidade="°C"),
                    icone="bi bi-arrow-down-up")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        exibir_card("Tensão", mostra_valor(df_ultimo, "Tensão", unidade="V"),
                    icone="bi bi-lightning-charge")
    with col6:
        exibir_card("Corrente", mostra_valor(df_ultimo, "Corrente", unidade="A"),
                    icone="bi bi-lightning")
    with col7:
        exibir_card("kcal/h", mostra_valor(df_ultimo, "kcal/h"),
                    icone="bi bi-fire")
    with col8:
        exibir_card("Vazão", mostra_valor(df_ultimo, "Vazão", unidade="L/min"),
                    icone="bi bi-water")

    col9, col10 = st.columns(2)
    with col9:
        exibir_card("kW Aquecimento", mostra_valor(df_ultimo, "kW Aquecimento", unidade="kW"),
                    icone="bi bi-sun")
    with col10:
        exibir_card("kW Consumo", mostra_valor(df_ultimo, "kW Consumo", unidade="kW"),
                    icone="bi bi-power")

    # ---- Card de performance (COP) ----
    st.markdown("---")
    st.subheader("Performance")
    col_cop, _, _, _ = st.columns(4)
    with col_cop:
        exibir_card("COP", mostra_valor(df_ultimo, "COP"),
                    icone="bi bi-graph-up")

# -------------------------------------------------
# Históricos Disponíveis
# -------------------------------------------------
st.markdown("---")
st.header("Históricos Disponíveis")

if not todos_arquivos:
    st.info("Nenhum histórico encontrado na pasta de dados.")
else:
    for arq in todos_arquivos:
        with st.expander(
            f"{arq['nome_arquivo']} (Modelo: {arq['modelo']}, OP: {arq['operacao']}, "
            f"Data: {arq['data_arquivo']} {arq['hora_arquivo']})",
            expanded=False
        ):
            st.write(f"**Caminho:** {arq['caminho']}")
            st.write(
                f"**Modificado em:** {arq['data_modificacao'].strftime('%d/%m/%Y %H:%M:%S')}"
            )
            # Botão opcional para visualizar o CSV completo (pode ser re‑ativado depois)
            # if st.button("Ver conteúdo", key=arq['nome_arquivo']):
            #     df = carregar_csv_caminho(arq['caminho'])
            #     st.dataframe(df)

# -------------------------------------------------
# Aba de Gráficos (placeholder – será reativada depois)
# -------------------------------------------------
st.markdown("---")
st.header("Visualização Gráfica")
if not todos_arquivos:
    st.info("Nenhum dado disponível para gerar gráficos.")
else:
    st.info(
        "A funcionalidade de gráficos será reintegrada assim que a listagem e os cards estiverem estáveis."
    )