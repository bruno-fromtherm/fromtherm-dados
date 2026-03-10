
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

    /* Cores especiais para T-Entrada e T-Saída */
    .temp-entrada-value {
        color: #00ffff !important; /* Azul Neon */
        font-weight: bold;
        text-shadow: 0 0 5px rgba(0, 255, 255, 0.7);
    }
    .temp-saida-value {
        color: #ff0000 !important; /* Vermelho Vibrante */
        font-weight: bold;
        text-shadow: 0 0 5px rgba(255, 0, 0, 0.7);
    }

    /* Botões de arquivo */
    .stButton > button {
        background-color: #003366; /* Azul escuro */
        color: #e0e0e0;
        border: 1px solid #00bfff; /* Borda azul neon */
        border-radius: 5px;
        padding: 8px 15px;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #004080; /* Azul mais claro no hover */
        border-color: #00ffff; /* Borda azul mais clara no hover */
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.5); /* Brilho no hover */
    }

    /* Tabela de dados */
    .stDataFrame {
        background-color: rgba(0, 0, 0, 0.1); /* Fundo escuro translúcido */
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stDataFrame table {
        color: #e0e0e0; /* Texto da tabela */
    }
    .stDataFrame th {
        background-color: rgba(0, 191, 255, 0.1); /* Cabeçalho da tabela azul neon translúcido */
        color: #00bfff; /* Texto do cabeçalho */
        font-weight: 600;
    }
    .stDataFrame tr:nth-child(even) {
        background-color: rgba(255, 255, 255, 0.02); /* Linhas pares mais claras */
    }
    .stDataFrame tr:nth-child(odd) {
        background-color: rgba(0, 0, 0, 0.05); /* Linhas ímpares mais escuras */
    }

    /* Multiselect para gráficos */
    .stMultiSelect > label {
        color: #00bfff; /* Rótulo do multiselect */
    }
    .stMultiSelect > div > div {
        background-color: #003366;
        color: #e0e0e0;
        border: 1px solid #00bfff;
    }
    .stMultiSelect > div > div > div > div > div {
        background-color: #003366; /* Opções selecionadas */
        color: #e0e0e0;
    }
    .stMultiSelect > div > div > div > div > div:hover {
        background-color: #004080;
    }
    .stMultiSelect > div > div > div > div > div > span {
        color: #e0e0e0;
    }

    /* Mensagens de alerta/info */
    .stAlert {
        background-color: rgba(0, 191, 255, 0.1);
        color: #00bfff;
        border-left: 5px solid #00bfff;
    }
    .stAlert > div > div > p {
        color: #e0e0e0 !important;
    }

    /* Responsividade para Mobile */
    @media (max-width: 768px) {
        .main > div {
            padding: 15px 20px 30px 20px; /* Reduz padding em mobile */
        }
        h1 {
            font-size: 1.8em !important; /* Reduz tamanho do título principal */
        }
        .metric-card h4 {
            font-size: 1em; /* Reduz tamanho do título da métrica */
        }
        .st-emotion-cache-1r6dm1x { /* Valor da métrica */
            font-size: 1.3em;
        }
        /* Empilha cards de métricas */
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card) {
            width: 100% !important;
            margin-bottom: 10px;
        }
        /* Empilha botões de arquivo */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button) {
            width: 100% !important;
            margin-bottom: 8px;
        }
        /* Gráficos ocupam 100% da largura */
        .stPlotlyChart {
            width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Funções Auxiliares ---

@st.cache_data(ttl=3600) # Cache para 1 hora
def listar_arquivos_csv(caminho_base):
    """Lista arquivos CSV, extrai metadados e ordena pelo mais recente."""
    arquivos_encontrados = []
    # Caminho para a pasta de dados brutos
    caminho_dados_brutos = os.path.join(caminho_base, 'dados_brutos')

    # Usar glob para encontrar todos os arquivos .csv recursivamente
    # Ajustado para buscar especificamente na estrutura de pastas que você mencionou
    # Ex: dados_brutos/historico_L1/IP_registro192.168.2.150/datalog/*.csv
    for root, _, files in os.walk(caminho_dados_brutos):
        for file in files:
            if file.endswith('.csv'):
                full_path = os.path.join(root, file)
                # Extrair informações do nome do arquivo
                # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
                match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", file)

                modelo = "N/D"
                operacao = "N/D"
                data_str = "N/D"
                hora_str = "N/D"
                data_obj = None

                if match:
                    ano, mes, dia, hora_min, op, mod = match.groups()
                    data_str = f"{dia}/{mes}/{ano}"
                    hora_str = f"{hora_min[:2]}:{hora_min[2:]}"
                    modelo = mod
                    operacao = op
                    try:
                        data_obj = datetime.strptime(f"{ano}-{mes}-{dia} {hora_min}", "%Y-%m-%d %H%M")
                    except ValueError:
                        pass # data_obj permanece None se houver erro

                arquivos_encontrados.append({
                    "nome_arquivo": file,
                    "caminho_completo": full_path,
                    "modelo": modelo,
                    "operacao": operacao,
                    "data": data_str,
                    "hora": hora_str,
                    "data_obj": data_obj # Para ordenação
                })

    # Ordenar os arquivos pelo mais recente primeiro
    arquivos_encontrados.sort(key=lambda x: x['data_obj'] if x['data_obj'] else datetime.min, reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=600) # Cache para 10 minutos
def carregar_csv_caminho(caminho_completo):
    """
    Carrega um arquivo CSV com separador '|', remove a linha de separação
    e padroniza os nomes das colunas.
    """
    try:
        # Ler o conteúdo do arquivo como uma string
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filtrar a linha de separação '| --- | --- | ... |' e linhas vazias
        filtered_lines = []
        header_line = ""
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line: # Ignorar linhas completamente vazias
                continue
            if re.match(r'^\|\s*-+\s*(\|\s*-+\s*)*\|$', stripped_line): # Linha de separação
                continue
            if i == 0: # Assumir que a primeira linha não filtrada é o cabeçalho
                header_line = stripped_line
            filtered_lines.append(stripped_line)

        if not filtered_lines:
            st.error(f"Erro: O arquivo '{os.path.basename(caminho_completo)}' está vazio ou não contém dados válidos.")
            return pd.DataFrame()

        # Juntar as linhas filtradas em uma única string para StringIO
        csv_content = "\n".join(filtered_lines)

        # Usar StringIO para ler com pandas
        df = pd.read_csv(StringIO(csv_content), sep='|', skipinitialspace=True)

        # Remover a primeira e a última coluna que podem ser vazias devido ao separador '|'
        # Verificar se há colunas suficientes antes de tentar remover
        if df.shape[1] > 2:
            df = df.iloc[:, 1:-1]
        elif df.shape[1] == 2: # Se só tiver 2 colunas, pode ser que uma seja o índice e outra o dado
            df = df.iloc[:, 1:] # Tenta remover a primeira
        else:
            st.error(f"Erro: O arquivo '{os.path.basename(caminho_completo)}' não tem colunas suficientes após a leitura. Conteúdo: {csv_content[:200]}...")
            return pd.DataFrame()

        # Limpar espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Mapeamento de nomes de colunas para padronização
        column_mapping = {
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
            'Date': 'Date', # Manter Date e Time como estão
            'Time': 'Time'
        }
        # Aplicar o mapeamento apenas para colunas existentes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # --- Criação da coluna DateTime ---
        if 'Date' in df.columns and 'Time' in df.columns:
            # Padronizar a coluna 'Date' para 'YYYY-MM-DD'
            df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
            df['Time'] = df['Time'].astype(str) # Garantir que Time é string

            # Tentar converter para datetime com formato específico
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

            # Se a maioria das conversões falhar, tentar inferir o formato
            if df['DateTime'].isnull().sum() > len(df) / 2:
                st.warning("Formato de data/hora '%Y-%m-%d %H:%M:%S' não funcionou para a maioria das linhas. Tentando inferir formato...")
                df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

            # Remover linhas onde DateTime não pôde ser criado
            df.dropna(subset=['DateTime'], inplace=True)

            if df.empty:
                st.error(f"Erro: Após processar 'Date' e 'Time', o DataFrame ficou vazio para '{os.path.basename(caminho_completo)}'.")
                return pd.DataFrame()
        else:
            st.error(f"Erro: Colunas 'Date' ou 'Time' não encontradas para criar 'DateTime' no arquivo '{os.path.basename(caminho_completo)}'. Colunas disponíveis: {df.columns.tolist()}")
            return pd.DataFrame()

        # --- Conversão de colunas numéricas ---
        # Lista de colunas que devem ser numéricas (usando os nomes padronizados)
        numeric_cols = [
            'Ambiente', 'Entrada', 'Saída', 'ΔT', 'Tensão', 'Corrente',
            'Kcal/h', 'Vazão', 'Kw Aquecimento', 'Kw Consumo', 'COP'
        ]
        for col in numeric_cols:
            if col in df.columns:
                # Substituir vírgula por ponto e converter para numérico
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        return pd.DataFrame()

def format_br_number(value, decimals=2, unit=""):
    """Formata um número para o padrão brasileiro (vírgula decimal, ponto de milhar)
    e trata valores NaN/None."""
    if pd.isna(value):
        return "N/D"

    # Formata o número com 2 casas decimais e ponto como separador de milhar
    # e vírgula como separador decimal
    formatted_value = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted_value} {unit}".strip()

# --- Carregar todos os arquivos CSV disponíveis ---
# Define o caminho base para a busca de arquivos
# Assumindo que o script está na raiz do repositório 'fromtherm-dados'
base_path = os.path.dirname(os.path.abspath(__file__))
all_files = listar_arquivos_csv(base_path)

# --- Sidebar para Filtros ---
st.sidebar.header("Filtros de Arquivos")

# Extrair todas as opções únicas para os filtros
all_modelos = sorted(list(set(f['modelo'] for f in all_files if f['modelo'] != "N/D")))
all_operacoes = sorted(list(set(f['operacao'] for f in all_files if f['operacao'] != "N/D")))
all_anos = sorted(list(set(f['data_obj'].year for f in all_files if f['data_obj'] is not None)), reverse=True)
all_meses = sorted(list(set(f['data_obj'].month for f in all_files if f['data_obj'] is not None)))

# Adicionar opção "Todos"
all_modelos.insert(0, "Todos")
all_operacoes.insert(0, "Todos")
all_anos.insert(0, "Todos")
all_meses.insert(0, "Todos")

selected_modelo = st.sidebar.selectbox("Modelo (ex: FTI165HBR):", all_modelos, key="modelo_filter")

# Filtrar operações com base no modelo selecionado
filtered_ops_by_model = [f['operacao'] for f in all_files if (selected_modelo == "Todos" or f['modelo'] == selected_modelo) and f['operacao'] != "N/D"]
unique_filtered_ops = sorted(list(set(filtered_ops_by_model)))
unique_filtered_ops.insert(0, "Todos")
selected_operacao = st.sidebar.selectbox("N° Operação (ex: OP987):", unique_filtered_ops, key="operacao_filter")

# Filtrar anos com base no modelo e operação
filtered_anos_by_selection = [f['data_obj'].year for f in all_files if 
                              (selected_modelo == "Todos" or f['modelo'] == selected_modelo) and
                              (selected_operacao == "Todos" or f['operacao'] == selected_operacao) and
                              f['data_obj'] is not None]
unique_filtered_anos = sorted(list(set(filtered_anos_by_selection)), reverse=True)
unique_filtered_anos.insert(0, "Todos")
selected_ano = st.sidebar.selectbox("Ano:", unique_filtered_anos, key="ano_filter")

# Filtrar meses com base no modelo, operação e ano
filtered_meses_by_selection = [f['data_obj'].month for f in all_files if 
                               (selected_modelo == "Todos" or f['modelo'] == selected_modelo) and
                               (selected_operacao == "Todos" or f['operacao'] == selected_operacao) and
                               (selected_ano == "Todos" or f['data_obj'].year == selected_ano) and
                               f['data_obj'] is not None]
unique_filtered_meses = sorted(list(set(filtered_meses_by_selection)))
unique_filtered_meses.insert(0, "Todos")
selected_mes = st.sidebar.selectbox("Mês:", unique_filtered_meses, key="mes_filter")

# Aplicar filtros aos arquivos
filtered_files = [f for f in all_files if
                  (selected_modelo == "Todos" or f['modelo'] == selected_modelo) and
                  (selected_operacao == "Todos" or f['operacao'] == selected_operacao) and
                  (selected_ano == "Todos" or (f['data_obj'] and f['data_obj'].year == selected_ano)) and
                  (selected_mes == "Todos" or (f['data_obj'] and f['data_obj'].month == selected_mes))]

# --- Painel de Última Leitura Registrada ---
st.markdown("<p style='color: #00bfff; font-size: 1.5em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);'>Última Leitura Registrada</p>", unsafe_allow_html=True)

df_ultima_leitura = pd.DataFrame()
ultima_linha = {}
ultima_leitura_data_hora_str = "N/D"
ultima_leitura_arquivo_nome = "N/D"

if filtered_files:
    # O arquivo mais recente já está no topo da lista 'filtered_files' devido à ordenação em listar_arquivos_csv
    arquivo_mais_recente = filtered_files[0]
    ultima_leitura_arquivo_nome = arquivo_mais_recente['nome_arquivo']

    # Tentar carregar o CSV do arquivo mais recente
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['caminho_completo'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1].to_dict() # Pega a última linha do DF
        if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']):
            ultima_leitura_data_hora_str = ultima_linha['DateTime'].strftime("%d/%m/%Y %H:%M:%S")
        else:
            st.warning("Coluna 'DateTime' não encontrada ou inválida na última leitura para o painel.")
    else:
        st.warning(f"Não foi possível carregar ou processar os dados do arquivo mais recente para o painel de última leitura: {ultima_leitura_arquivo_nome}")
else:
    st.info("Nenhum arquivo encontrado para exibir a última leitura.")

st.markdown(f"<p style='color: #e0e0e0; font-size: 0.9em;'>Arquivo: <span style='color: #00bfff;'>{ultima_leitura_arquivo_nome}</span></p>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #e0e0e0; font-size: 0.9em;'>Última leitura: <span style='color: #00bfff;'>{ultima_leitura_data_hora_str}</span></p>", unsafe_allow_html=True)

if not df_ultima_leitura.empty:
    # Definir os títulos, ícones e unidades das métricas
    metric_definitions = [
        ("Ambiente", "T-Ambiente", "🌡️", "°C"),
        ("Entrada", "T-Entrada", "➡️", "°C"),
        ("Saída", "T-Saída", "⬅️", "°C"),
        ("ΔT", "Dif", "🔥", "°C"),
        ("Tensão", "Tensão", "⚡", "V"),
        ("Corrente", "Corrente", "🔌", "A"),
        ("Kcal/h", "Kcal/h", "♨️", "Kcal/h"),
        ("Vazão", "Vazão", "💧", "L/h"),
        ("Kw Aquecimento", "Kw Aquecimento", "📈", "kW"),
        ("Kw Consumo", "Kw Consumo", "📉", "kW"),
        ("COP", "COP", "📊", ""),
    ]

    # Organizar as métricas em 4 colunas para desktop (e empilhar em mobile via CSS)
    cols_metrics = st.columns(4)

    for i, (col_name, display_title, icon, unit) in enumerate(metric_definitions):
        with cols_metrics[i % 4]: # Distribui em 4 colunas
            value = ultima_linha.get(col_name, np.nan) # Pega o valor, default é NaN
            formatted_value = format_br_number(value, decimals=2, unit=unit)

            # Estilo especial para T-Entrada e T-Saída
            if col_name == "Entrada":
                value_html = f"<span class='temp-entrada-value'>{formatted_value}</span>"
            elif col_name == "Saída":
                value_html = f"<span class='temp-saida-value'>{formatted_value}</span>"
            else:
                value_html = f"<span style='color: #e0e0e0; font-weight: bold;'>{formatted_value}</span>" # Cinza gelo para outros

            st.markdown(
                f"""
                <div class="metric-card">
                    <h4>{icon} {display_title}</h4>
                    <p style='font-size: 1.5em;'>{value_html}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
else:
    st.info("Não há dados de última leitura disponíveis para exibir as métricas.")

st.markdown("---")

# --- Título Principal ---
st.markdown("<h1>Máquina de Teste Fromtherm</h1>", unsafe_allow_html=True)

# --- Seção de Arquivos Disponíveis ---
st.subheader("Arquivos Disponíveis")

if filtered_files:
    # Exibir os arquivos filtrados como botões
    # Organizar em 3 colunas para desktop (e empilhar em mobile via CSS)
    cols = st.columns(3)
    for i, arquivo in enumerate(filtered_files):
        with cols[i % 3]:
            display_name = arquivo['nome_arquivo'] # Exibe o nome original do arquivo
            if st.button(display_name, key=f"file_button_{arquivo['nome_arquivo']}"):
                st.session_state['selected_file'] = arquivo['caminho_completo']
                st.session_state['selected_filename'] = arquivo['nome_arquivo']
                st.rerun() # Recarrega a página para exibir o arquivo selecionado
else:
    st.info("Nenhum arquivo CSV encontrado com os filtros aplicados.")

# --- Visualização do Arquivo Selecionado ---
if 'selected_file' in st.session_state and st.session_state['selected_file']:
    selected_file_path = st.session_state['selected_file']
    selected_filename = st.session_state['selected_filename']

    st.markdown(f"<p style='color: #00bfff; font-size: 1.2em; font-weight: bold;'>Visualizando: <span style='color: #e0e0e0;'>{selected_filename}</span></p>", unsafe_allow_html=True)

    df_dados = carregar_csv_caminho(selected_file_path)

    if not df_dados.empty:
        st.markdown("### Dados Brutos")
        st.dataframe(df_dados, use_container_width=True)

        # Botão de download para Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_dados.to_excel(writer, index=False, sheet_name='Dados')
        excel_buffer.seek(0)

        excel_file_name = selected_filename.replace('.csv', '.xlsx')
        st.download_button(
            label="Baixar como Excel",
            data=excel_buffer,
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
            variaveis_opcoes = [col for col col in df_graf.columns if col not in ['DateTime', 'Date', 'Time']]

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
