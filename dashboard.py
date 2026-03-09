import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
# from reportlab.lib.units import inch  # <-- REMOVIDO PARA EVITAR NameError

from io import BytesIO
import plotly.express as px

# -------------------------------------------------
# Configuração básica
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS simples (mantém layout, não mexe em nada estrutural)
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde o botão de menu do Streamlit, que geralmente contém o "0" */
    button[data-testid="stSidebarNavToggle"] {
        display: none !important;
    }
    /* Esconde o elemento que pode conter o "0" em alguns casos */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Outras tentativas de esconder elementos que podem aparecer */
    summary {
        display: none !important;
    }
    div[data-testid="stAppViewContainer"] > div:first-child span {
        display: none !important;
    }

    /* Estilo dos cards */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .ft-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd;
        animation: ft-pulse 1.5s ease-in-out infinite;
    }
    .ft-card-icon.red {
        color: #dc3545;
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
    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 1; }
        50%  { transform: scale(1.05); opacity: 0.8; }
        100% { transform: scale(1);   opacity: 1; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Funções auxiliares
# -------------------------------------------------

# Caminho para a pasta de dados brutos
# Ajustado para ser mais robusto no Streamlit Cloud
DADOS_DIR = os.path.join(
    ".", "dados_brutos", "historico_L1", "IP_registro192.168.2.150", "datalog"
)

# Função para extrair informações do nome do arquivo
def extrair_info_arquivo(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo)
    # Padrão: historico_L1_YYYYMMDD_HHMM_OPXXXX_FTYYY.csv
    match = re.match(
        r"historico_L1_(\d{8})_(\d{4})_OP(\d+)_FT(\w+)\.csv", nome_arquivo
    )
    if match:
        data_str, hora_str, operacao, modelo = match.groups()
        try:
            data_obj = datetime.strptime(data_str, "%Y%m%d").date()
            hora_obj = datetime.strptime(hora_str, "%H%M").time()
            return {
                "caminho": caminho_arquivo,
                "nome_arquivo": nome_arquivo,
                "data_arquivo": data_obj,
                "hora_arquivo": hora_obj,
                "operacao": operacao,
                "modelo": modelo,
                "data_modificacao": datetime.fromtimestamp(os.path.getmtime(caminho_arquivo)),
            }
        except ValueError:
            pass
    return None

# Função para listar arquivos CSV
@st.cache_data(ttl=300) # Cache por 5 minutos
def listar_arquivos_csv():
    todos_arquivos_info = []
    if os.path.exists(DADOS_DIR):
        for caminho_arquivo in glob.glob(os.path.join(DADOS_DIR, "*.csv")):
            info = extrair_info_arquivo(caminho_arquivo)
            if info:
                todos_arquivos_info.append(info)
    return sorted(todos_arquivos_info, key=lambda x: x["data_modificacao"], reverse=True)

# Função para carregar CSV
@st.cache_data(ttl=300) # Cache por 5 minutos
def carregar_csv_caminho(caminho_arquivo):
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', decimal=',')
        # Tenta converter 'DateTime' para datetime, se existir
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            df = df.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
        return None

# Função para extrair a última linha de um DataFrame
def extrair_ultima_linha(df):
    if df is not None and not df.empty:
        return df.iloc[-1].to_dict()
    return {}

# Função para exibir valor em um card (AJUSTADA PARA LIDAR COM N/D)
def mostra_valor(titulo, valor, unidade="", icone=""):
    # Tenta converter o valor para float para formatar, se não for possível, mantém como string
    try:
        valor_formatado = f"{float(valor):.2f}"
    except (ValueError, TypeError):
        valor_formatado = "N/D" # Se não for número, exibe N/D

    st.markdown(
        f"""
        <div class="ft-card">
            <span class="ft-card-icon">{icone}</span>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor_formatado} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Função para criar PDF (REVISADA PARA NÃO USAR 'inch' E SER MAIS SIMPLES)
def criar_pdf(df, info_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheets()
    elements = []

    # Título do PDF
    titulo_pdf = f"Relatório - Modelo {info_arquivo['modelo']} | OP {info_arquivo['operacao']} | Data {info_arquivo['data_arquivo'].strftime('%d/%m/%Y')}"
    elements.append(Paragraph(titulo_pdf, styles['h2']))
    elements.append(Spacer(1, 12)) # Espaço

    # Tabela de dados
    data = [df.columns.tolist()] + df.values.tolist()
    tabela = Table(data)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
            ]
        )
    )
    elements.append(tabela)

    # Constrói o PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Layout do Streamlit
# -------------------------------------------------

# Barra lateral
st.sidebar.image("LOGO-FROMTHERM.png", use_column_width=True) # Imagem do logo
st.sidebar.title("Filtros de Pesquisa")

todos_arquivos_info = listar_arquivos_csv()

# Extrair opções únicas para os filtros
modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info)))
anos_disponiveis = sorted(list(set(a["data_arquivo"].year for a in todos_arquivos_info)))
meses_disponiveis = sorted(list(set(a["data_arquivo"].month for a in todos_arquivos_info)))
operacoes_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info)))

# Filtros na barra lateral
filtro_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_disponiveis)
filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_disponiveis)
filtro_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_disponiveis, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos")
filtro_data = st.sidebar.date_input("Data Específica", None)
filtro_operacao = st.sidebar.selectbox("Operação", ["Todas"] + operacoes_disponiveis)

# Aplicar filtros
arquivos_filtrados = todos_arquivos_info
if filtro_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == filtro_modelo]
if filtro_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"].year == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"].month == filtro_mes]
if filtro_data:
    arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"] == filtro_data]
if filtro_operacao != "Todas":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == filtro_operacao]

# --- Conteúdo Principal ---
st.title("Máquina de Teste Fromtherm")

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.header("Dashboard de Última Leitura")

    # Encontrar o arquivo mais recente para os cards de última leitura
    ultima_linha = {}
    if todos_arquivos_info:
        arquivo_mais_recente = todos_arquivos_info[0]
        df_recente = carregar_csv_caminho(arquivo_mais_recente["caminho"])
        ultima_linha = extrair_ultima_linha(df_recente)

    # Cards de Última Leitura
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        mostra_valor("T-Ambiente", ultima_linha.get("Ambiente", "N/D"), "°C", "🌡️")
    with col2:
        mostra_valor("T-Entrada", ultima_linha.get("Entrada", "N/D"), "°C", "➡️")
    with col3:
        mostra_valor("T-Saída", ultima_linha.get("Saída", "N/D"), "°C", "⬅️")
    with col4:
        mostra_valor("Delta T", ultima_linha.get("DeltaT", "N/D"), "°C", "↔️")
    with col5:
        mostra_valor("Vazão", ultima_linha.get("Vazao", "N/D"), "L/h", "💧")

    st.markdown("---") # Separador

    st.header("Históricos Disponíveis")

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for info_arquivo in arquivos_filtrados:
            expander_label = f"Modelo: {info_arquivo['modelo']} | OP: {info_arquivo['operacao']} | Data: {info_arquivo['data_arquivo'].strftime('%d/%m/%Y')} | Hora: {info_arquivo['hora_arquivo'].strftime('%H:%M')}"
            with st.expander(expander_label):
                df_exibir = carregar_csv_caminho(info_arquivo["caminho"])
                if df_exibir is None or df_exibir.empty:
                    st.warning("Arquivo vazio ou ilegível.")
                else:
                    st.dataframe(df_exibir, use_container_width=True)

                    # Botões de Download
                    nome_base = f"Maquina_{info_arquivo['modelo']}_OP{info_arquivo['operacao']}_{info_arquivo['data_arquivo'].strftime('%d%m%Y')}_{info_arquivo['hora_arquivo'].strftime('%H%M')}"

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Download PDF
                        pdf_buffer = criar_pdf(df_exibir, info_arquivo)
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=f"{nome_base}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    with col_dl2:
                        # Download Excel
                        excel_buffer = BytesIO()
                        df_exibir.to_excel(excel_buffer, index=False, engine="openpyxl")
                        excel_buffer.seek(0)
                        st.download_button(
                            label="Baixar Excel",
                            data=excel_buffer,
                            file_name=f"{nome_base}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

with tab2:
    st.header("Crie Seu Gráfico Personalizado")

    # Filtros para o gráfico
    modelos_graf_disp = sorted(list(set(a["modelo"] for a in todos_arquivos_info)))
    operacoes_graf_disp = sorted(list(set(a["operacao"] for a in todos_arquivos_info)))

    modelo_graf = st.selectbox("Selecione o Modelo para o Gráfico:", modelos_graf_disp)
    op_graf = st.selectbox("Selecione a Operação para o Gráfico:", operacoes_graf_disp)

    # Filtrar datas disponíveis com base no modelo e operação selecionados
    datas_disp = sorted(list(set(
        a["data_arquivo"]
        for a in todos_arquivos_info
        if a["modelo"] == modelo_graf and a["operacao"] == op_graf
    )), reverse=True) # Datas mais recentes primeiro

    data_graf = st.selectbox("Selecione a Data do Arquivo:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))

    arq_escolhido = None
    for a in todos_arquivos_info:
        if (
            a["modelo"] == modelo_graf
            and a["operacao"] == op_graf
            and a["data_arquivo"] == data_graf
        ):
            arq_escolhido = a
            break

    if arq_escolhido is None:
        st.warning("Nenhum arquivo encontrado para esse modelo/OP/data.")
    else:
        df_graf = carregar_csv_caminho(arq_escolhido["caminho"])
        if df_graf is None or df_graf.empty:
            st.warning("Arquivo selecionado vazio ou ilegível.")
        else:
            opcoes_variaveis = [
                "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
            ]
            opcoes_variaveis_existentes = [c for c in opcoes_variaveis if c in df_graf.columns]

            vars_sel = st.multiselect(
                "Selecione as variáveis para plotar:",
                opcoes_variaveis_existentes,
                default=[v for v in ["Ambiente", "Entrada", "Saída"] if v in opcoes_variaveis_existentes],
            )
            if not vars_sel:
                st.info("Selecione pelo menos uma variável.")
            else:
                df_melted = df_graf[["DateTime"] + vars_sel].melt(
                    id_vars="DateTime",
                    value_vars=vars_sel,
                    var_name="Variável",
                    value_name="Valor",
                )
                fig = px.line(
                    df_melted,
                    x="DateTime",
                    y="Valor",
                    color="Variável",
                    title=f"Modelo {modelo_graf} | OP {op_graf} | {data_graf.strftime('%d/%m/%Y')}",
                    markers=True,
                )
                fig.update_yaxes(rangemode="tozero")
                fig.update_layout(
                    xaxis_title="Tempo",
                    yaxis_title="Valor",
                    hovermode="x unified",
                    legend_title="Variáveis",
                )
                st.plotly_chart(fig, use_container_width=True)

                st.markdown(
                    "- Use o botão de **fullscreen** no gráfico (canto superior direito do gráfico) para tela cheia.\n"
                    "- Use o ícone de **câmera** para baixar como imagem (PNG).\n"
                    "- A imagem pode ser enviada por WhatsApp, e-mail, etc., em PC ou celular."
                )