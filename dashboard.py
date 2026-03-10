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
        color: #00bfff; /* Azul Neon para títulos das métricas */
        font-size: 1.1em;
        margin-bottom: 5px;
        font-weight: 600;
    }
    /* Estilo para os valores dentro do st.metric (se usado) */
    .st-emotion-cache-1r6dm1x { /* Alvo para o valor do st.metric */
        font-size: 1.5em;
        font-weight: bold;
        color: #e0e0e0; /* Cinza Gelo para valores */
    }
    /* Estilo para o ícone dentro do st.metric (se usado) */
    .st-emotion-cache-1r6dm1x svg { /* Alvo para o ícone do st.metric */
        font-size: 1.2em;
        margin-right: 5px;
        color: #00bfff; /* Azul Neon para ícones */
    }

    /* Cores específicas para T-Entrada e T-Saída */
    .temp-entrada-value {
        color: #00ffff; /* Azul Neon */
        font-size: 1.5em;
        font-weight: bold;
        text-shadow: 0 0 5px rgba(0, 255, 255, 0.5); /* Brilho */
    }
    .temp-saida-value {
        color: #ff0000; /* Vermelho Vibrante */
        font-size: 1.5em;
        font-weight: bold;
        text-shadow: 0 0 5px rgba(255, 0, 0, 0.5); /* Brilho */
    }
    .metric-value { /* Estilo para outros valores de métrica */
        color: #e0e0e0; /* Cinza Gelo */
        font-size: 1.5em;
        font-weight: bold;
    }
    .metric-icon { /* Estilo para outros ícones de métrica */
        color: #00bfff; /* Azul Neon */
        margin-right: 5px;
    }

    /* Estilo para os botões de arquivo */
    .stButton > button {
        background-color: #003366; /* Fundo azul escuro */
        color: #e0e0e0; /* Texto cinza gelo */
        border: 1px solid #00bfff; /* Borda azul neon */
        border-radius: 5px;
        padding: 8px 15px;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #004080; /* Azul mais claro no hover */
        border-color: #00ffff; /* Borda azul mais clara no hover */
        color: #ffffff;
        box-shadow: 0 0 10px rgba(0, 191, 255, 0.5); /* Brilho no hover */
    }

    /* Estilo para a tabela de dados */
    .stDataFrame {
        border: 1px solid rgba(0, 191, 255, 0.2);
        border-radius: 8px;
        overflow: hidden; /* Garante que a borda arredondada seja visível */
    }
    .stDataFrame > div > div > div > div > div { /* Cabeçalho da tabela */
        background-color: #003366; /* Fundo do cabeçalho */
        color: #00bfff; /* Cor do texto do cabeçalho */
        font-weight: bold;
    }
    .stDataFrame > div > div > div > div > div > div { /* Células da tabela */
        background-color: rgba(0, 0, 0, 0.1); /* Fundo das células */
        color: #e0e0e0; /* Cor do texto das células */
    }
    .stDataFrame > div > div > div > div > div:nth-child(even) > div { /* Linhas pares */
        background-color: rgba(0, 0, 0, 0.05);
    }

    /* Estilo para o multiselect do gráfico */
    .stMultiSelect > label {
        color: #00bfff; /* Rótulo do multiselect */
    }
    .stMultiSelect > div > div {
        background-color: #003366;
        color: #e0e0e0;
        border: 1px solid #00bfff;
    }
    .stMultiSelect > div > div > div > div > span {
        color: #e0e0e0;
    }
    .stMultiSelect > div > div > div > div > div {
        background-color: #003366; /* Opções do multiselect */
        color: #e0e0e0;
    }
    .stMultiSelect > div > div > div > div > div:hover {
        background-color: #004080;
    }

    /* Ajustes de responsividade para telas menores */
    @media (max-width: 768px) {
        .main > div {
            padding: 10px 15px 20px 15px; /* Reduz o padding em mobile */
        }
        h1 {
            font-size: 1.8em !important; /* Reduz o tamanho do título principal */
        }
        .metric-card {
            padding: 10px; /* Reduz o padding dos cards */
        }
        .metric-card h4 {
            font-size: 1em; /* Reduz o tamanho da fonte dos títulos das métricas */
        }
        .st-emotion-cache-1r6dm1x, .temp-entrada-value, .temp-saida-value, .metric-value { /* Valor da métrica */
            font-size: 1.2em; /* Reduz o tamanho da fonte dos valores */
        }
        /* Força o empilhamento de colunas em mobile */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.stPlotlyChart) {
            width: 100% !important; /* Faz os elementos ocuparem a largura total */
            margin-bottom: 10px; /* Adiciona espaçamento entre eles */
        }
        /* Ajusta o tamanho do texto do botão de download */
        .stDownloadButton > button {
            font-size: 0.9em;
            padding: 6px 10px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Função para formatar números para o padrão brasileiro ---
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float, arredonda e formata
        num_float = float(value)
        formatted_num = f"{num_float:,.{decimals}f}"
        # Troca separador de milhar e decimal para padrão BR
        formatted_num = formatted_num.replace('.', 'X').replace(',', '.').replace('X', ',')
        return f"{formatted_num} {unit}".strip()
    except (ValueError, TypeError):
        return "N/D"

# --- Função para listar arquivos CSV e extrair metadados ---
@st.cache_data(ttl=3600) # Cache para evitar reprocessar a lista de arquivos
def listar_arquivos_csv(base_path="."):
    arquivos_encontrados = []
    # Caminho relativo para a pasta 'dados_brutos'
    search_path = os.path.join(base_path, "dados_brutos", "**", "*.csv")

    # Usa glob para encontrar arquivos recursivamente
    for f_path in glob.glob(search_path, recursive=True):
        f_name = os.path.basename(f_path)

        # Expressão regular mais flexível para capturar os componentes do nome do arquivo
        # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
        # Ex: historico_L1_20260306_1717_OP9090_FT55L.csv
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", f_name)

        modelo = "N/D"
        operacao = "N/D"
        data_str = "N/D"
        hora_str = "N/D"
        data_obj = None

        if match:
            ano, mes, dia, hora_completa, op, modelo_sufixo = match.groups()
            data_str = f"{dia}/{mes}/{ano}"
            hora_str = f"{hora_completa[:2]}:{hora_completa[2:]}"

            try:
                data_obj = datetime.strptime(f"{ano}{mes}{dia}{hora_completa}", "%Y%m%d%H%M")
            except ValueError:
                data_obj = None # Se a data for inválida, mantém como None

            modelo = modelo_sufixo # Usa o sufixo como modelo
            operacao = op
        else:
            # Se o regex não der match, tenta extrair o máximo possível ou usa o nome completo
            parts = f_name.replace('.csv', '').split('_')
            if len(parts) >= 6: # historico_L1_YYYYMMDD_HHMM_OPXXX_MODELO
                modelo = parts[5]
                operacao = parts[4]
                data_part = parts[2]
                hora_part = parts[3]
                if len(data_part) == 8 and len(hora_part) == 4:
                    data_str = f"{data_part[6:]}/{data_part[4:6]}/{data_part[:4]}"
                    hora_str = f"{hora_part[:2]}:{hora_part[2:]}"
                    try:
                        data_obj = datetime.strptime(f"{data_part}{hora_part}", "%Y%m%d%H%M")
                    except ValueError:
                        pass

        arquivos_encontrados.append({
            "caminho_completo": f_path,
            "nome_arquivo": f_name,
            "modelo": modelo,
            "operacao": operacao,
            "data": data_obj, # Objeto datetime para ordenação
            "data_str": data_str, # String formatada para exibição
            "hora_str": hora_str, # String formatada para exibição
            "ano": data_obj.year if data_obj else "N/D",
            "mes": data_obj.month if data_obj else "N/D",
        })

    # Ordena os arquivos pelo mais recente primeiro
    arquivos_encontrados.sort(key=lambda x: x["data"] if x["data"] else datetime.min, reverse=True)
    return arquivos_encontrados

# --- Função para carregar e processar um arquivo CSV ---
@st.cache_data(ttl=600) # Cache para os dados do CSV
def carregar_csv_caminho(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove a linha de separação "| --- | --- | ..."
        lines = content.split('\n')
        # Encontra a linha que contém "---" e a remove
        filtered_lines = [line for line in lines if not re.match(r'^\s*\|\s*-+\s*\|\s*-+\s*\|', line)]

        # Junta as linhas restantes e lê com pandas
        data_io = StringIO('\n'.join(filtered_lines))

        # Lê o CSV, usando '|' como separador e removendo espaços iniciais/finais
        df = pd.read_csv(data_io, sep='|', skipinitialspace=True)

        # Remove a primeira e a última coluna que podem ser vazias devido ao separador '|'
        df = df.iloc[:, 1:-1]

        # Limpa espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Mapeamento de nomes de colunas do CSV para nomes padronizados
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
            'Date': 'Date', # Manter Date e Time para criar DateTime
            'Time': 'Time'
        }

        # Renomeia as colunas existentes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # --- Processamento de Data e Hora ---
        if 'Date' in df.columns and 'Time' in df.columns:
            # Converte a coluna 'Date' para o formato YYYY-MM-DD para garantir consistência
            df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)

            # Combina 'Date' e 'Time' para criar 'DateTime'
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

            # Remove linhas onde DateTime não pôde ser parseado
            df.dropna(subset=['DateTime'], inplace=True)

            # Ordena o DataFrame por DateTime
            df.sort_values(by='DateTime', inplace=True)
        else:
            st.error("Colunas 'Date' ou 'Time' não encontradas para criar 'DateTime'.")
            return pd.DataFrame() # Retorna DataFrame vazio se colunas essenciais não existirem

        # --- Conversão de tipos numéricos ---
        numeric_cols = [
            'Ambiente', 'Entrada', 'Saída', 'ΔT', 'Tensão (V)', 'Corrente (A)',
            'Kcal/h', 'Vazão (L/h)', 'Kw Aquecimento', 'Kw Consumo', 'COP'
        ]
        for col in numeric_cols:
            if col in df.columns:
                # Converte para string, substitui vírgula por ponto, depois para numérico
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# --- Início da aplicação Streamlit ---
st.sidebar.image("https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png", use_column_width=True)
st.sidebar.markdown('<h2 style="color: #00bfff; text-shadow: 0 0 3px rgba(0, 191, 255, 0.3);">Filtros de Arquivos</h2>', unsafe_allow_html=True)

arquivos = listar_arquivos_csv()

# Extrair opções únicas para os filtros
modelos_disponiveis = sorted(list(set([a["modelo"] for a in arquivos if a["modelo"] != "N/D"])))
anos_disponiveis = sorted(list(set([a["ano"] for a in arquivos if a["ano"] != "N/D"])), reverse=True)
meses_disponiveis = sorted(list(set([a["mes"] for a in arquivos if a["mes"] != "N/D"])))

# Adicionar "Todos" como opção padrão
modelos_filtro = ["Todos"] + modelos_disponiveis
anos_filtro = ["Todos"] + anos_disponiveis
meses_filtro = ["Todos"] + meses_disponiveis

# --- Filtros na Sidebar ---
selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    modelos_filtro,
    key="modelo_filter"
)

# Filtrar arquivos com base no modelo selecionado para popular as operações
arquivos_filtrados_por_modelo = [a for a in arquivos if selected_modelo == "Todos" or a["modelo"] == selected_modelo]
operacoes_disponiveis = sorted(list(set([a["operacao"] for a in arquivos_filtrados_por_modelo if a["operacao"] != "N/D"])))
operacoes_filtro = ["Todos"] + operacoes_disponiveis

selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    operacoes_filtro,
    key="operacao_filter"
)

# Filtrar arquivos com base no modelo e operação selecionados para popular anos e meses
arquivos_filtrados_por_op = [a for a in arquivos_filtrados_por_modelo if selected_operacao == "Todos" or a["operacao"] == selected_operacao]
anos_disponiveis_filtrados = sorted(list(set([a["ano"] for a in arquivos_filtrados_por_op if a["ano"] != "N/D"])), reverse=True)
meses_disponiveis_filtrados = sorted(list(set([a["mes"] for a in arquivos_filtrados_por_op if a["mes"] != "N/D"])))

anos_filtro_dinamico = ["Todos"] + anos_disponiveis_filtrados
meses_filtro_dinamico = ["Todos"] + meses_disponiveis_filtrados

selected_ano = st.sidebar.selectbox(
    "Ano:",
    anos_filtro_dinamico,
    key="ano_filter"
)

selected_mes = st.sidebar.selectbox(
    "Mês:",
    meses_filtro_dinamico,
    key="mes_filter"
)

# Aplicar todos os filtros
arquivos_filtrados = arquivos
if selected_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == selected_modelo]
if selected_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == selected_operacao]
if selected_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["ano"] == selected_ano]
if selected_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["mes"] == selected_mes]

# --- Painel de Última Leitura Registrada ---
st.markdown('<p style="color: #00bfff; font-size: 1.8em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Última Leitura Registrada</p>', unsafe_allow_html=True)

if arquivos:
    arquivo_mais_recente = arquivos[0] # O primeiro da lista já é o mais recente
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente["caminho_completo"])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1].to_dict()

        st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em;">Arquivo: <span style="color: #00ffff;">{arquivo_mais_recente["nome_arquivo"]}</span></p>', unsafe_allow_html=True)
        if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']):
            st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em;">Data e Hora da Leitura: <span style="color: #00ffff;">{ultima_linha["DateTime"].strftime("%d/%m/%Y %H:%M:%S")}</span></p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p style="color: #e0e0e0; font-size: 1.1em;">Data e Hora da Leitura: <span style="color: #ff0000;">N/D</span></p>', unsafe_allow_html=True)

        st.markdown("---")

        metric_icons = {
            'Ambiente': '🌡️', 'Entrada': '➡️', 'Saída': '⬅️', 'ΔT': '↔️',
            'Tensão (V)': '⚡', 'Corrente (A)': ' 전류', 'Kcal/h': '🔥',
            'Vazão (L/h)': '💧', 'Kw Aquecimento': '♨️', 'Kw Consumo': '💡', 'COP': '📈'
        }
        metric_units = {
            'Ambiente': '°C', 'Entrada': '°C', 'Saída': '°C', 'ΔT': '°C',
            'Tensão (V)': 'V', 'Corrente (A)': 'A', 'Kcal/h': 'Kcal/h',
            'Vazão (L/h)': 'L/h', 'Kw Aquecimento': 'kW', 'Kw Consumo': 'kW', 'COP': ''
        }

        # Layout em 2 colunas para mobile, 4 para desktop (via CSS)
        cols_metrics = st.columns(2) 

        metrics_to_display = [
            'Ambiente', 'Entrada', 'Saída', 'ΔT', 'Tensão (V)', 'Corrente (A)',
            'Kcal/h', 'Vazão (L/h)', 'Kw Aquecimento', 'Kw Consumo', 'COP'
        ]

        for i, metric_name in enumerate(metrics_to_display):
            with cols_metrics[i % 2]: # Alterna entre as 2 colunas
                value = ultima_linha.get(metric_name)
                display_value = format_br_number(value, unit=metric_units.get(metric_name, ''))
                icon = metric_icons.get(metric_name, '📊')

                if metric_name == 'Entrada':
                    value_html = f'<span class="temp-entrada-value">{display_value}</span>'
                elif metric_name == 'Saída':
                    value_html = f'<span class="temp-saida-value">{display_value}</span>'
                else:
                    value_html = f'<span class="metric-value">{display_value}</span>'

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <h4>{icon} {metric_name}</h4>
                        {value_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.warning("Não foi possível carregar ou processar os dados do arquivo mais recente para o painel de última leitura.")
else:
    st.info("Nenhum arquivo CSV encontrado para exibir a última leitura.")

st.markdown("---") # Separador após o painel de última leitura

# --- Título principal do Dashboard ---
st.title("Máquina de Teste Fromtherm")

# --- Seção de Arquivos Disponíveis ---
st.markdown('<h2 style="color: #00bfff; text-shadow: 0 0 3px rgba(0, 191, 255, 0.3);">Arquivos Disponíveis</h2>', unsafe_allow_html=True)

if arquivos_filtrados:
    # Usar st.columns para organizar os botões em 3 colunas (desktop)
    # O CSS já fará com que se empilhem em mobile
    cols = st.columns(3) 
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols[i % 3]: # Distribui os botões entre as 3 colunas
            if st.button(arquivo['nome_arquivo'], key=f"file_button_{arquivo['nome_arquivo']}"):
                st.session_state['selected_file_path'] = arquivo['caminho_completo']
                st.session_state['selected_filename'] = arquivo['nome_arquivo']
                st.rerun() # Recarrega a página para exibir o arquivo selecionado
else:
    st.info("Nenhum arquivo encontrado com os filtros aplicados.")

# --- Visualização do Arquivo Selecionado ---
st.markdown("---")
if 'selected_file_path' in st.session_state and st.session_state['selected_file_path']:
    selected_filename = st.session_state['selected_filename']

    st.markdown(f'<h3 style="color: #00bfff; text-shadow: 0 0 3px rgba(0, 191, 255, 0.3);">Visualizando: <span style="color: #00ffff;">{selected_filename}</span></h3>', unsafe_allow_html=True)

    df_dados = carregar_csv_caminho(st.session_state['selected_file_path'])

    if not df_dados.empty:
        st.dataframe(df_dados, use_container_width=True)

        # Botão de exportar para Excel
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_dados.to_excel(writer, index=False, sheet_name='Dados')
            workbook = writer.book
            worksheet = writer.sheets['Dados']

            # Ajusta a largura das colunas no Excel
            for col_idx, col_name in enumerate(df_dados.columns):
                if "kW" in col_name:
                    worksheet.set_column(col_idx, col_idx, 15)
                elif "Ambiente" in col_name or "Corrente" in col_name:
                    worksheet.set_column(col_idx, col_idx, 10)
                elif "Date" in col_name or "DateTime" in col_name:
                    worksheet.set_column(col_idx, col_idx, 18) # Mais largo para DateTime
                elif "Time" in col_name:
                    worksheet.set_column(col_idx, col_idx, 10)
                else:
                    worksheet.set_column(col_idx, col_idx, 12)

        output_excel.seek(0)

        # Gera o nome do arquivo para download (usa o nome original do CSV, mas com extensão .xlsx)
        excel_file_name = selected_filename.replace('.csv', '.xlsx')

        st.download_button(
            label="Exportar para Excel",
            data=output_excel,
            file_name=excel_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"excel_download_{selected_filename}",
        )

        # --- Seção de Gráficos ---
        st.markdown("---")
        st.subheader("Crie Seu Gráfico")

        # Usar o DataFrame do arquivo selecionado para gerar o gráfico
        df_graf = df_dados.copy()

        if not df_graf.empty and 'DateTime' in df_graf.columns:
            st.markdown("### Variáveis para o gráfico")

            # Usar os nomes de colunas do DataFrame carregado, exceto 'DateTime', 'Date', 'Time'
            variaveis_opcoes = [col for col in df_graf.columns if col not in ['DateTime', 'Date', 'Time']]

            vars_selecionadas = st.multiselect(
                "Selecione uma ou mais variáveis:",
                variaveis_opcoes,
                default=["Ambiente", "Entrada", "Saída"] if all(v in variaveis_opcoes for v in ["Ambiente", "Entrada", "Saída"]) else variaveis_opcoes[:3],
                key=f"graf_vars_{selected_filename}"
            )

            if not vars_selecionadas:
                st.info("Selecione pelo menos uma variável para gerar o gráfico.")
            else:
                df_plot = df_graf[["DateTime"] + vars_selecionadas].copy()
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
