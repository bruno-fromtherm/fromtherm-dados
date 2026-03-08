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
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde qualquer elemento span que seja o primeiro filho de um div no topo da página */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > div:first-child > span {
        display: none !important;
    }
    /* Uma alternativa mais genérica, caso a de cima não funcione em todos os casos */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > span {
        display: none !important;
    }
    /* E uma última tentativa para qualquer span pequeno e solto no topo */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Outra tentativa para esconder o "0" que pode ser um elemento de "summary" */
    summary {
        display: none !important;
    }
    /* Esconder o botão de menu que pode conter o "0" */
    button[title="View options"] {
        display: none !important;
    }
    /* Esconder o ícone de menu do Streamlit que pode conter o "0" */
    .st-emotion-cache-1r6dm1x { /* Seletor específico para o ícone de menu */
        display: none !important;
    }
    /* Esconder o elemento pai do ícone de menu */
    .st-emotion-cache-10q71g7 { /* Seletor específico para o container do ícone de menu */
        display: none !important;
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
        50%  { transform: scale(1.05); opacity: 1;   }
        100% { transform: scale(1);   opacity: 0.9; }
    }

    /* Estilo para o título principal */
    .main-title {
        font-size: 2.5em;
        font-weight: bold;
        color: #0d6efd;
        text-align: center;
        margin-bottom: 20px;
    }

    /* Ajuste para o st.expander */
    .st-emotion-cache-p5m9x9 { /* Seletor para o cabeçalho do expander */
        font-weight: bold;
        color: #0d6efd;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Constantes e Funções Auxiliares
# -------------------------------------------------

# Caminho da pasta de dados brutos (ajustado para o seu repositório)
DADOS_DIR = "./dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# Expressão regular para extrair informações do nome do arquivo
# Ex: historico_L1_YYYYMMDD_HHMM_OPXXXX_FTYYY.csv
# Grupo 1: YYYYMMDD, Grupo 2: HHMM, Grupo 3: OPXXXX, Grupo 4: FTYYY
FILENAME_PATTERN = re.compile(r"historico_L1_(\d{8})_(\d{4})_(OP\d{4})_(FT\d{3})\.csv")

# Função para extrair informações do nome do arquivo
def extrair_info_arquivo(nome_arquivo):
    match = FILENAME_PATTERN.match(nome_arquivo)
    if match:
        data_str, hora_str, operacao, modelo = match.groups()
        try:
            data_obj = datetime.strptime(data_str, "%Y%m%d").date()
            hora_obj = datetime.strptime(hora_str, "%H%M").time()
            return {
                "data_arquivo": data_obj.strftime("%d/%m/%Y"),
                "hora_arquivo": hora_obj.strftime("%H:%M"),
                "operacao": operacao,
                "modelo": modelo,
                "ano": data_obj.year,
                "mes": data_obj.month,
                "data_completa_obj": datetime.combine(data_obj, hora_obj) # Para ordenação
            }
        except ValueError:
            pass # Falha na conversão de data/hora, retorna None
    return None

# Função para listar arquivos CSV e extrair informações
@st.cache_data(ttl=300) # Cache para não reprocessar a cada interação
def listar_arquivos_csv():
    caminhos_arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    todos_arquivos_info = []

    for caminho in caminhos_arquivos:
        nome_arquivo = os.path.basename(caminho)
        info = extrair_info_arquivo(nome_arquivo)
        if info:
            info["caminho"] = caminho
            info["nome_arquivo"] = nome_arquivo
            info["data_modificacao"] = datetime.fromtimestamp(os.path.getmtime(caminho))
            todos_arquivos_info.append(info)

    # Ordena os arquivos pelo mais recente (data_completa_obj)
    todos_arquivos_info.sort(key=lambda x: x["data_completa_obj"], reverse=True)
    return todos_arquivos_info

# Função para carregar um CSV específico
@st.cache_data(ttl=60) # Cache para não recarregar o mesmo CSV frequentemente
def carregar_csv_caminho(caminho_arquivo):
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', decimal=',')
        # Converte a coluna 'DateTime' para datetime se existir
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
            df = df.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

# Função para exibir cards de métricas
def exibir_card(titulo, valor, unidade="", icone="bi bi-info-circle", cor_icone="#0d6efd", cor_borda="#0d6efd"):
    st.markdown(
        f"""
        <div class="ft-card" style="border-left: 4px solid {cor_borda};">
            <i class="{icone} ft-card-icon" style="color: {cor_icone};"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Função para mostrar valor com tratamento de N/D
def mostra_valor(df, coluna):
    if df is None or df.empty or coluna not in df.columns:
        return "N/D"
    valor = df[coluna].iloc[-1] # Pega o último valor da coluna
    if pd.isna(valor):
        return "N/D"
    return f"{valor:.2f}".replace('.', ',') # Formata para 2 casas decimais e usa vírgula

# Função para gerar PDF
def gerar_pdf(df, info_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(
        'Custom',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=6,
    )

    elements = []
    elements.append(Paragraph(f"<b>Relatório de Dados - {info_arquivo['nome_arquivo']}</b>", styles['h2']))
    elements.append(Paragraph(f"<b>Modelo:</b> {info_arquivo['modelo']} | <b>OP:</b> {info_arquivo['operacao']} | <b>Data:</b> {info_arquivo['data_arquivo']} | <b>Hora:</b> {info_arquivo['hora_arquivo']}", custom_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Converte DataFrame para lista de listas para a tabela do PDF
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Layout do Streamlit
# -------------------------------------------------

# Logo da Fromtherm (substitua pelo caminho real da sua logo se tiver uma)
# st.image("caminho/para/sua/logo_fromtherm.png", width=150) # Descomente e ajuste se tiver logo

st.markdown("<h1 class='main-title'>Máquina de Teste Fromtherm</h1>", unsafe_allow_html=True)

# --- Barra Lateral para Filtros ---
st.sidebar.header("Filtros de Históricos")
todos_arquivos_info = listar_arquivos_csv()

# Extrair opções únicas para os filtros
modelos_disponiveis = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info])))
anos_disponiveis = sorted(list(set([arq["ano"] for arq in todos_arquivos_info])))
meses_disponiveis = sorted(list(set([arq["mes"] for arq in todos_arquivos_info])))
operacoes_disponiveis = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info])))

filtro_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_disponiveis)
filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_disponiveis)
filtro_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_disponiveis, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos")
filtro_operacao = st.sidebar.selectbox("Operação", ["Todos"] + operacoes_disponiveis)

# Aplicar filtros
arquivos_filtrados = todos_arquivos_info
if filtro_modelo != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["modelo"] == filtro_modelo]
if filtro_ano != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["ano"] == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["mes"] == filtro_mes]
if filtro_operacao != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["operacao"] == filtro_operacao]

# --- Abas Principais ---
tab1, tab2 = st.tabs(["Dashboard", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Última Leitura")

    if arquivos_filtrados:
        info_ultimo_arquivo = arquivos_filtrados[0] # O mais recente dos filtrados
        df_ultimo = carregar_csv_caminho(info_ultimo_arquivo["caminho"])

        if not df_ultimo.empty:
            ultima_linha = df_ultimo.iloc[-1]
            st.markdown(
                f"**Modelo:** {info_ultimo_arquivo['modelo']} | "
                f"**OP:** {info_ultimo_arquivo['operacao']} | "
                f"**Data:** {info_ultimo_arquivo['data_arquivo']} | "
                f"**Hora:** {info_ultimo_arquivo['hora_arquivo']}"
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                exibir_card("T-Ambiente", mostra_valor(df_ultimo, "Ambiente"), "°C", "bi bi-thermometer-half")
            with col2:
                exibir_card("T-Entrada", mostra_valor(df_ultimo, "Entrada"), "°C", "bi bi-arrow-down-circle")
            with col3:
                exibir_card("T-Saída", mostra_valor(df_ultimo, "Saída"), "°C", "bi bi-arrow-up-circle", "red", "red")
            with col4:
                exibir_card("DIF", mostra_valor(df_ultimo, "DeltaT"), "°C", "bi bi-arrow-down-up")

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                exibir_card("Tensão", mostra_valor(df_ultimo, "Tensao"), "V", "bi bi-lightning-charge")
            with col6:
                exibir_card("Corrente", mostra_valor(df_ultimo, "Corrente"), "A", "bi bi-lightning")
            with col7:
                exibir_card("kcal/h", mostra_valor(df_ultimo, "Kcal_h"), "", "bi bi-fire")
            with col8:
                exibir_card("Vazão", mostra_valor(df_ultimo, "Vazao"), "L/min", "bi bi-water")

            col9, col10 = st.columns(2)
            with col9:
                exibir_card("kW Aquecimento", mostra_valor(df_ultimo, "KWAquecimento"), "kW", "bi bi-sun")
            with col10:
                exibir_card("kW Consumo", mostra_valor(df_ultimo, "KWConsumo"), "kW", "bi bi-power")

            # Card para COP
            st.markdown("---")
            st.subheader("Performance")
            col_cop, _, _, _ = st.columns(4) # Usar colunas para centralizar ou alinhar
            with col_cop:
                exibir_card("COP", mostra_valor(df_ultimo, "COP"), "", "bi bi-graph-up")

        else:
            st.info("Não foi possível carregar a última leitura do arquivo selecionado ou o arquivo está vazio.")
    else:
        st.info("Nenhum histórico encontrado com os filtros aplicados para a última leitura.")

    st.markdown("---")
    st.header("Históricos Disponíveis")

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado na pasta de dados com os filtros aplicados.")
    else:
        for arq in arquivos_filtrados:
            with st.expander(f"{arq['nome_arquivo']} (Modelo: {arq['modelo']}, OP: {arq['operacao']}, Data: {arq['data_arquivo']} {arq['hora_arquivo']})", expanded=False):
                st.write(f"Caminho: {arq['caminho']}")
                st.write(f"Data modificação: {arq['data_modificacao'].strftime('%d/%m/%Y %H:%M:%S')}")

                df_exibir = carregar_csv_caminho(arq['caminho'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    # Botões de download
                    nome_base = f"Maquina_{arq['modelo']}_{arq['operacao']}_{arq['data_arquivo'].replace('/', '')}_{arq['hora_arquivo'].replace(':', '')}"
                    nome_pdf = f"{nome_base}.pdf"
                    nome_excel = f"{nome_base}.xlsx"

                    # Gerar PDF
                    pdf_buffer = gerar_pdf(df_exibir, arq)
                    st.download_button(
                        label="Baixar como PDF",
                        data=pdf_buffer,
                        file_name=nome_pdf,
                        mime="application/pdf",
                        key=f"download_pdf_{arq['nome_arquivo']}"
                    )

                    # Gerar Excel
                    excel_buffer = BytesIO()
                    df_exibir.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="Baixar como Excel",
                        data=excel_buffer,
                        file_name=nome_excel,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_excel_{arq['nome_arquivo']}"
                    )
                else:
                    st.warning("Não foi possível exibir o conteúdo deste arquivo CSV ou ele está vazio.")

with tab2:
    st.header("Crie Seu Gráfico")

    if not todos_arquivos_info:
        st.info("Nenhum dado disponível para gerar gráficos. Carregue arquivos CSV primeiro.")
    else:
        # Filtros para o gráfico (independentes dos filtros da sidebar)
        st.subheader("Selecione os Dados para o Gráfico")
        modelos_graf = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info])))
        ops_graf = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info])))
        anos_graf = sorted(list(set([arq["ano"] for arq in todos_arquivos_info])))
        meses_graf = sorted(list(set([arq["mes"] for arq in todos_arquivos_info])))

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            modelo_graf = st.selectbox("Modelo da Máquina", modelos_graf, key="graf_modelo")
        with col_graf2:
            op_graf = st.selectbox("Número da Operação (OP)", ops_graf, key="graf_op")

        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            ano_graf = st.selectbox("Ano", anos_graf, key="graf_ano")
        with col_graf4:
            mes_graf = st.selectbox("Mês", ["Todos"] + meses_graf, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos", key="graf_mes")

        # Encontrar o arquivo correspondente aos filtros do gráfico
        arquivo_para_grafico = None
        for arq in todos_arquivos_info:
            if (arq["modelo"] == modelo_graf and
                arq["operacao"] == op_graf and
                arq["ano"] == ano_graf and
                (mes_graf == "Todos" or arq["mes"] == mes_graf)):
                arquivo_para_grafico = arq
                break

        if arquivo_para_grafico is None:
            st.warning("Nenhum arquivo encontrado para a combinação de filtros selecionada para o gráfico.")
        else:
            st.info(f"Gerando gráfico para: {arquivo_para_grafico['nome_arquivo']}")
            df_graf = carregar_csv_caminho(arquivo_para_grafico["caminho"])

            if df_graf.empty:
                st.warning("O arquivo selecionado para o gráfico está vazio ou não pôde ser carregado.")
            else:
                # Opções de variáveis para o gráfico
                variaveis_opcoes = [
                    "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                    "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
                ]
                # Filtra apenas as colunas que realmente existem no DataFrame
                variaveis_opcoes = [v for v in variaveis_opcoes if v in df_graf.columns]

                vars_selecionadas = st.multiselect(
                    "Selecione uma ou mais variáveis para o gráfico:",
                    variaveis_opcoes,
                    default=["Ambiente", "Entrada", "Saída"],
                    key="graf_vars_selecionadas"
                )

                if not vars_selecionadas:
                    st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                else:
                    # Garante que apenas as colunas selecionadas e 'DateTime' sejam usadas
                    df_plot = df_graf[["DateTime"] + vars_selecionadas].copy()

                    # Melt o DataFrame para o formato longo, ideal para Plotly Express
                    df_melted = df_plot.melt(
                        id_vars="DateTime",
                        value_vars=vars_selecionadas,
                        var_name="Variável",
                        value_name="Valor",
                    )

                    fig = px.line(
                        df_melted,
                        x="DateTime",
                        y="Valor",
                        color="Variável",
                        title=f"Gráfico - Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{datetime(1, mes_graf, 1).strftime('%B') if mes_graf != 'Todos' else 'Todos os Meses'}",
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
                        "- Use o botão de **fullscreen** no gráfico para expandir.\n"
                        "- Use o ícone de **câmera** no gráfico para baixar como imagem (PNG).\n"
                        "- A imagem baixada pode ser compartilhada via WhatsApp, e-mail, etc., em qualquer dispositivo."
                    )
