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
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        background-color: rgba(0, 0, 0, 0.1); /* Fundo escuro translúcido para a tabela */
    }
    .stDataFrame .dataframe {
        background-color: transparent;
        color: #e0e0e0;
    }
    .stDataFrame .data-grid-container {
        background-color: transparent;
    }
    .stDataFrame .data-grid-container .header-row {
        background-color: rgba(0, 191, 255, 0.1); /* Cabeçalho da tabela */
        color: #00bfff;
    }
    .stDataFrame .data-grid-container .header-row .header-cell {
        color: #00bfff;
        font-weight: bold;
    }
    .stDataFrame .data-grid-container .cell {
        color: #e0e0e0;
    }
    .stDataFrame .data-grid-container .row-hover {
        background-color: rgba(0, 191, 255, 0.05); /* Linha hover */
    }
    .stDataFrame .data-grid-container .row-selected {
        background-color: rgba(0, 191, 255, 0.15); /* Linha selecionada */
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
    .stMultiSelect > div > div > div > div > div {
        background-color: #003366; /* Opções do multiselect */
        color: #e0e0e0;
    }
    .stMultiSelect > div > div > div > div > div:hover {
        background-color: #004080;
    }
    .stMultiSelect .st-emotion-cache-10trblm { /* selected items */
        background-color: #00bfff;
        color: #000000;
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
        /* Ajusta o layout dos botões de arquivo para empilhar em telas pequenas */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button) {
            width: 100% !important; /* Faz os botões ocuparem a largura total */
            margin-bottom: 5px; /* Adiciona um pequeno espaçamento entre eles */
        }
        /* Ajusta o layout das colunas de métricas para empilhar em telas pequenas */
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card) {
            width: 100% !important; /* Faz os cards ocuparem a largura total */
            margin-bottom: 5px; /* Adiciona um pequeno espaçamento entre eles */
        }
        /* Garante que o gráfico ocupe 100% da largura em mobile */
        .stPlotlyChart {
            width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para formatar números para o padrão brasileiro ---
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float e formata com duas casas decimais
        formatted_value = f"{float(value):,.{decimals}f}"
        # Troca o separador de milhar por ponto e o decimal por vírgula
        formatted_value = formatted_value.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted_value} {unit}".strip()
    except (ValueError, TypeError):
        return "N/D"


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome.
    Tenta ser flexível com o padrão de nome.
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    lista_arquivos = []

    # Regex mais flexível para capturar o modelo e operação
    # Ex: historico_L1_YYYYMMDD_HHMM_OPXXX_MODELO.csv
    # MODELO pode ser FTA987BR, FT55L, FTI165HBR, etc.
    regex_pattern = r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv"

    for caminho_completo in arquivos:
        nome_arquivo = os.path.basename(caminho_completo)
        match = re.match(regex_pattern, nome_arquivo)

        data = None
        hora = None
        modelo = "N/D"
        operacao = "N/D"
        ano = "N/D"
        mes = "N/D"

        if match:
            ano_str, mes_str, dia_str, hora_str, operacao_str, modelo_str = match.groups()
            try:
                data = datetime.strptime(f"{ano_str}{mes_str}{dia_str}", "%Y%m%d").date()
                hora = datetime.strptime(hora_str, "%H%M").time()
                ano = int(ano_str)
                mes = int(mes_str)
                modelo = modelo_str
                operacao = operacao_str
            except ValueError:
                pass # Se a conversão falhar, mantém N/D

        lista_arquivos.append({
            "caminho_completo": caminho_completo,
            "nome_arquivo": nome_arquivo,
            "data": data,
            "hora": hora,
            "modelo": modelo,
            "operacao": operacao,
            "ano": ano,
            "mes": mes
        })

    # Ordena os arquivos pelo nome (que contém a data e hora) para pegar o mais recente
    lista_arquivos.sort(key=lambda x: x['nome_arquivo'], reverse=True)
    return lista_arquivos


# --- Função para carregar e processar um arquivo CSV ---
@st.cache_data(ttl=10)
def carregar_csv_caminho(caminho_completo):
    try:
        # Lê o conteúdo do arquivo como uma string
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove a linha de separação "| --- | --- | ..."
        lines = content.splitlines()
        filtered_lines = [line for line in lines if not re.match(r'^\|\s*-+\s*\|', line)]

        # Junta as linhas novamente e usa StringIO para o pandas
        data_io = StringIO('\n'.join(filtered_lines))

        # Lê o CSV usando '|' como separador e pulando espaços iniciais/finais
        df = pd.read_csv(data_io, sep='|', skipinitialspace=True, decimal='.', encoding='utf-8')

        # Remove a primeira coluna vazia e a última coluna vazia que podem surgir devido ao separador '|'
        df = df.iloc[:, 1:-1]

        # Limpa espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Mapeamento de nomes de colunas do CSV para nomes padronizados
        column_mapping = {
            'Date': 'Date',
            'Time': 'Time',
            'ambiente': 'Ambiente',
            'entrada': 'Entrada',
            'saida': 'Saída',
            'dif': 'ΔT',
            'tensao': 'Tensão',
            'corrente': 'Corrente',
            'kacl/h': 'Kcal/h',
            'vazao': 'Vazão',
            'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo',
            'cop': 'COP'
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Converte colunas numéricas, tratando '000.0' e '00000'
        numeric_cols = [
            'Ambiente', 'Entrada', 'Saída', 'ΔT', 'Tensão', 'Corrente',
            'Kcal/h', 'Vazão', 'Kw Aquecimento', 'Kw Consumo', 'COP'
        ]
        for col in numeric_cols:
            if col in df.columns:
                # Substitui vírgulas por pontos para conversão para float
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Cria a coluna DateTime
        if 'Date' in df.columns and 'Time' in df.columns:
            # Garante que 'Date' e 'Time' são strings antes de combinar
            df['Date'] = df['Date'].astype(str)
            df['Time'] = df['Time'].astype(str)

            # Tenta diferentes formatos de data
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y/%m/%d %H:%M:%S', errors='coerce')
            # Se o formato acima falhar, tenta outro (ex: YYYY-MM-DD)
            df['DateTime'] = df['DateTime'].fillna(pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y-%m-%d %H:%M:%S', errors='coerce'))

            # Remove linhas onde DateTime não pôde ser parseado
            df.dropna(subset=['DateTime'], inplace=True)
            df.sort_values(by='DateTime', inplace=True)
        else:
            st.warning("Colunas 'Date' ou 'Time' não encontradas para criar 'DateTime'.")
            return pd.DataFrame() # Retorna DataFrame vazio se não puder criar DateTime

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        return pd.DataFrame()


# --- Lógica principal do Dashboard ---
todos_arquivos = listar_arquivos_csv()

# --- Painel de Última Leitura Registrada ---
st.markdown('<h2 style="color: #00bfff; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Última Leitura Registrada</h2>', unsafe_allow_html=True)

if todos_arquivos:
    arquivo_mais_recente = todos_arquivos[0]
    df_mais_recente = carregar_csv_caminho(arquivo_mais_recente['caminho_completo'])

    if not df_mais_recente.empty:
        ultima_linha = df_mais_recente.iloc[-1]

        st.markdown(f'<p style="color: #e0e0e0;">Arquivo: <span style="color: #00bfff;">{arquivo_mais_recente["nome_arquivo"]}</span></p>', unsafe_allow_html=True)

        ultima_leitura_dt = ultima_linha['DateTime'].strftime('%d/%m/%Y %H:%M') if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']) else "N/D"
        st.markdown(f'<p style="color: #e0e0e0;">Última leitura: <span style="color: #00bfff;">{ultima_leitura_dt}</span></p>', unsafe_allow_html=True)

        st.markdown("---")

        # Definição das métricas e seus ícones/unidades
        metric_definitions = [
            {"label": "T-Ambiente", "col": "Ambiente", "icon": "🏠", "unit": "°C", "color_class": "metric-value"},
            {"label": "T-Entrada", "col": "Entrada", "icon": "➡️", "unit": "°C", "color_class": "temp-entrada-value"},
            {"label": "T-Saída", "col": "Saída", "icon": "⬅️", "unit": "°C", "color_class": "temp-saida-value"},
            {"label": "ΔT", "col": "ΔT", "icon": "🌡️", "unit": "°C", "color_class": "metric-value"},
            {"label": "Tensão", "col": "Tensão", "icon": "⚡", "unit": "V", "color_class": "metric-value"},
            {"label": "Corrente", "col": "Corrente", "icon": "🔌", "unit": "A", "color_class": "metric-value"},
            {"label": "Kcal/h", "col": "Kcal/h", "icon": "🔥", "unit": "Kcal/h", "color_class": "metric-value"},
            {"label": "Vazão", "col": "Vazão", "icon": "💧", "unit": "L/h", "color_class": "metric-value"},
            {"label": "Kw Aquecimento", "col": "Kw Aquecimento", "icon": "♨️", "unit": "kW", "color_class": "metric-value"},
            {"label": "Kw Consumo", "col": "Kw Consumo", "icon": "💡", "unit": "kW", "color_class": "metric-value"},
            {"label": "COP", "col": "COP", "icon": "📈", "unit": "", "color_class": "metric-value"},
        ]

        cols_metrics = st.columns(4) # 4 colunas para desktop, CSS empilha em mobile

        for i, metric_def in enumerate(metric_definitions):
            with cols_metrics[i % 4]: # Garante que as métricas se distribuam nas 4 colunas
                col_name = metric_def["col"]
                label = metric_def["label"]
                icon = metric_def["icon"]
                unit = metric_def["unit"]
                color_class = metric_def["color_class"]

                valor = ultima_linha.get(col_name)
                display_value = format_br_number(valor, unit=unit)

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <h4>{label}</h4>
                        <p><span class="metric-icon">{icon}</span> <span class="{color_class}">{display_value}</span></p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.warning("Não foi possível carregar os dados do arquivo mais recente para o painel de última leitura.")
else:
    st.info("Nenhum arquivo de histórico encontrado na pasta. Por favor, adicione arquivos CSV.")

st.markdown("---") # Separador após o painel de última leitura

# --- Título principal da página ---
st.markdown('<h1 style="color: #00bfff; text-shadow: 0 0 8px rgba(0, 191, 255, 0.5);">Máquina de Teste Fromtherm</h1>', unsafe_allow_html=True)


# --- Filtros de Arquivos na barra lateral ---
st.sidebar.markdown('<h3 style="color: #00bfff;">Filtros de Arquivos</h3>', unsafe_allow_html=True)

# Coleta todas as opções disponíveis antes de filtrar
all_modelos = sorted(list(set([a["modelo"] for a in todos_arquivos if a["modelo"] != "N/D"])))
all_operacoes = sorted(list(set([a["operacao"] for a in todos_arquivos if a["operacao"] != "N/D"])))
all_anos = sorted(list(set([a["ano"] for a in todos_arquivos if a["ano"] != "N/D"])), reverse=True)
all_meses = sorted(list(set([a["mes"] for a in todos_arquivos if a["mes"] != "N/D"])))

selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    ["Todos"] + all_modelos,
    key="filter_modelo"
)

# Filtra operações com base no modelo selecionado
arquivos_filtrados_por_modelo = [
    a for a in todos_arquivos
    if selected_modelo == "Todos" or a["modelo"] == selected_modelo
]
all_operacoes_for_model = sorted(list(set([a["operacao"] for a in arquivos_filtrados_por_modelo if a["operacao"] != "N/D"])))

selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    ["Todos"] + all_operacoes_for_model,
    key="filter_operacao"
)

# Filtra anos com base nas seleções anteriores
arquivos_filtrados_por_operacao = [
    a for a in arquivos_filtrados_por_modelo
    if selected_operacao == "Todos" or a["operacao"] == selected_operacao
]
all_anos_for_selection = sorted(list(set([a["ano"] for a in arquivos_filtrados_por_operacao if a["ano"] != "N/D"])), reverse=True)

selected_ano = st.sidebar.selectbox(
    "Ano:",
    ["Todos"] + all_anos_for_selection,
    key="filter_ano"
)

# Filtra meses com base nas seleções anteriores
arquivos_filtrados_por_ano = [
    a for a in arquivos_filtrados_por_operacao
    if selected_ano == "Todos" or a["ano"] == selected_ano
]
all_meses_for_selection = sorted(list(set([a["mes"] for a in arquivos_filtrados_por_ano if a["mes"] != "N/D"])))

selected_mes = st.sidebar.selectbox(
    "Mês:",
    ["Todos"] + all_meses_for_selection,
    format_func=lambda x: x if x == "Todos" else datetime(2000, x, 1).strftime('%B').capitalize(),
    key="filter_mes"
)

# Aplica todos os filtros
arquivos_filtrados = [
    a for a in arquivos_filtrados_por_ano
    if selected_mes == "Todos" or a["mes"] == selected_mes
]

st.sidebar.markdown("---")

# --- Exibição dos Arquivos Disponíveis na área principal ---
st.markdown('<h2 style="color: #00bfff; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Arquivos Disponíveis</h2>', unsafe_allow_html=True)

selected_filename = None
if arquivos_filtrados:
    # Cria colunas para os botões de arquivo
    cols_buttons = st.columns(3) # 3 colunas para desktop, CSS empilha em mobile
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols_buttons[i % 3]:
            if st.button(arquivo['nome_arquivo'], key=f"file_button_{i}"):
                selected_filename = arquivo['nome_arquivo']
                st.session_state['selected_file_path'] = arquivo['caminho_completo']
else:
    st.info("Nenhum arquivo encontrado com os filtros selecionados.")

# Carrega o arquivo selecionado ou o que está na session_state
if 'selected_file_path' in st.session_state and st.session_state['selected_file_path']:
    if selected_filename is None: # Se a página recarregou e não clicou em um novo botão
        selected_filename = os.path.basename(st.session_state['selected_file_path'])

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
