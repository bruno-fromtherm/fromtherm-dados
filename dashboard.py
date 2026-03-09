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
    # Padrão de nome de arquivo mais flexível: historico_L1_YYYYMMDD_HHMM_OPX_MODELO.csv
    # O 'X' em OPX pode ter 1 ou mais dígitos. O MODELO pode ter letras e números.
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (este será ignorado ou terá campos N/D)
    # Ex: historico_L1_20260305_2143_OP0000_FT100H.csv

    # Regex para capturar:
    # L1 (opcional, para ser mais robusto)
    # Data (YYYYMMDD)
    # Hora (HHMM)
    # Operação (OP seguido de 1 ou mais dígitos)
    # Modelo (FT seguido de letras/numeros, ou qualquer string alfanumérica)

    # Regex mais robusto para capturar as partes, tornando a operação e o modelo mais flexíveis
    # e lidando com nomes de arquivo que podem não ter todas as partes.
    # Usamos grupos nomeados para facilitar a extração.

    # Padrão mais flexível para o nome do arquivo
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (data e hora seriam capturadas, op e modelo seriam None)

    # O regex tenta capturar as partes, mas se não encontrar, os grupos serão None.
    # Isso permite que o código continue sem quebrar, mesmo com nomes de arquivo "inválidos".

    # Regex:
    # historico_L1_ : prefixo
    # (?P<data>\d{8}) : 8 dígitos para a data (YYYYMMDD)
    # _(?P<hora>\d{4}) : 4 dígitos para a hora (HHMM)
    # (?:_OP(?P<operacao>\d+))? : Opcional: _OP seguido de 1 ou mais dígitos
    # (?:_(?P<modelo>[a-zA-Z0-9]+))? : Opcional: _ seguido de 1 ou mais caracteres alfanuméricos para o modelo
    # \.csv$ : termina com .csv

    # Novo regex para ser mais flexível e robusto
    # Ele tenta capturar as partes, mas se uma parte não existir, o grupo será None.
    # Isso evita que o programa quebre com nomes de arquivo que não seguem o padrão exato.

    # Regex mais flexível:
    # historico_L1_ (prefixo)
    # (?P<data>\d{8}) (data YYYYMMDD)
    # _(?P<hora>\d{4}) (hora HHMM)
    # (?:_OP(?P<operacao>\d+))? (grupo opcional para OP e números)
    # (?:_(?P<modelo>[a-zA-Z0-9]+))? (grupo opcional para modelo alfanumérico)
    # \.csv$ (extensão)

    # O '?:' torna o grupo não-capturante, e o '?' torna o grupo opcional.
    # Isso significa que se 'OP' ou 'modelo' não estiverem no nome, o regex ainda casa.

    # Padrão mais flexível para o nome do arquivo
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (data e hora seriam capturadas, op e modelo seriam None)

    # Regex para capturar as partes, tornando a operação e o modelo mais flexíveis
    # e lidando com nomes de arquivo que podem não ter todas as partes.
    # Usamos grupos nomeados para facilitar a extração.

    # Regex:
    # ^historico_L1_ # Início do nome do arquivo
    # (?P<data>\d{8}) # Captura 8 dígitos para a data (YYYYMMDD)
    # _(?P<hora>\d{4}) # Captura 4 dígitos para a hora (HHMM)
    # (?:_OP(?P<operacao>\d+))? # Grupo opcional para OP seguido de 1 ou mais dígitos
    # (?:_(?P<modelo>[a-zA-Z0-9]+))? # Grupo opcional para _ seguido de 1 ou mais caracteres alfanuméricos para o modelo
    # \.csv$ # Fim do nome do arquivo

    # O '?:' torna o grupo não-capturante, e o '?' torna o grupo opcional.
    # Isso significa que se 'OP' ou 'modelo' não estiverem no nome, o regex ainda casa.

    # Regex final, mais robusto e flexível
    file_pattern = re.compile(r"^historico_L1_(?P<data>\d{8})_(?P<hora>\d{4})(?:_OP(?P<operacao>\d+))?(?:_(?P<modelo>[a-zA-Z0-9]+))?\.csv$")

    for root, _, files in os.walk(DATA_PATH):
        for filename in files:
            if filename.endswith(".csv"):
                match = file_pattern.match(filename)
                if match:
                    parts = match.groupdict()
                    try:
                        data_str = parts['data']
                        hora_str = parts['hora']

                        # Formatar data para exibição
                        data_formatada = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")

                        # Combinar data e hora para um timestamp
                        datetime_obj = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")

                        arquivos_encontrados.append({
                            "nome_arquivo": filename,
                            "caminho_completo": os.path.join(root, filename),
                            "data_raw": data_str,
                            "data_f": data_formatada,
                            "hora_raw": hora_str,
                            "operacao": parts.get('operacao', 'N/D'), # 'N/D' se não encontrado
                            "modelo": parts.get('modelo', 'N/D'),   # 'N/D' se não encontrado
                            "timestamp": datetime_obj
                        })
                    except Exception as e:
                        st.warning(f"Nome de arquivo CSV inválido: {filename}. Não foi possível extrair a data/hora/operação/modelo. Ignorando. Erro: {e}")
                else:
                    st.warning(f"Nome de arquivo CSV inválido: {filename}. Não segue o padrão esperado. Ignorando.")

    # Ordenar os arquivos pelo timestamp (mais recente primeiro)
    arquivos_encontrados.sort(key=lambda x: x['timestamp'], reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=3600) # Cache para não recarregar o CSV toda hora
def carregar_csv(caminho_arquivo):
    try:
        # Tenta ler com o separador '|' e quotechar padrão (")
        df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], encoding='utf-8', on_bad_lines='warn')

        # Remove colunas que são completamente vazias (geralmente as primeiras e últimas devido ao separador)
        df = df.dropna(axis=1, how='all')

        # Remove espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Tenta converter colunas numéricas, lidando com vírgulas e erros
        for col in df.columns:
            # Ignora colunas 'Date' e 'Time' para conversão numérica direta
            if col not in ['Date', 'Time']:
                # Substitui vírgulas por pontos para conversão para float
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                # Converte para numérico, forçando erros para NaN, depois preenche NaN com 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Combina 'Date' e 'Time' em uma única coluna 'DateTime'
        if 'Date' in df.columns and 'Time' in df.columns:
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            df = df.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
            df = df.set_index('DateTime').sort_index()

        return df

    except pd.errors.ParserError as e:
        st.error(f"Erro de parsing no CSV '{os.path.basename(caminho_arquivo)}': {e}. Tentando novamente sem quotechar.")
        try:
            # Segunda tentativa: Tenta ler sem esperar aspas duplas
            df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], encoding='utf-8', on_bad_lines='warn', quotechar='\0') # quotechar='\0' desabilita o tratamento de aspas

            # Remove colunas que são completamente vazias
            df = df.dropna(axis=1, how='all')
            df.columns = df.columns.str.strip()

            for col in df.columns:
                if col not in ['Date', 'Time']:
                    df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            if 'Date' in df.columns and 'Time' in df.columns:
                df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                df = df.dropna(subset=['DateTime'])
                df = df.set_index('DateTime').sort_index()

            return df
        except Exception as e_retry:
            st.error(f"Erro final ao carregar o CSV '{os.path.basename(caminho_arquivo)}': {e_retry}")
            return pd.DataFrame() # Retorna DataFrame vazio em caso de falha
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de falha

# -------------------------------------------------
# 4. LAYOUT DO DASHBOARD
# -------------------------------------------------

# Título principal
st.markdown('<div class="main-header">Dashboard de Testes de Máquinas Fromtherm</div>', unsafe_allow_html=True)

# Logo da Fromtherm na barra lateral
st.sidebar.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
st.sidebar.markdown("---")

# Carregar todos os arquivos CSV disponíveis
todos_arquivos = buscar_arquivos()

# Extrair opções únicas para os filtros
modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D'])))
anos_unicos = sorted(list(set([a['timestamp'].year for a in todos_arquivos])))
meses_unicos = sorted(list(set([a['timestamp'].month for a in todos_arquivos])))
datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos])))
operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D'])))

# -------------------------------------------------
# 5. FILTROS NA BARRA LATERAL
# -------------------------------------------------
st.sidebar.header("Filtros de Histórico")

filtro_modelo = st.sidebar.selectbox("Modelo da Máquina", ["Todos"] + modelos_unicos)
filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
filtro_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos")
filtro_data = st.sidebar.selectbox("Data Específica", ["Todas"] + datas_unicas)
filtro_operacao = st.sidebar.selectbox("Número da Operação", ["Todas"] + operacoes_unicas)

# Aplicar filtros
arquivos_filtrados = todos_arquivos
if filtro_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == filtro_modelo]
if filtro_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['timestamp'].year == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['timestamp'].month == filtro_mes]
if filtro_data != "Todas":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == filtro_data]
if filtro_operacao != "Todas":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == filtro_operacao]

# -------------------------------------------------
# 6. EXIBIÇÃO DOS CARDS DE ÚLTIMA LEITURA
# -------------------------------------------------
st.subheader("Última Leitura Registrada")

if arquivos_filtrados:
    ultimo_arquivo = arquivos_filtrados[0] # O primeiro é o mais recente devido à ordenação
    df_ultimo = carregar_csv(ultimo_arquivo['caminho_completo'])

    if not df_ultimo.empty:
        ultima_linha = df_ultimo.iloc[-1] # Pega a última linha do DataFrame

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            mostra_valor("T-Ambiente", f"{ultima_linha.get('ambiente', 'N/D'):.2f}", "°C", "bi-thermometer-half")
        with col2:
            mostra_valor("T-Entrada", f"{ultima_linha.get('entrada', 'N/D'):.2f}", "°C", "bi-arrow-down-circle")
        with col3:
            mostra_valor("T-Saída", f"{ultima_linha.get('saida', 'N/D'):.2f}", "°C", "bi-arrow-up-circle")
        with col4:
            mostra_valor("DIF", f"{ultima_linha.get('dif', 'N/D'):.2f}", "°C", "bi-arrows-expand")
        with col5:
            mostra_valor("Tensão", f"{ultima_linha.get('tensao', 'N/D'):.2f}", "V", "bi-lightning-charge")
        with col6:
            mostra_valor("Corrente", f"{ultima_linha.get('corrente', 'N/D'):.2f}", "A", "bi-lightning")

        col7, col8, col9, col10, col11 = st.columns(5)
        with col7:
            mostra_valor("Kcal/h", f"{ultima_linha.get('kacl/h', 'N/D'):.2f}", "", "bi-fire")
        with col8:
            mostra_valor("Vazão", f"{ultima_linha.get('vazao', 'N/D'):.2f}", "L/h", "bi-water")
        with col9:
            mostra_valor("kW Aquecimento", f"{ultima_linha.get('kw aquecimento', 'N/D'):.2f}", "kW", "bi-sun")
        with col10:
            mostra_valor("kW Consumo", f"{ultima_linha.get('kw consumo', 'N/D'):.2f}", "kW", "bi-power")
        with col11:
            mostra_valor("COP", f"{ultima_linha.get('cop', 'N/D'):.2f}", "", "bi-graph-up")
    else:
        st.info("Não foi possível carregar os dados do último histórico para exibir a última leitura.")
else:
    st.info("Nenhum histórico disponível com os filtros aplicados para exibir a última leitura.")

st.markdown("---")

# -------------------------------------------------
# 7. ABAS PRINCIPAIS
# -------------------------------------------------
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Históricos Disponíveis")
    if arquivos_filtrados:
        for i, arquivo_info in enumerate(arquivos_filtrados):
            expander_label = f"Arquivo: {arquivo_info['nome_arquivo']} (Modelo: {arquivo_info['modelo']}, Operação: {arquivo_info['operacao']}, Data: {arquivo_info['data_f']} {arquivo_info['hora_raw']})"
            with st.expander(expander_label):
                df_exibir = carregar_csv(arquivo_info['caminho_completo'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    # Botões de download
                    col_dl1, col_dl2 = st.columns(2)

                    # Formatar nome do arquivo para download
                    nome_base = f"Maquina_{arquivo_info['modelo']}_OP{arquivo_info['operacao']}_{arquivo_info['data_f'].replace('/', '')}_{arquivo_info['hora_raw']}hs"

                    with col_dl1:
                        # Download PDF
                        pdf_buffer = BytesIO()
                        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                        styles = getSampleStyleSheet()

                        # Estilo para o título do PDF
                        style_title = ParagraphStyle(
                            'Title',
                            parent=styles['h1'],
                            fontSize=16,
                            leading=20,
                            alignment=1, # CENTER
                            spaceAfter=12,
                            textColor=colors.HexColor('#003366')
                        )

                        # Estilo para o cabeçalho da tabela
                        style_header = ParagraphStyle(
                            'TableHeader',
                            parent=styles['Normal'],
                            fontSize=8,
                            leading=10,
                            alignment=1, # CENTER
                            textColor=colors.white
                        )

                        # Estilo para o conteúdo da tabela
                        style_body = ParagraphStyle(
                            'TableBody',
                            parent=styles['Normal'],
                            fontSize=7,
                            leading=9,
                            alignment=1, # CENTER
                            textColor=colors.black
                        )

                        elements = []
                        elements.append(Paragraph(f"Relatório de Dados - {arquivo_info['modelo']} - Operação {arquivo_info['operacao']}", style_title))
                        elements.append(Paragraph(f"Data: {arquivo_info['data_f']} Hora: {arquivo_info['hora_raw']}", styles['h3']))
                        elements.append(Spacer(1, 0.2 * 28.35)) # 0.2 cm

                        # Preparar dados para a tabela do PDF
                        data_pdf = [list(df_exibir.columns)] + df_exibir.values.tolist()

                        # Aplicar estilos aos cabeçalhos
                        header_data = [Paragraph(col, style_header) for col in df_exibir.columns]
                        table_data = [header_data] + [[Paragraph(str(cell), style_body) for cell in row] for row in df_exibir.values.tolist()]

                        table = Table(table_data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('FONTSIZE', (0, 1), (-1, -1), 7),
                            ('LEFTPADDING', (0, 0), (-1, -1), 2),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                            ('TOPPADDING', (0, 0), (-1, -1), 2),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ]))
                        elements.append(table)
                        doc.build(elements)

                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{nome_base}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{i}"
                        )

                    with col_dl2:
                        # Download Excel
                        excel_buffer = BytesIO()
                        df_exibir.to_excel(excel_buffer, index=False, engine='xlsxwriter')
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_buffer.getvalue(),
                            file_name=f"{nome_base}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_excel_{i}"
                        )
                else:
                    st.info(f"Não foi possível carregar os dados para o arquivo: {arquivo_info['nome_arquivo']}")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico")

    # Filtros para o gráfico (usando os mesmos dados de arquivos_filtrados)
    modelos_grafico = sorted(list(set([a['modelo'] for a in arquivos_filtrados if a['modelo'] != 'N/D'])))
    operacoes_grafico = sorted(list(set([a['operacao'] for a in arquivos_filtrados if a['operacao'] != 'N/D'])))
    datas_grafico = sorted(list(set([a['data_f'] for a in arquivos_filtrados])))

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        filtro_modelo_grafico = st.selectbox("Modelo para Gráfico", ["Selecione"] + modelos_grafico, key="modelo_grafico")
    with col_g2:
        filtro_operacao_grafico = st.selectbox("Operação para Gráfico", ["Selecione"] + operacoes_grafico, key="operacao_grafico")
    with col_g3:
        filtro_data_grafico = st.selectbox("Data para Gráfico", ["Selecione"] + datas_grafico, key="data_grafico")

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