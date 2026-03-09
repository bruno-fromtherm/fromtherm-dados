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
# Caminho para a pasta onde os arquivos CSV estão localizados
# Baseado no caminho que você forneceu: C:\FROMTHERM_REPOS\fromtherm-dados\dados_brutos\historico_L1\IP_registro192.168.2.150
# Assumindo que o Streamlit app está na raiz de 'fromtherm-dados', o caminho relativo seria:
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog" # Adicionado 'datalog' conforme estrutura comum

@st.cache_data(ttl=5) # Cache para não reprocessar a cada interação
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
    # Grupo 3: Operação (OP seguido de 1 ou mais dígitos)
    # Grupo 4: Modelo (letras/números, pode incluir hífens ou outros caracteres comuns em modelos)
    # O regex agora é mais flexível para o modelo, permitindo mais caracteres.
    regex_padrao = re.compile(r"historico_L1_(\d{8})_(\d{4})_(OP\d+)_([A-Za-z0-9\-_]+)\.csv")

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
                    'hora': hora_str,
                    'operacao': operacao,
                    'modelo': modelo
                })
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido: '{nome_arquivo}'. Não foi possível extrair a data. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: '{nome_arquivo}'. Não segue o padrão esperado. Ignorando.")

    # Ordena os arquivos pelo mais recente primeiro
    arquivos_info.sort(key=lambda x: x['data_obj'], reverse=True)
    return arquivos_info

@st.cache_data(ttl=5) # Cache para não reprocessar o CSV a cada interação
def carregar_csv(caminho_arquivo):
    try:
        # Tenta ler o CSV com o separador '|' e o quotechar padrão (")
        df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], encoding='utf-8', skipinitialspace=True)
    except pd.errors.ParserError:
        # Se falhar, tenta novamente, mas sem esperar aspas duplas
        # Isso resolve o erro "'|' expected after '"'" se não houver aspas no CSV
        try:
            df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], encoding='utf-8', skipinitialspace=True, quotechar='\0') # quotechar='\0' desabilita o tratamento de aspas
        except Exception as e:
            st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

    # Limpeza de colunas: remove colunas vazias que podem surgir do separador '|' no início/fim
    df = df.dropna(axis=1, how='all')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')] # Remove colunas 'Unnamed'

    # Limpa espaços em branco dos nomes das colunas
    df.columns = df.columns.str.strip()

    # Converte colunas numéricas, tratando vírgulas e zeros à esquerda
    colunas_numericas = ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']
    for col in colunas_numericas:
        if col in df.columns:
            # Substitui vírgula por ponto e tenta converter para numérico, preenchendo erros com 0
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            # Para 'vazao', que pode ter 00000, garantir que seja int se for o caso
            if col == 'vazao':
                df[col] = df[col].astype(int)

    return df

# Função para gerar PDF
def gerar_pdf(df, info_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para o título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=18,
        leading=22,
        alignment=1, # Centro
        spaceAfter=12,
        textColor=colors.HexColor('#003366')
    )

    # Estilo para subtítulos/informações
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['h2'],
        fontSize=12,
        leading=14,
        alignment=0, # Esquerda
        spaceAfter=6,
        textColor=colors.HexColor('#333333')
    )

    elements = []
    elements.append(Paragraph(f"Relatório de Histórico - Máquina {info_arquivo['modelo']}", title_style))
    elements.append(Paragraph(f"Operação: {info_arquivo['operacao']}", subtitle_style))
    elements.append(Paragraph(f"Data: {info_arquivo['data_f']} | Hora: {info_arquivo['hora']}", subtitle_style))
    elements.append(Spacer(1, 12))

    # Preparar dados para a tabela
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)

    # Estilo da tabela
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f8ff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# 4. LAYOUT DO DASHBOARD
# -------------------------------------------------

st.markdown('<div class="main-header">Monitoramento de Máquinas Fromtherm</div>', unsafe_allow_html=True)

# Busca todos os arquivos disponíveis
arquivos_disponiveis = buscar_arquivos()

# Cria os filtros na barra lateral
st.sidebar.header("Filtros de Busca")

# Extrai opções únicas para os filtros
modelos_unicos = sorted(list(set([a['modelo'] for a in arquivos_disponiveis])))
anos_unicos = sorted(list(set([a['ano'] for a in arquivos_disponiveis])), reverse=True)
meses_unicos = sorted(list(set([a['mes'] for a in arquivos_disponiveis])), reverse=True)
operacoes_unicas = sorted(list(set([a['operacao'] for a in arquivos_disponiveis])))

# Adiciona "Todos" como opção padrão
sel_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
sel_operacao = st.sidebar.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
sel_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
sel_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos")

# Filtra os arquivos com base nas seleções
arquivos_filtrados = arquivos_disponiveis
if sel_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == sel_modelo]
if sel_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == sel_operacao]
if sel_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == sel_ano]
if sel_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == sel_mes]

# Tenta carregar o arquivo mais recente para os cards de última leitura
df_ultima_leitura = pd.DataFrame()
if arquivos_filtrados:
    arquivo_mais_recente = arquivos_filtrados[0] # Já estão ordenados pelo mais recente
    df_ultima_leitura = carregar_csv(arquivo_mais_recente['caminho'])

# Exibe os cards de última leitura
st.subheader("Última Leitura Registrada")
if not df_ultima_leitura.empty:
    ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha do DataFrame

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    with col1: mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", 'bi-thermometer-half')
    with col2: mostra_valor("Entrada", f"{ultima_linha['entrada']:.2f}", "°C", 'bi-arrow-down-circle')
    with col3: mostra_valor("Saída", f"{ultima_linha['saida']:.2f}", "°C", 'bi-arrow-up-circle')
    with col4: mostra_valor("Dif", f"{ultima_linha['dif']:.2f}", "°C", 'bi-arrow-down-up')
    with col5: mostra_valor("Tensão", f"{ultima_linha['tensao']:.1f}", "V", 'bi-lightning-charge')
    with col6: mostra_valor("Corrente", f"{ultima_linha['corrente']:.1f}", "A", 'bi-lightning')
    with col7: mostra_valor("Vazão", f"{ultima_linha['vazao']:.0f}", "L/min", 'bi-droplet') # Vazão como inteiro
else:
    st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")

st.markdown("---") # Separador visual

# Abas para Históricos e Gráficos
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Históricos Disponíveis")
    if arquivos_filtrados:
        for i, arquivo_info in enumerate(arquivos_filtrados):
            with st.expander(f"**{arquivo_info['modelo']}** - Operação: **{arquivo_info['operacao']}** - Data: **{arquivo_info['data_f']}** - Hora: **{arquivo_info['hora']}**"):
                df_exibir = carregar_csv(arquivo_info['caminho'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        csv_buffer = BytesIO()
                        df_exibir.to_csv(csv_buffer, index=False, sep=';', decimal=',') # Salva como CSV com ; e ,
                        st.download_button(
                            label="Baixar como CSV",
                            data=csv_buffer.getvalue(),
                            file_name=f"{arquivo_info['nome_arquivo'].replace('.csv', '')}_export.csv",
                            mime="text/csv",
                            key=f"download_csv_{i}"
                        )
                    with col_dl2:
                        pdf_buffer = gerar_pdf(df_exibir, arquivo_info)
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{arquivo_info['nome_arquivo'].replace('.csv', '')}_relatorio.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{i}"
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados do arquivo '{arquivo_info['nome_arquivo']}'. Verifique o arquivo.")
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