import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from io import BytesIO, StringIO
import plotly.express as px
import re
import numpy as np # Importar numpy para np.nan

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# =========================
#  CSS GLOBAL (Tema Industrial e Responsividade)
# =========================
st.markdown(
    """
    <style>
    /* Fundo geral da página - Gradiente Industrial */
    .stApp {
        background: linear-gradient(to bottom, #001f3f, #000000); /* Azul Marinho Profundo para Preto */
        color: #e0e0e0; /* Cinza Gelo para texto padrão */
        font-family: 'Inter', 'Roboto', sans-serif; /* Tipografia moderna */
    }

    /* Container principal - Cartão translúcido com desfoque */
    .main > div {
        background-color: rgba(255, 255, 255, 0.05); /* Fundo branco translúcido */
        backdrop-filter: blur(10px); /* Efeito de desfoque */
        border-radius: 12px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2); /* Sombra mais pronunciada */
        border: 1px solid rgba(255, 255, 255, 0.1); /* Borda sutil */
        padding: 20px 30px 40px 30px; /* Ajusta padding */
        margin-top: 10px;
    }

    /* Título principal */
    h1 {
        color: #00bfff !important; /* Azul Neon para o título principal */
        font-weight: 800 !important;
        letter-spacing: 0.05em;
        text-shadow: 0 0 8px rgba(0, 191, 255, 0.5); /* Efeito de brilho */
    }

    /* Subtítulos e outros textos importantes */
    h2, h3, h4, h5, h6 {
        color: #00bfff !important; /* Azul Neon para subtítulos */
        font-weight: 600 !important;
    }
    p, label, .stMarkdown {
        color: #e0e0e0; /* Cinza Gelo para textos gerais */
    }

    /* Linha abaixo do título */
    h1 + div {
        border-bottom: 1px solid rgba(0, 191, 255, 0.3); /* Linha de destaque azul neon */
        margin-bottom: 15px;
        padding-bottom: 8px;
    }

    /* Sidebar com leve separação e tema escuro */
    section[data-testid="stSidebar"] {
        background-color: #001a33; /* Azul escuro para sidebar */
        border-right: 1px solid rgba(0, 191, 255, 0.2);
        color: #e0e0e0;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #003366; /* Botões da sidebar */
        color: #e0e0e0;
        border: 1px solid #00bfff;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #004080;
        border-color: #00ffff;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #003366;
        color: #e0e0e0;
        border: 1px solid #00bfff;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div > div > span {
        color: #e0e0e0;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div > div > div > div {
        background-color: #003366; /* Opções do selectbox */
        color: #e0e0e0;
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div > div > div > div:hover {
        background-color: #004080;
    }
    section[data-testid="stSidebar"] .stSelectbox > label {
        color: #00bfff; /* Rótulo do selectbox */
    }


    /* Esconder qualquer pequeno span/ícone no topo esquerdo
       que esteja causando o "0" indesejado */
    div[data-testid="stAppViewContainer"] > div:first-child span {
        font-size: 0px !important;
        color: transparent !important;
    }

    /* Estilo para os cards de métricas (mantendo o fundo translúcido) */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05); /* Fundo branco translúcido */
        backdrop-filter: blur(10px); /* Efeito de desfoque */
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1); /* Borda sutil */
    }
    .metric-card h4 {
        color: #00bfff; /* Azul Neon para o título da métrica */
        font-size: 1.1em;
        margin-bottom: 5px;
    }
    .metric-card .metric-value {
        font-size: 1.6em;
        font-weight: bold;
        color: #e0e0e0; /* Cinza Gelo para o valor */
        text-shadow: 0 0 5px rgba(255, 255, 255, 0.2);
    }
    .metric-card .temp-entrada-value {
        color: #00ffff; /* Azul Neon para T-Entrada */
        text-shadow: 0 0 8px rgba(0, 255, 255, 0.7);
    }
    .metric-card .temp-saida-value {
        color: #ff0000; /* Vermelho Vibrante para T-Saída */
        text-shadow: 0 0 8px rgba(255, 0, 0, 0.7);
    }
    .metric-card .metric-unit {
        font-size: 0.8em;
        color: #a0a0a0;
    }

    /* Estilo para os botões de arquivo */
    .stButton > button {
        width: 100%;
        background-color: #003366; /* Azul escuro */
        color: #e0e0e0;
        border: 1px solid #00bfff; /* Borda azul neon */
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 5px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #004080; /* Azul um pouco mais claro no hover */
        color: #00ffff; /* Texto azul neon no hover */
        border-color: #00ffff;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.5); /* Brilho no hover */
    }

    /* Estilo para a tabela de dados */
    .stDataFrame, .stTable {
        background-color: rgba(0, 0, 0, 0.1); /* Fundo escuro translúcido */
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stDataFrame div[data-testid="stTable"] div[role="rowheader"] div,
    .stDataFrame div[data-testid="stTable"] div[role="cell"] div {
        color: #e0e0e0; /* Cor do texto da tabela */
    }
    .stDataFrame div[data-testid="stTable"] div[role="columnheader"] div {
        color: #00bfff; /* Cor do cabeçalho da tabela */
        font-weight: bold;
    }

    /* Estilo para o multiselect de gráficos */
    .stMultiSelect > label {
        color: #00bfff; /* Rótulo do multiselect */
    }
    .stMultiSelect > div > div {
        background-color: #003366;
        color: #e0e0e0;
        border: 1px solid #00bfff;
    }
    .stMultiSelect > div > div > div > div > div {
        background-color: #003366; /* Opções do multiselect */
        color: #e0e0e0;
    }
    .stMultiSelect > div > div > div > div > div:hover {
        background-color: #004080;
    }
    .stMultiSelect .st-emotion-cache-1g62x7d { /* Cor do texto selecionado no multiselect */
        color: #e0e0e0;
    }
    .stMultiSelect .st-emotion-cache-1g62x7d:hover {
        color: #00ffff;
    }


    /* Mensagens de alerta e informação */
    .stAlert {
        background-color: rgba(0, 191, 255, 0.1); /* Fundo azul claro translúcido */
        color: #00bfff;
        border-left: 5px solid #00bfff;
        border-radius: 8px;
    }
    .stAlert > div > div > div > p {
        color: #e0e0e0 !important;
    }
    .stAlert > div > div > div > svg {
        color: #00bfff !important;
    }
    .stWarning {
        background-color: rgba(255, 165, 0, 0.1); /* Fundo laranja translúcido */
        color: #ffa500;
        border-left: 5px solid #ffa500;
        border-radius: 8px;
    }
    .stWarning > div > div > div > p {
        color: #e0e0e0 !important;
    }
    .stWarning > div > div > div > svg {
        color: #ffa500 !important;
    }
    .stError {
        background-color: rgba(255, 0, 0, 0.1); /* Fundo vermelho translúcido */
        color: #ff0000;
        border-left: 5px solid #ff0000;
        border-radius: 8px;
    }
    .stError > div > div > div > p {
        color: #e0e0e0 !important;
    }
    .stError > div > div > div > svg {
        color: #ff0000 !important;
    }


    /* Responsividade para Mobile */
    @media (max-width: 768px) {
        .main > div {
            padding: 10px 15px 20px 15px; /* Reduz padding em mobile */
        }
        h1 {
            font-size: 1.8em !important; /* Título menor em mobile */
            letter-spacing: 0.03em;
        }
        .metric-card {
            padding: 10px;
            margin-bottom: 8px;
        }
        .metric-card h4 {
            font-size: 1em;
        }
        .metric-card .metric-value {
            font-size: 1.4em;
        }
        /* Força o empilhamento de colunas em mobile */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.stPlotlyChart) {
            width: 100% !important;
            margin-bottom: 10px;
        }
        .stPlotlyChart {
            width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
#  Funções Auxiliares
# =========================

# Função para formatar números para o padrão brasileiro
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float, formata, e substitui . por ,
        formatted_value = f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted_value} {unit}".strip()
    except (ValueError, TypeError):
        return "N/D"

# Função para listar arquivos CSV
@st.cache_data(ttl=3600) # Cache por 1 hora
def listar_arquivos_csv(diretorio="."):
    caminho_completo = os.path.join(os.getcwd(), diretorio)
    arquivos_csv = glob.glob(os.path.join(caminho_completo, "*.csv"))

    lista_arquivos = []
    for arquivo_path in arquivos_csv:
        nome_arquivo = os.path.basename(arquivo_path)

        # Expressão regular mais flexível para capturar modelo e operação
        # Garante que OP seja seguido por dígitos e o final seja flexível
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", nome_arquivo)

        modelo = "N/D"
        operacao = "N/D"
        data_str = "N/D"
        hora_str = "N/D"
        data_obj = None

        if match:
            ano, mes, dia, hora_completa, operacao, modelo = match.groups()
            data_str = f"{dia}/{mes}/{ano}"
            hora_str = f"{hora_completa[:2]}:{hora_completa[2:]}"
            try:
                data_obj = datetime.strptime(f"{ano}-{mes}-{dia} {hora_completa[:2]}:{hora_completa[2:]}:00", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                data_obj = None

        lista_arquivos.append({
            "path": arquivo_path,
            "nome_arquivo": nome_arquivo,
            "modelo": modelo,
            "operacao": operacao,
            "data_str": data_str,
            "hora_str": hora_str,
            "data_obj": data_obj # Para ordenação
        })

    # Ordenar por data_obj, os N/D (None) vão para o final
    lista_arquivos.sort(key=lambda x: x['data_obj'] if x['data_obj'] is not None else datetime.min, reverse=True)

    return lista_arquivos

# Função para carregar e processar um arquivo CSV
@st.cache_data(ttl=600) # Cache por 10 minutos
def carregar_csv_caminho(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Encontrar a linha do cabeçalho e a linha de separação
        header_line_index = -1
        separator_line_index = -1
        for i, line in enumerate(lines):
            if re.match(r"\|\s*Date\s*\|\s*Time\s*\|", line, re.IGNORECASE):
                header_line_index = i
            if re.match(r"\|\s*---\s*\|\s*---\s*\|", line):
                separator_line_index = i
            if header_line_index != -1 and separator_line_index != -1:
                break

        if header_line_index == -1:
            st.error(f"Erro: Cabeçalho 'Date | Time | ...' não encontrado no arquivo '{os.path.basename(caminho_arquivo)}'.")
            return pd.DataFrame()

        # Filtrar as linhas de dados (após o separador, se existir)
        data_lines = []
        if separator_line_index != -1 and separator_line_index > header_line_index:
            data_lines = lines[separator_line_index + 1:]
        else: # Se não houver separador, assume que os dados começam após o cabeçalho
            data_lines = lines[header_line_index + 1:]

        # Remover linhas completamente vazias
        data_lines = [line for line in data_lines if line.strip()]

        # Adicionar o cabeçalho de volta ao início das linhas de dados
        processed_csv_content = [lines[header_line_index]] + data_lines

        # Juntar as linhas para formar uma string que pd.read_csv possa ler
        csv_string = "".join(processed_csv_content)

        # Usar StringIO para ler a string como um arquivo
        df = pd.read_csv(StringIO(csv_string), sep='|', skipinitialspace=True)

        # Remover a primeira e a última coluna que podem ser vazias devido ao separador '|'
        # Verifica se há colunas suficientes antes de tentar remover
        if df.shape[1] > 2:
            df = df.iloc[:, 1:-1]
        else:
            st.error(f"Erro: O arquivo '{os.path.basename(caminho_arquivo)}' não tem colunas suficientes após a leitura. Verifique o formato.")
            return pd.DataFrame()

        # Limpar espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Mapeamento de nomes de colunas (minúsculas/sem acento para padrão)
        column_mapping = {
            'ambiente': 'Ambiente',
            'entrada': 'Entrada',
            'saida': 'Saída',
            'dif': 'ΔT',
            'tensao': 'Tensão (V)',
            'corrente': 'Corrente (A)',
            'kacl/h': 'Kcal/h',
            'vazao': 'Vazão (L/h)',
            'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo',
            'cop': 'COP',
            'date': 'Date', # Garante que 'Date' e 'Time' sejam mapeadas
            'time': 'Time'
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Verificar se as colunas 'Date' e 'Time' existem após o mapeamento
        if 'Date' not in df.columns or 'Time' not in df.columns:
            st.error(f"Erro: Colunas 'Date' ou 'Time' não encontradas no arquivo '{os.path.basename(caminho_arquivo)}' após o mapeamento. Colunas encontradas: {df.columns.tolist()}")
            return pd.DataFrame()

        # Criar coluna DateTime
        df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
        df['Time'] = df['Time'].astype(str)

        # Tentar formatar com formato específico
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

        # Fallback para inferência se a maioria das datas falhar
        if df['DateTime'].isnull().sum() > len(df) / 2:
            st.warning(f"Aviso: Formato de data/hora '%Y-%m-%d %H:%M:%S' falhou para a maioria das linhas em '{os.path.basename(caminho_arquivo)}'. Tentando inferir o formato.")
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

        df.dropna(subset=['DateTime'], inplace=True)

        if df.empty:
            st.error(f"Erro: Nenhum dado válido com 'DateTime' pôde ser processado no arquivo '{os.path.basename(caminho_arquivo)}'.")
            return pd.DataFrame()

        # Converter colunas numéricas (exceto DateTime, Date, Time)
        colunas_numericas = [col for col in df.columns if col not in ['DateTime', 'Date', 'Time']]
        for col in colunas_numericas:
            if col in df.columns:
                # Converte vírgula para ponto antes de converter para numérico
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

# =========================
#  Layout do Dashboard
# =========================

st.title("Máquina de Teste Fromtherm")

# --- Painel de Última Leitura Registrada ---
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: 600; margin-bottom: 10px;">Última Leitura Registrada</p>', unsafe_allow_html=True)

lista_arquivos = listar_arquivos_csv()
arquivo_mais_recente = lista_arquivos[0] if lista_arquivos else None

if arquivo_mais_recente and 'path' in arquivo_mais_recente:
    st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em; margin-bottom: 5px;">Arquivo: <span style="color: #00ffff; font-weight: bold;">{arquivo_mais_recente["nome_arquivo"]}</span></p>', unsafe_allow_html=True)

    if 'data_obj' in arquivo_mais_recente and arquivo_mais_recente['data_obj']:
        st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em; margin-bottom: 15px;">Data/Hora: <span style="color: #00ffff; font-weight: bold;">{arquivo_mais_recente["data_obj"].strftime("%d/%m/%Y %H:%M:%S")}</span></p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em; margin-bottom: 15px;">Data/Hora: <span style="color: #a0a0a0;">N/D</span></p>', unsafe_allow_html=True)

    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['path'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1]

        cols_metrics = st.columns(4) # 4 colunas para desktop, CSS empilha em mobile

        metric_titles = {
            'Ambiente': 'T-Ambiente',
            'Entrada': 'T-Entrada',
            'Saída': 'T-Saída',
            'ΔT': 'Dif',
            'Tensão (V)': 'Tensão',
            'Corrente (A)': 'Corrente',
            'Kcal/h': 'Kcal/h',
            'Vazão (L/h)': 'Vazão',
            'Kw Aquecimento': 'Kw Aquecimento',
            'Kw Consumo': 'Kw Consumo',
            'COP': 'COP',
        }

        metric_icons = {
            'Ambiente': '🌡️', 'Entrada': '➡️🌡️', 'Saída': '⬅️🌡️', 'ΔT': '↔️',
            'Tensão (V)': '⚡', 'Corrente (A)': '🔌', 'Kcal/h': '🔥',
            'Vazão (L/h)': '💧', 'Kw Aquecimento': '♨️', 'Kw Consumo': '💡', 'COP': '📈',
        }

        metric_units = {
            'Ambiente': '°C', 'Entrada': '°C', 'Saída': '°C', 'ΔT': '°C',
            'Tensão (V)': 'V', 'Corrente (A)': 'A', 'Kcal/h': 'Kcal/h',
            'Vazão (L/h)': 'L/h', 'Kw Aquecimento': 'Kw', 'Kw Consumo': 'Kw', 'COP': '',
        }

        for i, (col_name, title) in enumerate(metric_titles.items()):
            with cols_metrics[i % 4]:
                valor = ultima_linha.get(col_name, np.nan) # Usa .get para evitar KeyError
                display_value = format_br_number(valor, unit=metric_units.get(col_name, ''))
                icon = metric_icons.get(col_name, '📊')

                value_class = "metric-value"
                if col_name == 'Entrada':
                    value_class = "metric-value temp-entrada-value"
                elif col_name == 'Saída':
                    value_class = "metric-value temp-saida-value"

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <h4>{icon} {title}</h4>
                        <span class="{value_class}">{display_value}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.warning("Não foi possível carregar os dados do arquivo mais recente para o painel de última leitura.")
else:
    st.info("Nenhum arquivo CSV encontrado para exibir a última leitura.")

st.markdown("---")

# --- Filtros de Arquivos ---
st.sidebar.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: 600; margin-bottom: 10px;">Filtros de Arquivos</p>', unsafe_allow_html=True)

# Coletar todas as opções possíveis para os filtros
all_modelos = sorted(list(set(arq['modelo'] for arq in lista_arquivos if arq['modelo'] != 'N/D')))
all_operacoes = sorted(list(set(arq['operacao'] for arq in lista_arquivos if arq['operacao'] != 'N/D')))
all_anos = sorted(list(set(arq['data_obj'].year for arq in lista_arquivos if arq['data_obj'] is not None)), reverse=True)
all_meses = sorted(list(set(arq['data_obj'].month for arq in lista_arquivos if arq['data_obj'] is not None)))

# Adicionar opção "Todos"
all_modelos.insert(0, "Todos")
all_operacoes.insert(0, "Todos")
all_anos.insert(0, "Todos")
all_meses.insert(0, "Todos")

selected_modelo = st.sidebar.selectbox("Modelo (ex: FTI165HBR)", all_modelos, key="filtro_modelo")

# Filtrar operações com base no modelo selecionado
filtered_operacoes_by_model = []
if selected_modelo != "Todos":
    filtered_operacoes_by_model = sorted(list(set(arq['operacao'] for arq in lista_arquivos if arq['modelo'] == selected_modelo and arq['operacao'] != 'N/D')))
else:
    filtered_operacoes_by_model = sorted(list(set(arq['operacao'] for arq in lista_arquivos if arq['operacao'] != 'N/D')))

filtered_operacoes_by_model.insert(0, "Todos")
selected_operacao = st.sidebar.selectbox("N° Operação (ex: OP987)", filtered_operacoes_by_model, key="filtro_operacao")

selected_ano = st.sidebar.selectbox("Ano", all_anos, key="filtro_ano")
selected_mes = st.sidebar.selectbox("Mês", all_meses, key="filtro_mes")

# Aplicar filtros
arquivos_filtrados = lista_arquivos
if selected_modelo != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq['modelo'] == selected_modelo]
if selected_operacao != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq['operacao'] == selected_operacao]
if selected_ano != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq['data_obj'] and arq['data_obj'].year == selected_ano]
if selected_mes != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq['data_obj'] and arq['data_obj'].month == selected_mes]

# --- Arquivos Disponíveis ---
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: 600; margin-bottom: 10px;">Arquivos Disponíveis</p>', unsafe_allow_html=True)

if not arquivos_filtrados:
    st.info("Nenhum arquivo encontrado com os filtros selecionados.")
else:
    # Usar st.columns para organizar os botões em 3 colunas
    cols = st.columns(3)
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols[i % 3]: # Distribui os botões entre as 3 colunas
            display_name = arquivo['nome_arquivo'] # Exibe o nome original do arquivo
            if st.button(display_name, key=f"file_button_{arquivo['nome_arquivo']}"):
                st.session_state['selected_file_path'] = arquivo['path']
                st.session_state['selected_file_name'] = arquivo['nome_arquivo']
                st.rerun() # Recarrega a página para exibir os dados do arquivo selecionado

# Inicializa selected_filename e selected_file_path se não existirem
selected_filename = st.session_state.get('selected_file_name', None)
selected_file_path = st.session_state.get('selected_file_path', None)

st.markdown("---")

# --- Visualização de Dados e Gráficos ---
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: 600; margin-bottom: 10px;">Visualização de Dados e Gráficos</p>', unsafe_allow_html=True)

if selected_file_path:
    st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em; margin-bottom: 15px;">Arquivo Selecionado: <span style="color: #00ffff; font-weight: bold;">{selected_filename}</span></p>', unsafe_allow_html=True)

    df_selecionado = carregar_csv_caminho(selected_file_path)

    if not df_selecionado.empty:
        st.subheader("Dados do Arquivo")
        st.dataframe(df_selecionado, use_container_width=True)

        # Botão de download para Excel
        excel_file_name = selected_filename.replace(".csv", ".xlsx")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_selecionado.to_excel(writer, index=False, sheet_name='Dados')
        output.seek(0)
        st.download_button(
            label="Baixar Dados em Excel",
            data=output.getvalue(),
            file_name=excel_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_excel_{selected_filename}"
        )

        st.subheader("Crie Seu Gráfico")

        df_graf = df_selecionado.copy()

        if 'DateTime' in df_graf.columns and not df_graf.empty:
            # Garante que 'DateTime' seja o índice para gráficos de tempo
            df_graf = df_graf.set_index('DateTime')

            # Opções de variáveis para o gráfico (exclui colunas de data/hora)
            variaveis_opcoes = [col for col in df_graf.columns if col not in ['Date', 'Time']]

            vars_selecionadas = st.multiselect(
                "Selecione uma ou mais variáveis:",
                variaveis_opcoes,
                default=["Ambiente", "Entrada", "Saída"] if all(v in variaveis_opcoes for v in ["Ambiente", "Entrada", "Saída"]) else variaveis_opcoes[:3],
                key=f"graf_vars_{selected_filename}"
            )

            if not vars_selecionadas:
                st.info("Selecione pelo menos uma variável para gerar o gráfico.")
            else:
                # Resetar o índice para 'DateTime' ser uma coluna novamente para Plotly Express
                df_plot = df_graf.reset_index()[["DateTime"] + vars_selecionadas].copy()
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
                    title=f"Gráfico - {selected_filename}",
                    markers=True,
                )

                fig.update_yaxes(rangemode="tozero")

                fig.update_layout(
                    xaxis_title="Tempo",
                    yaxis_title="Valor",
                    hovermode="x unified",
                    legend_title="Variáveis",
                    plot_bgcolor='rgba(0,0,0,0.1)', # Fundo do gráfico escuro
                    paper_bgcolor='rgba(0,0,0,0)', # Fundo do papel transparente
                    font=dict(color='#e0e0e0'), # Cor da fonte do gráfico
                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)'), # Cor da grade X
                    yaxis=dict(gridcolor='rgba(255,255,255,0.1)')  # Cor da grade Y
                )

                st.plotly_chart(fig, use_container_width=True)

                st.markdown(
                    "- Use o botão de **fullscreen** no gráfico para expandir.\n"
                    "- Use o ícone de **câmera** no gráfico para baixar como imagem (PNG).\n"
                    "- A imagem baixada pode ser compartilhada via WhatsApp, e-mail, etc., em qualquer dispositivo."
                )
        else:
            st.warning("Não há dados válidos ou coluna 'DateTime' para gerar o gráfico.")

    else:
        st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo na lista acima para visualizar os dados e gerar gráficos.")
