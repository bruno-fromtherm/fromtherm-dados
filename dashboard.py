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
        font-size: 1.2em;
        margin-right: 5px;
    }

    /* Estilo para os botões de arquivo */
    .stButton > button {
        background-color: #003366; /* Fundo azul escuro */
        color: #e0e0e0; /* Texto cinza gelo */
        border: 1px solid #00bfff; /* Borda azul neon */
        border-radius: 5px;
        padding: 8px 15px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #004080; /* Azul mais claro no hover */
        border-color: #00ffff; /* Borda azul mais vibrante */
        box-shadow: 0 0 8px rgba(0, 255, 255, 0.5); /* Brilho no hover */
    }

    /* Estilo para a tabela de dados */
    .stDataFrame {
        background-color: rgba(0, 0, 0, 0.1); /* Fundo escuro translúcido */
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stDataFrame table {
        color: #e0e0e0; /* Texto da tabela cinza gelo */
    }
    .stDataFrame th {
        background-color: rgba(0, 191, 255, 0.1); /* Cabeçalho da tabela azul neon translúcido */
        color: #00bfff; /* Texto do cabeçalho azul neon */
        font-weight: 600;
    }
    .stDataFrame tr:nth-child(even) {
        background-color: rgba(255, 255, 255, 0.02); /* Linhas pares mais claras */
    }
    .stDataFrame tr:hover {
        background-color: rgba(0, 191, 255, 0.05); /* Efeito hover na linha */
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
    .stMultiSelect .st-emotion-cache-1r6dm1x { /* Tags selecionadas */
        background-color: #00bfff;
        color: #001f3f;
    }

    /* Ajustes de responsividade para telas menores */
    @media (max-width: 768px) {
        .main > div {
            padding: 10px 15px 20px 15px; /* Reduz o padding em mobile */
        }
        h1 {
            font-size: 1.8em !important;
        }
        h4 {
            font-size: 1em !important;
        }
        .temp-entrada-value, .temp-saida-value, .metric-value {
            font-size: 1.2em !important; /* Reduz o tamanho da fonte dos valores */
        }
        .metric-icon {
            font-size: 1em !important;
        }

        /* Empilhamento de colunas para mobile */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.stPlotlyChart) {
            width: 100% !important;
            margin-bottom: 10px; /* Espaçamento entre elementos empilhados */
        }
        /* Garantir que o gráfico Plotly ocupe 100% da largura */
        .stPlotlyChart {
            width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Funções Auxiliares ---

# Função para formatar números para o padrão brasileiro
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float, arredonda e formata
        num = float(value)
        formatted_num = f"{num:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted_num} {unit}".strip()
    except (ValueError, TypeError):
        return "N/D"

# Função para carregar e processar arquivos CSV
@st.cache_data(ttl=3600) # Cache por 1 hora
def carregar_csv_caminho(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Encontra a linha de cabeçalho (primeira linha)
        header_line = lines[0]

        # Encontra e remove a linha de separação '| --- | --- | ... |'
        # Usamos um regex para ser mais flexível na identificação
        filtered_lines = [line for line in lines if not re.match(r'^\|\s*-+\s*(\|\s*-+\s*)*\|$', line.strip())]

        # Se a linha de cabeçalho foi removida por engano (ex: se o cabeçalho for igual ao separador),
        # ou se não há linhas suficientes, tentamos recuperar.
        if len(filtered_lines) < 2 and len(lines) >= 2: # Pelo menos cabeçalho e uma linha de dados
            filtered_lines = lines # Reverte para as linhas originais e tenta com skipinitialspace

        # Junta as linhas filtradas em uma única string para o pandas
        data_string = "".join(filtered_lines)

        # Tenta ler o CSV com pandas
        df = pd.read_csv(StringIO(data_string), sep='|', skipinitialspace=True)

        # Remove a primeira e a última coluna que geralmente são vazias devido ao separador '|'
        # Verifica se o DataFrame tem colunas suficientes antes de tentar fatiar
        if df.shape[1] > 2:
            df = df.iloc[:, 1:-1]
        else: # Se tiver 2 ou menos colunas, algo está errado, retorna vazio
            st.error(f"Erro: O arquivo '{os.path.basename(caminho_arquivo)}' não tem colunas suficientes após a leitura. Conteúdo: {data_string[:200]}...")
            return pd.DataFrame()

        # Limpa espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Mapeamento de nomes de colunas (do CSV para o padrão do dashboard)
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
            'cop': 'COP',
        }
        # Aplica o mapeamento apenas para colunas que existem no DataFrame
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # --- Criação da coluna 'DateTime' ---
        if 'Date' in df.columns and 'Time' in df.columns:
            # Garante que 'Date' e 'Time' são strings e substitui '/' por '-' em 'Date'
            df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
            df['Time'] = df['Time'].astype(str)

            # Tenta converter para datetime com formato específico, e se falhar, tenta inferir
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

            # Se a conversão com formato falhar para muitas linhas, tenta inferir
            if df['DateTime'].isnull().sum() > len(df) / 2: # Se mais da metade falhou
                df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

            df.dropna(subset=['DateTime'], inplace=True) # Remove linhas onde DateTime não pôde ser criado

            if df.empty:
                st.warning(f"Aviso: Nenhuma linha válida após a criação de 'DateTime' no arquivo '{os.path.basename(caminho_arquivo)}'.")
                return pd.DataFrame()
        else:
            st.error(f"Erro: Colunas 'Date' ou 'Time' não encontradas para criar 'DateTime' no arquivo '{os.path.basename(caminho_arquivo)}'. Colunas disponíveis: {df.columns.tolist()}")
            return pd.DataFrame()

        # --- Conversão de colunas numéricas ---
        numeric_cols = [col for col in df.columns if col not in ['Date', 'Time', 'DateTime']]
        for col in numeric_cols:
            # Converte vírgula para ponto e depois para numérico
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df.sort_values('DateTime').reset_index(drop=True)

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

# Função para listar arquivos CSV e extrair metadados
@st.cache_data(ttl=3600)
def listar_arquivos_csv(diretorio_base):
    arquivos_encontrados = []
    # Caminho para os arquivos de teste
    caminho_dados = os.path.join(diretorio_base, "dados_brutos", "historico_L1", "**", "*.csv")

    for caminho_completo in glob.glob(caminho_dados, recursive=True):
        nome_arquivo = os.path.basename(caminho_completo)

        # Expressão regular mais flexível para extrair informações
        # Captura: Ano, Mês, Dia, Hora, Operação (OP seguido de dígitos), Modelo (qualquer coisa depois de OP)
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", nome_arquivo)

        if match:
            ano, mes, dia, hora_str, operacao, modelo = match.groups()
            data_str = f"{dia}/{mes}/{ano}"
            hora_formatada = f"{hora_str[:2]}:{hora_str[2:]}"

            try:
                data_obj = datetime.strptime(f"{ano}-{mes}-{dia} {hora_formatada}", "%Y-%m-%d %H:%M")
            except ValueError:
                data_obj = None # Se a data/hora for inválida, define como None
        else:
            # Se o nome do arquivo não seguir o padrão, usa valores padrão
            ano, mes, dia, hora_formatada, operacao, modelo = "N/D", "N/D", "N/D", "N/D", "N/D", "N/D"
            data_str = "N/D"
            data_obj = None

        arquivos_encontrados.append({
            'caminho_completo': caminho_completo,
            'nome_arquivo': nome_arquivo,
            'modelo': modelo,
            'operacao': operacao,
            'ano': ano,
            'mes': mes,
            'dia': dia,
            'data': data_str,
            'hora': hora_formatada,
            'data_obj': data_obj # Para ordenação e filtro
        })

    # Ordena os arquivos pelo objeto de data, se disponível, ou pelo nome do arquivo
    arquivos_encontrados.sort(key=lambda x: x['data_obj'] if x['data_obj'] else datetime.min, reverse=True)

    return arquivos_encontrados

# --- Carregar todos os arquivos CSV disponíveis ---
# Usar o diretório atual do script como base
base_dir = os.path.dirname(os.path.abspath(__file__))
all_files_metadata = listar_arquivos_csv(base_dir)

# Extrair opções únicas para os filtros
all_modelos = sorted(list(set([a['modelo'] for a in all_files_metadata if a['modelo'] != 'N/D'])))
all_operacoes = sorted(list(set([a['operacao'] for a in all_files_metadata if a['operacao'] != 'N/D'])))
all_anos = sorted(list(set([a['ano'] for a in all_files_metadata if a['ano'] != 'N/D'])), reverse=True)
all_meses = sorted(list(set([a['mes'] for a in all_files_metadata if a['mes'] != 'N/D'])))

# --- Painel de Última Leitura Registrada ---
st.markdown(
    f"<p style='color: #00bfff; font-size: 1.5em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);'>Última Leitura Registrada</p>",
    unsafe_allow_html=True
)

arquivo_mais_recente = None
if all_files_metadata:
    # O primeiro arquivo na lista já é o mais recente devido à ordenação
    arquivo_mais_recente = all_files_metadata[0]

if arquivo_mais_recente:
    st.markdown(
        f"<p style='color: #e0e0e0; font-size: 1em;'>Arquivo: <span style='color: #00bfff;'>{arquivo_mais_recente['nome_arquivo']}</span></p>",
        unsafe_allow_html=True
    )

    ultima_leitura_str = "N/D"
    if arquivo_mais_recente['data_obj']:
        ultima_leitura_str = arquivo_mais_recente['data_obj'].strftime("%d/%m/%Y %H:%M")
    st.markdown(
        f"<p style='color: #e0e0e0; font-size: 1em;'>Última leitura: <span style='color: #00bfff;'>{ultima_leitura_str}</span></p>",
        unsafe_allow_html=True
    )

    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['caminho_completo'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha do DataFrame

        # Definir os títulos das métricas e suas unidades
        metric_titles = {
            "Ambiente": "T-Ambiente",
            "Entrada": "T-Entrada",
            "Saída": "T-Saída",
            "ΔT": "Dif",
            "Tensão": "Tensão",
            "Corrente": "Corrente",
            "Kcal/h": "Kcal/h",
            "Vazão": "Vazão",
            "Kw Aquecimento": "Kw Aquecimento",
            "Kw Consumo": "Kw Consumo",
            "COP": "COP",
        }
        metric_units = {
            "Ambiente": "°C", "Entrada": "°C", "Saída": "°C", "ΔT": "°C",
            "Tensão": "V", "Corrente": "A", "Kcal/h": "Kcal/h", "Vazão": "L/h",
            "Kw Aquecimento": "kW", "Kw Consumo": "kW", "COP": "",
        }
        metric_icons = {
            "Ambiente": "🌍", "Entrada": "➡️", "Saída": "⬅️", "ΔT": "🌡️",
            "Tensão": "⚡", "Corrente": "🔌", "Kcal/h": "🔥", "Vazão": "💧",
            "Kw Aquecimento": "♨️", "Kw Consumo": "💡", "COP": "📈",
        }

        # Organiza as métricas em 4 colunas para desktop, empilhando em mobile
        cols_metrics = st.columns(4)
        col_idx = 0

        for original_col, display_title in metric_titles.items():
            with cols_metrics[col_idx]:
                valor = ultima_linha.get(original_col, np.nan) # Usa .get para evitar KeyError
                display_value = format_br_number(valor, unit=metric_units.get(original_col, ""))
                icon = metric_icons.get(original_col, "📊")

                # Estilos específicos para T-Entrada e T-Saída
                if original_col == "Entrada":
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <h4>{display_title}</h4>
                            <span class="metric-icon">{icon}</span> <span class="temp-entrada-value">{display_value}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                elif original_col == "Saída":
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <h4>{display_title}</h4>
                            <span class="metric-icon">{icon}</span> <span class="temp-saida-value">{display_value}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <h4>{display_title}</h4>
                            <span class="metric-icon">{icon}</span> <span class="metric-value">{display_value}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            col_idx = (col_idx + 1) % 4 # Avança para a próxima coluna ou volta para a primeira
    else:
        st.error("Não foi possível carregar ou processar os dados do arquivo mais recente para o painel de última leitura.")
else:
    st.info("Nenhum arquivo CSV encontrado para exibir a última leitura.")

st.markdown("---") # Separador visual

# --- Título Principal ---
st.title("Máquina de Teste Fromtherm")

# --- Filtros de Arquivos (Sidebar) ---
st.sidebar.markdown(
    f"<p style='color: #00bfff; font-size: 1.2em; font-weight: bold;'>Filtros de Arquivos</p>",
    unsafe_allow_html=True
)

selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    ["Todos"] + all_modelos,
    key="filter_modelo"
)

# Filtra operações com base no modelo selecionado
filtered_operacoes = sorted(list(set([
    a['operacao'] for a in all_files_metadata
    if (selected_modelo == "Todos" or a['modelo'] == selected_modelo) and a['operacao'] != 'N/D'
])))
selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    ["Todos"] + filtered_operacoes,
    key="filter_operacao"
)

# Filtra anos com base no modelo e operação selecionados
filtered_anos = sorted(list(set([
    a['ano'] for a in all_files_metadata
    if (selected_modelo == "Todos" or a['modelo'] == selected_modelo) and
       (selected_operacao == "Todos" or a['operacao'] == selected_operacao) and
       a['ano'] != 'N/D'
])), reverse=True)
selected_ano = st.sidebar.selectbox(
    "Ano:",
    ["Todos"] + filtered_anos,
    key="filter_ano"
)

# Filtra meses com base no modelo, operação e ano selecionados
filtered_meses = sorted(list(set([
    a['mes'] for a in all_files_metadata
    if (selected_modelo == "Todos" or a['modelo'] == selected_modelo) and
       (selected_operacao == "Todos" or a['operacao'] == selected_operacao) and
       (selected_ano == "Todos" or a['ano'] == selected_ano) and
       a['mes'] != 'N/D'
])))
selected_mes = st.sidebar.selectbox(
    "Mês:",
    ["Todos"] + filtered_meses,
    key="filter_mes"
)

# --- Aplicar filtros aos arquivos ---
arquivos_filtrados = [
    a for a in all_files_metadata
    if (selected_modelo == "Todos" or a['modelo'] == selected_modelo) and
       (selected_operacao == "Todos" or a['operacao'] == selected_operacao) and
       (selected_ano == "Todos" or a['ano'] == selected_ano) and
       (selected_mes == "Todos" or a['mes'] == selected_mes)
]

# --- Exibição dos Arquivos Disponíveis (Área Principal) ---
st.subheader("Arquivos Disponíveis")

if arquivos_filtrados:
    # Exibe os botões em colunas, 3 por linha para desktop, empilhando em mobile
    cols_per_row = 3
    for i in range(0, len(arquivos_filtrados), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(arquivos_filtrados):
                arquivo = arquivos_filtrados[i + j]
                with cols[j]:
                    if st.button(arquivo['nome_arquivo'], key=f"file_button_{arquivo['nome_arquivo']}"):
                        st.session_state['selected_file_path'] = arquivo['caminho_completo']
                        st.session_state['selected_file_name'] = arquivo['nome_arquivo']
                        st.rerun() # Recarrega a página para exibir o arquivo selecionado
else:
    st.info("Nenhum arquivo encontrado com os filtros selecionados.")

# --- Visualização do Arquivo Selecionado ---
selected_file_path = st.session_state.get('selected_file_path', None)
selected_filename = st.session_state.get('selected_file_name', None)

if selected_file_path and selected_filename:
    st.markdown("---")
    st.subheader(f"Visualizando: {selected_filename}")

    df_dados = carregar_csv_caminho(selected_file_path)

    if not df_dados.empty:
        st.markdown("### Dados Brutos")
        st.dataframe(df_dados, use_container_width=True)

        # --- Botão de Exportar para Excel ---
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_dados.to_excel(writer, index=False, sheet_name='Dados Fromtherm')

            # Ajustar largura das colunas no Excel
            workbook = writer.book
            worksheet = writer.sheets['Dados Fromtherm']
            for col_idx, col_name in enumerate(df_dados.columns):
                if "Modelo" in col_name or "Operação" in col_name:
                    worksheet.set_column(col_idx, col_idx, 15)
                elif "Ambiente" in col_name or "Entrada" in col_name or "Saída" in col_name or "ΔT" in col_name:
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
