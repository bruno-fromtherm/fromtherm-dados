
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
# 1. CONFIGURAÇÃO DA PÁGINA
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# 2. CSS PARA DASHBOARD ATRATIVO (Remoção do "0" e ajuste mobile)
# -------------------------------------------------
st.markdown("""
    <style>
    /* Esconder elementos estranhos do Streamlit e o "0" teimoso */
    header {visibility: hidden;}
    div[data-testid="stAppViewContainer"] > div:first-child span { display: none !important; }
    button[data-testid="stSidebarNavToggle"] { display: none !important; }
    summary { display: none !important; }

    .stApp { background-color: #f4f7f6; }

    /* Cabeçalho Principal */
    .main-header {
        color: #003366; font-size: 26px; font-weight: 800; text-align: center;
        padding: 15px; border-bottom: 4px solid #003366; margin-bottom: 25px;
        background-color: white; border-radius: 10px;
    }

    /* Estilo dos Cards (Dashboards) */
    .ft-card {
        background: white; border-radius: 12px; padding: 15px; text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 15px;
        border-top: 6px solid #003366; transition: 0.3s;
        display: flex; align-items: center; justify-content: center; flex-direction: column;
    }
    .ft-card:hover { transform: translateY(-5px); }
    .ft-icon { font-size: 35px; margin-bottom: 8px; display: block; color: #003366; }
    .ft-label { font-size: 12px; font-weight: 700; color: #666; text-transform: uppercase; }
    .ft-value { font-size: 20px; font-weight: 800; color: #003366; margin-top: 5px; }

    /* Cores dos Ícones (se necessário, mas o código usa bi- para Bootstrap Icons) */
    .azul { color: #007bff; }
    .vermelho { color: #dc3545; }
    .ouro { color: #ffc107; }
    .verde { color: #28a745; }

    /* Ajuste para Celulares */
    @media (max-width: 768px) {
        .ft-value { font-size: 16px; }
        .main-header { font-size: 20px; }
        .ft-icon { font-size: 30px; }
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. FUNÇÕES AUXILIARES
# -------------------------------------------------

# Função para exibir cards
def mostra_valor(label, value, unit, icon_class): # icon_class é agora apenas a classe do ícone
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon"><i class="{icon_class}"></i></span>
            <div class="ft-content">
                <div class="ft-label">{label}</div>
                <div class="ft-value">{value} {unit}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 3.1. CONFIGURAÇÃO DE DADOS E LEITURA DE ARQUIVOS
# Caminho para a pasta de dados (ajustado para o ambiente do Streamlit Cloud)
DATA_PATH = "dados_brutos/historico_L1" # Certifique-se que esta pasta existe no seu repositório

@st.cache_data(ttl=3600) # Cache para não recarregar os arquivos toda hora
def buscar_arquivos():
    arquivos_encontrados = []

    # Regex mais flexível e robusto para capturar as partes
    # Ele tenta capturar as partes, mas se uma parte não existir, o grupo será None.
    # Isso evita que o programa quebre com nomes de arquivo que não seguem o padrão exato.
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260306_0718_OP999_FTI378L_BR.csv
    # Ex: historico_L1_20260305_2340_OP8888_FTI240L_BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (data e hora seriam capturadas, op e modelo seriam None)

    # Novo regex:
    # ^historico_L1_ : Início do nome do arquivo
    # (?P<data>\d{8}) : Captura 8 dígitos para a data (YYYYMMDD)
    # _(?P<hora>\d{4}) : Captura 4 dígitos para a hora (HHMM)
    # (?:_OP(?P<operacao>\d+))? : Opcional: _OP seguido de 1 ou mais dígitos para a operação
    # (?:_(?P<modelo>[a-zA-Z0-9_]+))? : Opcional: _ seguido de 1 ou mais caracteres alfanuméricos ou underscore para o modelo
    # \.csv$ : Termina com .csv

    # A principal mudança é em (?P<modelo>[a-zA-Z0-9_]+) para incluir o underscore no modelo
    # e o (?:_OP(?P<operacao>\d+))? para garantir que OP seja capturado corretamente

    # Regex final para máxima flexibilidade
    # Captura data e hora obrigatoriamente. Operação e Modelo são opcionais e mais flexíveis.
    regex_padrao = re.compile(r"^historico_L1_(?P<data>\d{8})_(?P<hora>\d{4})(?:_OP(?P<operacao>[a-zA-Z0-9]+))?(?:_(?P<modelo>[a-zA-Z0-9_]+))?\.csv$")

    # Verifica se a pasta de dados existe
    if not os.path.exists(DATA_PATH):
        st.error(f"A pasta de dados '{DATA_PATH}' não foi encontrada. Por favor, verifique o caminho.")
        return []

    for root, _, files in os.walk(DATA_PATH):
        for nome_arquivo in files:
            if nome_arquivo.endswith(".csv"):
                match = regex_padrao.match(nome_arquivo)
                if match:
                    partes = match.groupdict()

                    data_str = partes.get('data')
                    hora_str = partes.get('hora')
                    operacao = partes.get('operacao', 'N/D') # Pega 'N/D' se não encontrar
                    modelo = partes.get('modelo', 'N/D')     # Pega 'N/D' se não encontrar

                    # Formata a data e hora
                    try:
                        data_obj = datetime.strptime(data_str, "%Y%m%d").date()
                        hora_obj = datetime.strptime(hora_str, "%H%M").time()
                        data_formatada = data_obj.strftime("%d/%m/%Y")
                        ano = data_obj.year
                        mes = data_obj.month
                    except (ValueError, TypeError):
                        st.warning(f"Erro ao formatar data/hora do arquivo: {nome_arquivo}. Ignorando.")
                        continue # Pula para o próximo arquivo se a data/hora for inválida

                    caminho_completo = os.path.join(root, nome_arquivo)
                    arquivos_encontrados.append({
                        'nome_arquivo': nome_arquivo,
                        'caminho_completo': caminho_completo,
                        'data_obj': data_obj,
                        'hora_obj': hora_obj,
                        'data_f': data_formatada,
                        'ano': ano,
                        'mes': mes,
                        'operacao': operacao,
                        'modelo': modelo
                    })
                else:
                    st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.")

    # Ordena os arquivos pelo nome (data e hora) para que a "última leitura" seja a mais recente
    arquivos_encontrados.sort(key=lambda x: (x['data_obj'], x['hora_obj']), reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=3600) # Cache para não recarregar o CSV toda hora
def carregar_csv(caminho_arquivo):
    try:
        # Tenta ler o CSV com o separador '|' e o quotechar padrão (")
        df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], encoding='utf-8', skipinitialspace=True)
    except pd.errors.ParserError:
        # Se falhar, tenta novamente sem esperar aspas duplas (quotechar=None)
        # Isso é comum quando o CSV tem caracteres que parecem aspas mas não são delimitadores
        try:
            df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], encoding='utf-8', skipinitialspace=True, quotechar='\0') # '\0' significa nenhum quotechar
        except Exception as e:
            st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
            return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

    # Remove colunas que são completamente vazias (geralmente as primeiras e últimas devido ao separador)
    df = df.dropna(axis=1, how='all')

    # Remove espaços em branco dos nomes das colunas
    df.columns = df.columns.str.strip()

    # Tenta converter colunas numéricas, tratando vírgulas e erros
    for col in df.columns:
        # Ignora colunas de data e hora para conversão numérica direta
        if col in ['Date', 'Time', 'DateTime']:
            continue

        # Tenta converter para numérico, tratando vírgulas como decimais e erros como NaN
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

        # Preenche NaN com 0 (ou outro valor padrão, se preferir)
        df[col] = df[col].fillna(0)

    # Combina 'Date' e 'Time' em uma única coluna 'DateTime'
    if 'Date' in df.columns and 'Time' in df.columns:
        try:
            # Garante que 'Date' e 'Time' são strings antes de combinar
            df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str), format='%Y/%m/%d %H:%M:%S', errors='coerce')
            # Remove linhas onde a conversão de DateTime falhou
            df = df.dropna(subset=['DateTime'])
        except Exception as e:
            st.warning(f"Erro ao combinar 'Date' e 'Time' em '{os.path.basename(caminho_arquivo)}': {e}")
            # Se a combinação falhar, ainda podemos usar o DataFrame, mas sem DateTime
            if 'DateTime' in df.columns:
                df = df.drop(columns=['DateTime'])

    return df

# -------------------------------------------------
# 4. GERAÇÃO DE RELATÓRIOS PDF E EXCEL
# -------------------------------------------------

def gerar_pdf(df, nome_arquivo_base):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
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
    elements.append(Paragraph(f"Relatório de Histórico - {nome_arquivo_base}", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Preparar dados para a tabela
    data = [
        [Paragraph(col, header_style) for col in df.columns]
    ]
    for _, row in df.iterrows():
        data.append([Paragraph(str(row[col]), cell_style) for col in df.columns])

    # Calcular largura das colunas
    num_cols = len(df.columns)
    table_width = landscape(A4)[0] - 2 * inch # Largura da página menos margens
    col_widths = [table_width / num_cols] * num_cols

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f4f7f6')), # Linhas de dados cinza claro
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def gerar_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Historico')
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# 5. LAYOUT DO DASHBOARD
# -------------------------------------------------

# Carrega todos os arquivos e metadados
todos_arquivos = buscar_arquivos()

# 5.1. BARRA LATERAL
with st.sidebar:
    st.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
    st.markdown("<h2 class='sidebar-title'>Filtros de Histórico</h2>", unsafe_allow_html=True)

    # Garante que as listas de opções não estejam vazias
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D'])))
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos])))
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos])))
    datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos])), reverse=True)
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D'])))

    # Adiciona "Todos" como opção padrão
    filtro_modelo = st.selectbox("Modelo", ["Todos"] + modelos_unicos)
    filtro_ano = st.selectbox("Ano", ["Todos"] + anos_unicos)
    filtro_mes = st.selectbox("Mês", ["Todos"] + meses_unicos)
    filtro_data = st.selectbox("Data", ["Todos"] + datas_unicas)
    filtro_operacao = st.selectbox("Operação", ["Todos"] + operacoes_unicas)

# 5.2. CONTEÚDO PRINCIPAL
st.markdown("<h1 class='main-header'>Dashboard de Teste de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

# Aplica os filtros
arquivos_filtrados = todos_arquivos
if filtro_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == filtro_modelo]
if filtro_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == filtro_mes]
if filtro_data != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == filtro_data]
if filtro_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == filtro_operacao]

# Exibe os cards de última leitura
st.subheader("Última Leitura Disponível")
if arquivos_filtrados:
    ultimo_arquivo = arquivos_filtrados[0] # O primeiro é o mais recente devido à ordenação
    df_ultima_leitura = carregar_csv(ultimo_arquivo['caminho_completo'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha para a última leitura

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            mostra_valor("Ambiente", f"{ultima_linha.get('ambiente', 'N/D'):.2f}", "°C", "bi-thermometer-half")
        with col2:
            mostra_valor("Entrada", f"{ultima_linha.get('entrada', 'N/D'):.2f}", "°C", "bi-arrow-down-circle")
        with col3:
            mostra_valor("Saída", f"{ultima_linha.get('saida', 'N/D'):.2f}", "°C", "bi-arrow-up-circle")
        with col4:
            mostra_valor("Diferença", f"{ultima_linha.get('dif', 'N/D'):.2f}", "°C", "bi-arrows-expand")
        with col5:
            mostra_valor("Tensão", f"{ultima_linha.get('tensao', 'N/D'):.2f}", "V", "bi-lightning-charge")
        with col6:
            mostra_valor("Corrente", f"{ultima_linha.get('corrente', 'N/D'):.2f}", "A", "bi-lightning")

        # Adicione mais cards conforme necessário
        col7, col8, col9, col10, col11, col12 = st.columns(6)
        with col7:
            mostra_valor("Kcal/h", f"{ultima_linha.get('kacl/h', 'N/D'):.2f}", "", "bi-fire")
        with col8:
            mostra_valor("Vazão", f"{ultima_linha.get('vazao', 'N/D'):.2f}", "L/min", "bi-water")
        with col9:
            mostra_valor("KW Aquecimento", f"{ultima_linha.get('kw aquecimento', 'N/D'):.2f}", "kW", "bi-sun")
        with col10:
            mostra_valor("KW Consumo", f"{ultima_linha.get('kw consumo', 'N/D'):.2f}", "kW", "bi-power")
        with col11:
            mostra_valor("COP", f"{ultima_linha.get('cop', 'N/D'):.2f}", "", "bi-graph-up")
        with col12:
            st.empty() # Coluna vazia para manter o layout
    else:
        st.info("Não foi possível carregar os dados da última leitura do arquivo selecionado.")
else:
    st.info("Nenhum histórico disponível para a última leitura com os filtros aplicados.")

st.markdown("---")

# Abas para Históricos e Gráficos
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Históricos Disponíveis")
    if arquivos_filtrados:
        for arquivo in arquivos_filtrados:
            expander_label = f"Máquina: {arquivo['modelo']} | Operação: {arquivo['operacao']} | Data: {arquivo['data_f']} | Hora: {arquivo['hora_obj'].strftime('%H:%M')}"
            with st.expander(expander_label):
                df_historico = carregar_csv(arquivo['caminho_completo'])
                if not df_historico.empty:
                    st.dataframe(df_historico, use_container_width=True)

                    # Botões de download
                    nome_base_download = f"Maquina_{arquivo['modelo']}_OP{arquivo['operacao']}_{arquivo['data_f'].replace('/', '-')}_{arquivo['hora_obj'].strftime('%Hh%M')}"

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        pdf_buffer = gerar_pdf(df_historico, nome_base_download)
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer,
                            file_name=f"{nome_base_download}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with col_dl2:
                        excel_buffer = gerar_excel(df_historico)
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_buffer,
                            file_name=f"{nome_base_download}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para o histórico: {arquivo['nome_arquivo']}")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico")

    # Filtros específicos para o gráfico (para selecionar um único histórico)
    st.markdown("Selecione um histórico específico para gerar o gráfico:")

    # Garante que as listas de opções não estejam vazias para os filtros do gráfico
    modelos_grafico = sorted(list(set([a['modelo'] for a in arquivos_filtrados if a['modelo'] != 'N/D'])))
    operacoes_grafico = sorted(list(set([a['operacao'] for a in arquivos_filtrados if a['operacao'] != 'N/D'])))
    datas_grafico = sorted(list(set([a['data_f'] for a in arquivos_filtrados])), reverse=True)

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        filtro_modelo_grafico = st.selectbox("Modelo do Gráfico", ["Selecione"] + modelos_grafico, key="mod_graf")
    with col_g2:
        filtro_operacao_grafico = st.selectbox("Operação do Gráfico", ["Selecione"] + operacoes_grafico, key="op_graf")
    with col_g3:
        filtro_data_grafico = st.selectbox("Data do Gráfico", ["Selecione"] + datas_grafico, key="data_graf")

    arquivo_para_grafico = None
    if filtro_modelo_grafico != "Selecione" and filtro_operacao_grafico != "Selecione" and filtro_data_grafico != "Selecione":
            for arquivo in arquivos_filtrados:
                if (arquivo['modelo'] == filtro_modelo_grafico and
                    arquivo['operacao'] == filtro_operacao_grafico and
                    arquivo['data_f'] == filtro_data_grafico):
                    arquivo_para_grafico = arquivo
                    break

        if arquivo_para_grafico:
            df_grafico = carregar_csv(arquivo_para_grafico['caminho_completo'])
            if not df_grafico.empty and 'DateTime' in df_grafico.columns:
                # Lista de variáveis numéricas para o gráfico (excluindo Date, Time, DateTime)
                numeric_cols_for_plot = df_grafico.select_dtypes(include=['number']).columns.tolist()
                numeric_cols_for_plot = [col for col in numeric_cols_for_plot if col not in ['Date', 'Time']]

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