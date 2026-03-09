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
    # Regex para capturar:
    # historico_L1_ : prefixo
    # (?P<data>\d{8}) : 8 dígitos para a data (YYYYMMDD)
    # _(?P<hora>\d{4}) : 4 dígitos para a hora (HHMM)
    # (?:_OP(?P<operacao>\d+))? : Opcional: _OP seguido de 1 ou mais dígitos
    # (?:_(?P<modelo>[a-zA-Z0-9]+))? : Opcional: _ seguido de 1 ou mais caracteres alfanuméricos para o modelo
    # \.csv$ : termina com .csv

    # Regex mais flexível e robusto para capturar as partes
    # Ele tenta capturar as partes, mas se uma parte não existir, o grupo será None.
    # Isso evita que o programa quebre com nomes de arquivo que não seguem o padrão exato.
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (data e hora seriam capturadas, op e modelo seriam None)
    # Ex: historico_L1_20260305_2143_OP0000_FT100H.csv

    # O '?' após cada grupo de captura torna-o opcional.
    # O (?:...) é um grupo não-capturante.
    # O (?P<name>...) é um grupo nomeado.

    # Regex atualizado para ser mais robusto
    # O padrão é: prefixo_DATA_HORA_OP(OPERAÇÃO)_MODELO.csv
    # Cada parte _OP(...) e _MODELO(...) é opcional.
    # O modelo pode ser qualquer sequência alfanumérica.

    # Novo regex para capturar as partes, tornando a operação e o modelo mais flexíveis
    # e lidando com nomes de arquivo que podem não ter todas as partes.
    # Usamos grupos nomeados para facilitar a extração.
    # A parte 'L1' é opcional no prefixo.

    # Regex mais flexível:
    # ^historico_(?:L\d_)?(?P<data>\d{8})_(?P<hora>\d{4})(?:_OP(?P<operacao>[a-zA-Z0-9]+))?(?:_(?P<modelo>[a-zA-Z0-9]+))?\.csv$
    # Explicação:
    # ^historico_ : Início da string com "historico_"
    # (?:L\d_)? : Opcional, grupo não-capturante para "L" seguido de um dígito e "_" (ex: L1_)
    # (?P<data>\d{8}) : Captura 8 dígitos para a data (YYYYMMDD)
    # _(?P<hora>\d{4}) : Captura 4 dígitos para a hora (HHMM)
    # (?:_OP(?P<operacao>[a-zA-Z0-9]+))? : Opcional, grupo não-capturante para "_OP" seguido da operação (alfanumérica)
    # (?:_(?P<modelo>[a-zA-Z0-9]+))? : Opcional, grupo não-capturante para "_" seguido do modelo (alfanumérica)
    # \.csv$ : Termina com ".csv"

    # Teste com os nomes de arquivo que você forneceu:
    # historico_L1_20260308_0939_OP987_FTA987BR.csv -> data, hora, operacao, modelo
    # historico_L1_20260307_TESTE_NOVO.csv -> data, hora (op e modelo seriam None)
    # historico_L1_20260305_2143_OP0000_FT100H.csv -> data, hora, operacao, modelo

    # O regex foi ajustado para ser mais flexível com o modelo e a operação, aceitando alfanuméricos.
    # O prefixo 'L1_' também foi tornado opcional.

    file_pattern = re.compile(r"^historico_(?:L\d_)?(?P<data>\d{8})_(?P<hora>\d{4})(?:_OP(?P<operacao>[a-zA-Z0-9]+))?(?:_(?P<modelo>[a-zA-Z0-9]+))?\.csv$")

    if os.path.exists(DATA_PATH):
        for root, _, files in os.walk(DATA_PATH):
            for file_name in files:
                match = file_pattern.match(file_name)
                if match:
                    data_raw = match.group('data')
                    hora_raw = match.group('hora')
                    operacao_raw = match.group('operacao') if match.group('operacao') else 'N/D'
                    modelo_raw = match.group('modelo') if match.group('modelo') else 'N/D'

                    try:
                        data_obj = datetime.strptime(data_raw, '%Y%m%d')
                        data_formatada = data_obj.strftime('%d/%m/%Y')
                        ano = data_obj.year
                        mes = data_obj.month
                    except ValueError:
                        st.warning(f"Nome de arquivo CSV inválido: {file_name}. Não foi possível extrair a data. Ignorando.")
                        continue # Pula para o próximo arquivo

                    caminho_completo = os.path.join(root, file_name)
                    arquivos_encontrados.append({
                        'nome_arquivo': file_name,
                        'caminho_completo': caminho_completo,
                        'data_raw': data_raw,
                        'hora_raw': hora_raw,
                        'data_f': data_formatada,
                        'ano': ano,
                        'mes': mes,
                        'operacao': operacao_raw,
                        'modelo': modelo_raw
                    })
                else:
                    st.warning(f"Nome de arquivo CSV inválido: {file_name}. Não segue o padrão esperado. Ignorando.")
    else:
        st.error(f"A pasta de dados '{DATA_PATH}' não foi encontrada. Por favor, verifique o caminho.")

    # Ordena os arquivos pelo nome (que contém data e hora) para ter a última leitura mais fácil
    arquivos_encontrados.sort(key=lambda x: x['nome_arquivo'], reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=3600) # Cache para não recarregar o CSV toda hora
def carregar_csv(caminho_completo):
    try:
        # Tenta ler com o separador '|' e o quotechar padrão (")
        df = pd.read_csv(caminho_completo, sep='|', skiprows=[1], encoding='utf-8')
    except pd.errors.ParserError:
        # Se falhar, tenta novamente, mas sem esperar aspas duplas (quotechar=None)
        # Isso é útil se alguns campos contêm aspas que não são delimitadores
        try:
            df = pd.read_csv(caminho_completo, sep='|', skiprows=[1], encoding='utf-8', quotechar='\0') # Use '\0' para desativar quotechar
        except Exception as e:
            st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_completo)}': {e}")
            return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

    # Remove colunas vazias que podem surgir do separador '|' no início/fim
    df = df.dropna(axis=1, how='all')

    # Limpa nomes das colunas (remove espaços em branco e o '|' extra)
    df.columns = df.columns.str.strip().str.replace('|', '', regex=False).str.strip()

    # Converte colunas 'Date' e 'Time' para datetime
    if 'Date' in df.columns and 'Time' in df.columns:
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y/%m/%d %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
    else:
        st.warning(f"Colunas 'Date' ou 'Time' não encontradas em {os.path.basename(caminho_completo)}. Gráficos podem não funcionar.")
        df['DateTime'] = pd.to_datetime(df.index, unit='s') # Cria um DateTime básico se não encontrar

    # Converte colunas numéricas, tratando vírgulas e zeros à esquerda
    numeric_cols = ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']
    for col in numeric_cols:
        if col in df.columns:
            # Substitui vírgula por ponto e tenta converter para float. Erros viram NaN.
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False).astype(float, errors='coerce')
            df[col] = df[col].fillna(0) # Preenche NaN com 0

    return df

# 3.2. GERAÇÃO DE PDF
def criar_pdf(df, nome_arquivo_base):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para o título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=18,
        spaceAfter=14,
        alignment=1, # Centro
        textColor=colors.HexColor('#003366')
    )

    # Estilo para o cabeçalho da tabela
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.white,
        alignment=1, # Centro
        fontName='Helvetica-Bold'
    )

    # Estilo para o conteúdo da tabela
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.black,
        alignment=1, # Centro
    )

    story = []
    story.append(Paragraph(f"Relatório de Histórico - {nome_arquivo_base}", title_style))
    story.append(Spacer(1, 0.2 * 28.35)) # 0.2 cm de espaço

    # Preparar dados para a tabela
    data = [Paragraph(col, header_style) for col in df.columns.tolist()]
    table_data = [data] # Adiciona o cabeçalho

    for index, row in df.iterrows():
        table_row = [Paragraph(str(row[col]), body_style) for col in df.columns.tolist()]
        table_data.append(table_row)

    # Estilo da tabela
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')), # Linhas alternadas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ])

    # Calcula a largura das colunas
    col_widths = [doc.width / len(df.columns)] * len(df.columns)

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(table_style)
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# 4. LAYOUT DO DASHBOARD
# -------------------------------------------------

st.markdown('<div class="main-header">Dashboard de Teste de Máquinas Fromtherm</div>', unsafe_allow_html=True)

# Barra lateral para filtros
st.sidebar.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
st.sidebar.header("Filtros de Históricos")

todos_arquivos = buscar_arquivos()

# Garante que as listas de opções para os filtros não quebrem se 'todos_arquivos' estiver vazio
modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D']))) if todos_arquivos else []
anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos]))) if todos_arquivos else []
meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos]))) if todos_arquivos else []
datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos]))) if todos_arquivos else []
operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D']))) if todos_arquivos else []


filtro_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
filtro_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos)
filtro_data = st.sidebar.selectbox("Data", ["Todas"] + datas_unicas)
filtro_operacao = st.sidebar.selectbox("Operação", ["Todas"] + operacoes_unicas)

# Aplica os filtros
arquivos_filtrados = []
for arquivo in todos_arquivos:
    match_modelo = (filtro_modelo == "Todos") or (arquivo['modelo'] == filtro_modelo)
    match_ano = (filtro_ano == "Todos") or (arquivo['ano'] == filtro_ano)
    match_mes = (filtro_mes == "Todos") or (arquivo['mes'] == filtro_mes)
    match_data = (filtro_data == "Todas") or (arquivo['data_f'] == filtro_data)
    match_operacao = (filtro_operacao == "Todas") or (arquivo['operacao'] == filtro_operacao)

    if match_modelo and match_ano and match_mes and match_data and match_operacao:
        arquivos_filtrados.append(arquivo)

# -------------------------------------------------
# 5. CARDS DE ÚLTIMA LEITURA
# -------------------------------------------------
st.subheader("Última Leitura Registrada")

if arquivos_filtrados:
    # Pega o arquivo mais recente (já ordenado por buscar_arquivos)
    ultimo_arquivo = arquivos_filtrados[0]
    df_ultima_leitura = carregar_csv(ultimo_arquivo['caminho_completo'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha do DataFrame

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
        with col2:
            mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-arrow-down-circle")
        with col3:
            mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-arrow-up-circle")
        with col4:
            mostra_valor("T-Diferença", f"{ultima_linha['dif']:.2f}", "°C", "bi-thermometer-sun")
        with col5:
            mostra_valor("Tensão", f"{ultima_linha['tensao']:.2f}", "V", "bi-lightning-charge")
        with col6:
            mostra_valor("Corrente", f"{ultima_linha['corrente']:.2f}", "A", "bi-lightning")

        st.markdown(f"""
            <div style="text-align: center; font-size: 14px; color: #666; margin-top: 10px;">
                Última atualização: {ultima_linha['DateTime'].strftime('%d/%m/%Y %H:%M:%S')}
                <br>Arquivo: {ultimo_arquivo['nome_arquivo']}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Não foi possível carregar os dados do último histórico para os cards.")
else:
    st.info("Nenhum histórico disponível para exibir a última leitura com os filtros aplicados.")

# -------------------------------------------------
# 6. ABAS DE NAVEGAÇÃO
# -------------------------------------------------
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Históricos Disponíveis")
    if arquivos_filtrados:
        for arquivo in arquivos_filtrados:
            with st.expander(f"**{arquivo['modelo']} - Operação {arquivo['operacao']} - {arquivo['data_f']} {arquivo['hora_raw']}**"):
                df_exibir = carregar_csv(arquivo['caminho_completo'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    nome_base_download = f"Maquina_{arquivo['modelo']}_OP{arquivo['operacao']}_{arquivo['data_f'].replace('/', '-')}_{arquivo['hora_raw']}hs"

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Botão de download CSV
                        csv_buffer = BytesIO()
                        df_exibir.to_csv(csv_buffer, index=False, sep=';', decimal=',', encoding='utf-8-sig')
                        st.download_button(
                            label="Baixar Planilha (CSV)",
                            data=csv_buffer.getvalue(),
                            file_name=f"{nome_base_download}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col_dl2:
                        # Botão de download PDF
                        pdf_buffer = criar_pdf(df_exibir, nome_base_download)
                        st.download_button(
                            label="Baixar Relatório (PDF)",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{nome_base_download}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para o arquivo: {arquivo['nome_arquivo']}")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico")
    if arquivos_filtrados:
        # Filtros para o gráfico
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
    else:
        st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados.")