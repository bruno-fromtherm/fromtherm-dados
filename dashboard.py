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
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .ft-icon {
        font-size: 28px;
        margin-right: 12px;
        color: #0d6efd;
    }
    .ft-content {
        flex-grow: 1;
    }
    .ft-label {
        font-size: 11px;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .ft-value {
        font-size: 18px;
        color: #343a40;
        font-weight: 700;
    }

    /* Estilo para os botões de download */
    .stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #0d6efd;
        color: #0d6efd;
        background-color: #e9f0ff;
        padding: 8px 12px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stDownloadButton > button:hover {
        background-color: #0d6efd;
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Estilo para abas */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: 600;
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

# -------------------------------------------------
# Funções Auxiliares
# -------------------------------------------------

# Função para exibir cards
def mostra_valor(label, value, unit, icon):
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon">{icon}</span>
            <div class="ft-content">
                <div class="ft-label">{label}</div>
                <div class="ft-value">{value} {unit}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 3. CONFIGURAÇÃO DE DADOS
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=5)
def buscar_arquivos():
    if not os.path.exists(DADOS_DIR):
        st.error(f"Diretório de dados não encontrado: {DADOS_DIR}")
        return []

    caminhos_csv = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    arquivos_info = []

    # Regex aprimorado para capturar as partes do nome do arquivo
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Grupo 1: Data (YYYYMMDD)
    # Grupo 2: Hora (HHMM)
    # Grupo 3: Operação (OPXXX)
    # Grupo 4: Modelo (FTXXX ou similar)
    # O último grupo (modelo) pode ser mais flexível
    regex_padrao = re.compile(r"historico_L1_(\d{8})_(\d{4})_(OP\d{3})_([A-Za-z0-9]+)\.csv")

    for caminho in caminhos_csv:
        nome_arquivo = os.path.basename(caminho)
        match = regex_padrao.match(nome_arquivo)

        if match:
            data_str, hora_str, operacao, modelo = match.groups()

            try:
                data_obj = datetime.strptime(data_str, "%Y%m%d").date()
                data_formatada = data_obj.strftime("%d/%m/%Y")

                arquivos_info.append({
                    'caminho': caminho,
                    'nome_arquivo': nome_arquivo,
                    'data_obj': data_obj,
                    'data_f': data_formatada,
                    'ano': data_obj.year,
                    'mes': data_obj.month,
                    'operacao': operacao,
                    'modelo': modelo
                })
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não foi possível extrair a data. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.")

    return sorted(arquivos_info, key=lambda x: x['data_obj'], reverse=True)

@st.cache_data(ttl=5)
def carregar_csv(caminho_arquivo):
    try:
        # Lê o arquivo, pulando a segunda linha (que contém '---|---')
        # Usa 'sep=|' para o separador pipe
        # Usa 'skipinitialspace=True' para lidar com espaços após o separador
        # Usa 'engine='python'' para garantir que o separador de múltiplas letras funcione
        df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], skipinitialspace=True, engine='python')

        # Remove a primeira e última coluna que são vazias devido ao separador '|' no início e fim
        df = df.iloc[:, 1:-1]

        # Remove espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Converte colunas numéricas, tratando erros e valores como '000.0'
        for col in ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']:
            if col in df.columns:
                # Converte para numérico, tratando vírgulas como decimais e forçando float
                df[col] = df[col].str.replace(',', '.', regex=False).astype(float, errors='coerce')
                # Substitui NaN por 0 após a conversão
                df[col] = df[col].fillna(0)

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

# Funções para gerar PDF e Excel
def gerar_pdf(df, nome_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesizes=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para o título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=18,
        alignment=1, # Centro
        spaceAfter=14,
        textColor=colors.HexColor('#003366')
    )

    # Estilo para o cabeçalho da tabela
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1, # Centro
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )

    # Estilo para o conteúdo da tabela
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=7,
        alignment=1, # Centro
        textColor=colors.black
    )

    elements = []
    elements.append(Paragraph(f"Relatório de Dados - {nome_arquivo.replace('.csv', '')}", title_style))
    elements.append(Spacer(1, 0.2 * 2.54 * 72)) # 0.2cm spacer

    # Preparar dados para a tabela
    data = [Paragraph(col, header_style) for col in df.columns]
    for _, row in df.iterrows():
        data.extend([Paragraph(str(row[col]), cell_style) for col in df.columns])

    num_cols = len(df.columns)
    table_data = [data[i:i + num_cols] for i in range(0, len(data), num_cols)]

    # Calcular largura das colunas (distribuir igualmente)
    col_widths = [landscape(A4)[0] / num_cols for _ in range(num_cols)]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')), # Linhas alternadas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def gerar_excel(df, nome_arquivo):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
        # Opcional: Auto-ajustar largura das colunas no Excel
        worksheet = writer.sheets['Dados']
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Layout do Streamlit
# -------------------------------------------------

st.markdown('<h1 class="main-title">Monitoramento de Máquinas Fromtherm</h1>', unsafe_allow_html=True)

# Sidebar para filtros
st.sidebar.header("Filtros de Busca")

arquivos_disponiveis = buscar_arquivos()

if arquivos_disponiveis:
    modelos_unicos = sorted(list(set([a['modelo'] for a in arquivos_disponiveis])))
    operacoes_unicas = sorted(list(set([a['operacao'] for a in arquivos_disponiveis])))
    anos_unicos = sorted(list(set([a['ano'] for a in arquivos_disponiveis])), reverse=True)
    meses_unicos = sorted(list(set([a['mes'] for a in arquivos_disponiveis])), reverse=True)
    datas_unicas = sorted(list(set([a['data_f'] for a in arquivos_disponiveis])), reverse=True)

    filtro_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
    filtro_operacao = st.sidebar.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
    filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
    filtro_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos)
    filtro_data = st.sidebar.selectbox("Data", ["Todos"] + datas_unicas)

    # Aplica os filtros
    arquivos_filtrados = arquivos_disponiveis
    if filtro_modelo != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == filtro_modelo]
    if filtro_operacao != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == filtro_operacao]
    if filtro_ano != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == filtro_ano]
    if filtro_mes != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == filtro_mes]
    if filtro_data != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == filtro_data]

    # Exibe os cards de última leitura apenas se houver arquivos filtrados
    if arquivos_filtrados:
        # Pega o arquivo mais recente entre os filtrados
        arquivo_mais_recente = max(arquivos_filtrados, key=lambda x: x['data_obj'])
        df_ultima_leitura = carregar_csv(arquivo_mais_recente['caminho'])

        if not df_ultima_leitura.empty:
            ultima_linha = df_ultima_leitura.iloc[-1]

            st.subheader(f"Última Leitura ({arquivo_mais_recente['data_f']} {ultima_linha['Time']})")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mostra_valor("Temperatura Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", '<i class="bi bi-thermometer-half"></i>')
            with col2:
                mostra_valor("Temperatura Entrada", f"{ultima_linha['entrada']:.2f}", "°C", '<i class="bi bi-arrow-down-circle"></i>')
            with col3:
                mostra_valor("Temperatura Saída", f"{ultima_linha['saida']:.2f}", "°C", '<i class="bi bi-arrow-up-circle"></i>')
            with col4:
                mostra_valor("Diferença Temp.", f"{ultima_linha['dif']:.2f}", "°C", '<i class="bi bi-arrows-expand"></i>')

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                mostra_valor("Tensão", f"{ultima_linha['tensao']:.1f}", "V", '<i class="bi bi-lightning-charge"></i>')
            with col6:
                mostra_valor("Corrente", f"{ultima_linha['corrente']:.1f}", "A", '<i class="bi bi-ampere"></i>')
            with col7:
                mostra_valor("Vazão", f"{ultima_linha['vazao']:.0f}", "L/h", '<i class="bi bi-water"></i>')
            with col8:
                mostra_valor("COP", f"{ultima_linha['cop']:.1f}", "", '<i class="bi bi-graph-up"></i>')
        else:
            st.warning("Não foi possível carregar os dados do arquivo mais recente para a última leitura.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")

    st.markdown("---") # Separador visual

    # Abas para Históricos e Gráficos
    tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

    with tab1:
        st.subheader("Históricos Disponíveis")
        if arquivos_filtrados:
            for arquivo in arquivos_filtrados:
                with st.expander(f"**{arquivo['modelo']} - {arquivo['operacao']} - {arquivo['data_f']}**"):
                    df_exibir = carregar_csv(arquivo['caminho'])
                    if not df_exibir.empty:
                        st.dataframe(df_exibir, use_container_width=True)

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button(
                                label="Baixar como PDF",
                                data=gerar_pdf(df_exibir, arquivo['nome_arquivo']),
                                file_name=f"{arquivo['nome_arquivo'].replace('.csv', '')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        with col_dl2:
                            st.download_button(
                                label="Baixar como Excel",
                                data=gerar_excel(df_exibir, arquivo['nome_arquivo']),
                                file_name=f"{arquivo['nome_arquivo'].replace('.csv', '')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    else:
                        st.warning(f"Não foi possível carregar os dados para {arquivo['nome_arquivo']}.")
        else:
            st.info("Nenhum histórico disponível com os filtros aplicados.")

    with tab2:
        st.subheader("Crie Seu Gráfico Personalizado")
        if arquivos_disponiveis:
            # Filtros específicos para o gráfico (para selecionar um único arquivo)
            st.write("Selecione um histórico específico para gerar o gráfico:")

            modelos_unicos_g = sorted(list(set([a['modelo'] for a in arquivos_disponiveis])))
            sel_modelo_g = st.selectbox("Modelo", ["Selecione"] + modelos_unicos_g, key="modelo_grafico")

            operacoes_unicas_g = []
            if sel_modelo_g != "Selecione":
                operacoes_unicas_g = sorted(list(set([a['operacao'] for a in arquivos_disponiveis if a['modelo'] == sel_modelo_g])))
            sel_op_g = st.selectbox("Operação (OP)", ["Selecione"] + operacoes_unicas_g, key="op_grafico")

            datas_unicas_g = []
            if sel_modelo_g != "Selecione" and sel_op_g != "Selecione":
                datas_unicas_g = sorted(list(set([
                    a['data_f'] for a in arquivos_disponiveis if a['modelo'] == sel_modelo_g and a['operacao'] == sel_op_g
                ])), reverse=True)

            sel_data_g = st.selectbox("Data", ["Selecione"] + datas_unicas_g, key="data_grafico")

        if sel_modelo_g != "Selecione" and sel_op_g != "Selecione" and sel_data_g != "Selecione":
            # Encontra o arquivo correspondente aos filtros
            arquivo_para_grafico = next((a for a in arquivos_disponiveis if a['modelo'] == sel_modelo_g and a['operacao'] == sel_op_g and a['data_f'] == sel_data_g), None)

            if arquivo_para_grafico:
                df_grafico = carregar_csv(arquivo_para_grafico['caminho'])
                if not df_grafico.empty:
                    # Concatena Date e Time para criar um índice de tempo antes de identificar numéricas
                    df_grafico['DateTime'] = pd.to_datetime(df_grafico['Date'] + ' ' + df_grafico['Time'], errors='coerce')
                    df_grafico = df_grafico.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
                    df_grafico = df_grafico.sort_values('DateTime')

                    # Identifica colunas numéricas para o gráfico
                    numeric_cols_for_plot = [col for col in df_grafico.columns if pd.api.types.is_numeric_dtype(df_grafico[col]) and col not in ["Date", "Time", "DateTime"]]

                    if numeric_cols_for_plot:
                        variaveis_selecionadas = st.multiselect(
                            "Selecione as variáveis para o gráfico",
                            options=numeric_cols_for_plot,
                            default=numeric_cols_for_plot[:2] if len(numeric_cols_for_plot) >= 2 else numeric_cols_for_plot # Seleciona as duas primeiras por padrão
                        )

                        if variaveis_selecionadas:
                            fig = px.line(
                                df_grafico,
                                x="DateTime",
                                y=variaveis_selecionadas,
                                title=f"Gráfico de Variáveis para {arquivo_para_grafico['modelo']} - {arquivo_para_grafico['operacao']} em {arquivo_para_grafico['data_f']}",
                                labels={"DateTime": "Data e Hora", "value": "Valor"},
                                hovermode="x unified",
                                legend_title="Variáveis",
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            st.markdown(
                                "- Use o botão de **fullscreen** no gráfico (canto superior direito do gráfico) para tela cheia.\n"
                                "- Use o ícone de **câmera** para baixar como imagem (PNG).\n"
                                "- A imagem pode ser enviada por WhatsApp, e-mail, etc., em PC ou celular."
                            )
                        else:
                            st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                    else:
                        st.info("Nenhuma variável numérica encontrada para gerar gráficos neste histórico.")
                else:
                    st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados ou dados inválidos.")
            else:
                st.info("Selecione um Modelo, Operação e Data para gerar o gráfico.")
        else:
            st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados.")