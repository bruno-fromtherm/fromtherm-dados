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

# Função para exibir valor em um card
def mostra_valor(titulo, valor, unidade="", icon="📈", is_red=False):
    st.markdown(
        f"""
        <div class="ft-card">
            <span class="ft-card-icon {'red' if is_red else ''}">{icon}</span>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Função para criar PDF (REVISADA PARA NÃO USAR 'inch')
def criar_pdf(df, info_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    # Estilo para título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h2'],
        alignment=1, # Centro
        spaceAfter=14,
    )
    # Estilo para subtítulo
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['h3'],
        alignment=1, # Centro
        spaceAfter=8,
    )
    # Estilo para texto normal
    normal_style = styles['Normal']

    # Título do relatório
    elements.append(Paragraph("Relatório de Dados da Máquina Fromtherm", title_style))
    elements.append(Paragraph(f"Modelo: {info_arquivo['modelo']} | Operação: {info_arquivo['operacao']}", subtitle_style))
    elements.append(Paragraph(f"Data: {info_arquivo['data_arquivo'].strftime('%d/%m/%Y')} | Hora: {info_arquivo['hora_arquivo'].strftime('%H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.2 * 20)) # Usando um valor fixo em pontos (1 polegada = 72 pontos)

    # Preparar dados para a tabela
    data = [df.columns.tolist()] + df.values.tolist()

    # Criar tabela
    tabela = Table(data)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
            ]
        )
    )

    elements.append(tabela)
    elements.append(Spacer(1, 0.2 * 20)) # Usando um valor fixo em pontos

    # Constrói o PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Barra Lateral
# -------------------------------------------------
with st.sidebar:
    # Tenta carregar a imagem, com fallback se não encontrar
    try:
        st.image(
            "LOGO-FROMTHERM.png",
            use_column_width=True,
        )
    except Exception:
        st.warning("Logo não encontrada. Verifique se 'LOGO-FROMTHERM.png' está na mesma pasta do dashboard.py.")

    st.title("Filtros de Históricos")

    todos_arquivos_info = listar_arquivos_csv()

    if not todos_arquivos_info:
        st.info("Nenhum histórico encontrado na pasta de dados.")
        modelos_disponiveis = []
        anos_disponiveis = []
        meses_disponiveis = []
        datas_disponiveis = []
        operacoes_disponiveis = []
    else:
        modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
        anos_disponiveis = sorted(list(set(a["data_arquivo"].year for a in todos_arquivos_info)))
        meses_disponiveis = sorted(list(set(a["data_arquivo"].month for a in todos_arquivos_info)))
        datas_disponiveis = sorted(list(set(a["data_arquivo"] for a in todos_arquivos_info)))
        operacoes_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))

    filtro_modelo = st.selectbox("Modelo", ["Todos"] + modelos_disponiveis, key="filtro_modelo")
    filtro_ano = st.selectbox("Ano", ["Todos"] + anos_disponiveis, key="filtro_ano")
    filtro_mes = st.selectbox("Mês", ["Todos"] + meses_disponiveis, format_func=lambda x: datetime(1, x, 1).strftime('%B') if x != "Todos" else "Todos", key="filtro_mes")
    filtro_data = st.selectbox("Data", ["Todos"] + datas_disponiveis, format_func=lambda x: x.strftime('%d/%m/%Y') if x != "Todos" else "Todos", key="filtro_data")
    filtro_operacao = st.selectbox("Operação", ["Todos"] + operacoes_disponiveis, key="filtro_operacao")

    # Aplica os filtros
    arquivos_filtrados = todos_arquivos_info
    if filtro_modelo != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == filtro_modelo]
    if filtro_ano != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"].year == filtro_ano]
    if filtro_mes != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"].month == filtro_mes]
    if filtro_data != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"] == filtro_data]
    if filtro_operacao != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == filtro_operacao]

# -------------------------------------------------
# Conteúdo Principal
# -------------------------------------------------
st.title("Máquina de Teste Fromtherm")

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.header("Dashboard de Última Leitura")

    # Tenta carregar o último arquivo para os cards de última leitura
    ultimo_arquivo_info = None
    if todos_arquivos_info:
        # Pega o arquivo mais recente (já está ordenado por data de modificação)
        ultimo_arquivo_info = todos_arquivos_info[0]
        df_ultimo = carregar_csv_caminho(ultimo_arquivo_info["caminho"])

        if df_ultimo is not None and not df_ultimo.empty:
            ultima_linha = df_ultimo.iloc[-1]
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                mostra_valor("T-Ambiente", f"{ultima_linha.get('Ambiente', 'N/D'):.2f}", "°C", "🌡️")
            with col2:
                mostra_valor("T-Entrada", f"{ultima_linha.get('Entrada', 'N/D'):.2f}", "°C", "➡️")
            with col3:
                mostra_valor("T-Saída", f"{ultima_linha.get('Saída', 'N/D'):.2f}", "°C", "⬅️")
            with col4:
                mostra_valor("T-Delta", f"{ultima_linha.get('DeltaT', 'N/D'):.2f}", "°C", "∆T")
            with col5:
                mostra_valor("Vazão", f"{ultima_linha.get('Vazao', 'N/D'):.2f}", "L/h", "💧")
        else:
            st.info("Nenhum dado válido encontrado no último histórico para exibir nos cards.")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1: mostra_valor("T-Ambiente", "N/D", "°C", "🌡️")
            with col2: mostra_valor("T-Entrada", "N/D", "°C", "➡️")
            with col3: mostra_valor("T-Saída", "N/D", "°C", "⬅️")
            with col4: mostra_valor("T-Delta", "N/D", "°C", "∆T")
            with col5: mostra_valor("Vazão", "N/D", "L/h", "💧")
    else:
        st.info("Nenhum histórico disponível para exibir cards de última leitura.")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: mostra_valor("T-Ambiente", "N/D", "°C", "🌡️")
        with col2: mostra_valor("T-Entrada", "N/D", "°C", "➡️")
        with col3: mostra_valor("T-Saída", "N/D", "°C", "⬅️")
        with col4: mostra_valor("T-Delta", "N/D", "°C", "∆T")
        with col5: mostra_valor("Vazão", "N/D", "L/h", "💧")


    st.header("Históricos Disponíveis")

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arq in arquivos_filtrados:
            nome_display = f"Modelo: {arq['modelo']} | OP: {arq['operacao']} | Data: {arq['data_arquivo'].strftime('%d/%m/%Y')} | Hora: {arq['hora_arquivo'].strftime('%H:%M')}"
            with st.expander(nome_display):
                df_exibir = carregar_csv_caminho(arq["caminho"])
                if df_exibir is not None and not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Botão de download PDF
                        nome_pdf = f"Maquina_FT{arq['modelo']}_OP{arq['operacao']}_{arq['data_arquivo'].strftime('%d%m%Y')}_{arq['hora_arquivo'].strftime('%H%M')}hs.pdf"
                        pdf_buffer = criar_pdf(df_exibir, arq)
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=nome_pdf,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    with col_dl2:
                        # Botão de download Excel
                        nome_excel = f"Maquina_FT{arq['modelo']}_OP{arq['operacao']}_{arq['data_arquivo'].strftime('%d%m%Y')}_{arq['hora_arquivo'].strftime('%H%M')}hs.xlsx"
                        excel_buffer = BytesIO()
                        df_exibir.to_excel(excel_buffer, index=False)
                        excel_buffer.seek(0)
                        st.download_button(
                            label="Baixar Excel",
                            data=excel_buffer,
                            file_name=nome_excel,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                else:
                    st.warning("Não foi possível exibir a planilha para este histórico.")

with tab2:
    st.header("Crie Seu Gráfico Personalizado")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo disponível para gerar gráficos.")
    else:
        modelos_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
        modelo_graf = st.selectbox("Modelo:", modelos_graf, key="graf_modelo")

        ops_graf = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["modelo"] == modelo_graf)))
        op_graf = st.selectbox("Operação (OP):", ops_graf, key="graf_op")

        datas_disp = sorted(list(set(
            a["data_arquivo"]
            for a in todos_arquivos_info
            if a["modelo"] == modelo_graf and a["operacao"] == op_graf
        )), reverse=True) # Ordena as datas para a mais recente primeiro
        data_graf = st.selectbox("Data:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'), key="graf_data")

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