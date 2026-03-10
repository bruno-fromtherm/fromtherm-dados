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
        color: #00bfff; /* Azul Neon */
        border: 1px solid #00bfff;
        border-radius: 5px;
        padding: 10px 15px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 0 5px rgba(0, 191, 255, 0.3);
    }
    .stButton > button:hover {
        background-color: #004080; /* Azul um pouco mais claro no hover */
        color: #00ffff; /* Azul Neon mais claro */
        border-color: #00ffff;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }

    /* Estilo para a tabela de dados */
    .stDataFrame {
        background-color: rgba(0, 0, 0, 0.1); /* Fundo escuro translúcido */
        border-radius: 8px;
        padding: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stDataFrame .dataframe {
        background-color: transparent; /* Fundo da tabela transparente */
        color: #e0e0e0; /* Cor do texto da tabela */
    }
    .stDataFrame .dataframe th {
        background-color: #003366; /* Fundo do cabeçalho da tabela */
        color: #00bfff; /* Cor do texto do cabeçalho */
        border-bottom: 1px solid #00bfff;
    }
    .stDataFrame .dataframe td {
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Estilo para o multiselect */
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

    /* Responsividade para telas menores */
    @media (max-width: 768px) {
        .main > div {
            padding: 10px 15px 20px 15px;
        }
        h1 {
            font-size: 1.8em !important;
        }
        h2 {
            font-size: 1.4em !important;
        }
        .metric-card h4 {
            font-size: 0.9em;
        }
        .metric-card .metric-value {
            font-size: 1.3em;
        }
        /* Empilha os botões de arquivo */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button) {
            width: 100% !important;
            margin-bottom: 8px;
        }
        /* Empilha os cards de métricas */
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card) {
            width: 100% !important;
            margin-bottom: 8px;
        }
        /* Garante que os gráficos ocupem a largura total */
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.stPlotlyChart) {
            width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
#  Funções Auxiliares
# =========================

# Função para formatar números para o padrão brasileiro
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float, formata, e depois troca . por ,
        formatted_value = f"{float(value):,.{decimals}f}"
        return formatted_value.replace(",", "X").replace(".", ",").replace("X", ".") + unit
    except (ValueError, TypeError):
        return "N/D"

# Função para carregar e pré-processar o CSV
@st.cache_data(ttl=3600) # Cache para não recarregar o CSV toda hora
def carregar_csv_caminho(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        header_found = False
        data_started = False

        # Mapeamento de colunas para padronização
        column_mapping = {
            'date': 'Date', 'time': 'Time', 'ambiente': 'Ambiente',
            'entrada': 'Entrada', 'saida': 'Saída', 'dif': 'ΔT',
            'tensao': 'Tensão (V)', 'corrente': 'Corrente (A)', 'kcal/h': 'Kcal/h',
            'vazao': 'Vazão (L/h)', 'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo', 'cop': 'COP'
        }

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line: # Ignora linhas completamente vazias
                continue

            # Se a linha começa e termina com '|' e não é a linha de separação '---'
            if stripped_line.startswith('|') and stripped_line.endswith('|') and not re.match(r'^\|\s*-+\s*\|', stripped_line):
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                cleaned_parts = [p for p in parts if p] # Remove partes vazias resultantes de ||

                if not header_found and 'Date' in cleaned_parts and 'Time' in cleaned_parts: # Tenta identificar o cabeçalho
                    processed_lines.append(','.join(cleaned_parts))
                    header_found = True
                    data_started = True # Dados começam após o cabeçalho
                elif header_found and data_started: # Se o cabeçalho já foi encontrado, é uma linha de dados
                    processed_lines.append(','.join(cleaned_parts))
            elif header_found and data_started: # Se o cabeçalho foi encontrado e estamos em dados, mas a linha não tem barras (erro?)
                # Tenta processar como CSV normal se já estamos em dados
                processed_lines.append(stripped_line)

        if not processed_lines:
            st.error(f"Erro: O arquivo '{os.path.basename(caminho)}' está vazio ou não contém dados válidos após o pré-processamento.")
            return pd.DataFrame()

        # Unir as linhas processadas em uma única string para pd.read_csv
        csv_data_string = "\n".join(processed_lines)

        # Tenta ler o CSV com o novo formato de vírgulas
        df = pd.read_csv(StringIO(csv_data_string), sep=',', skipinitialspace=True)

        # Limpar espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Renomear colunas para o padrão esperado
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns.str.lower()})

        # Verificar se as colunas essenciais 'Date' e 'Time' existem após o renomeio
        if 'Date' not in df.columns or 'Time' not in df.columns:
            st.error(f"Erro: Colunas 'Date' ou 'Time' não encontradas no arquivo '{os.path.basename(caminho)}' após o pré-processamento e renomeio. Colunas disponíveis: {df.columns.tolist()}")
            return pd.DataFrame()

        # Criar coluna DateTime
        df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
        df['Time'] = df['Time'].astype(str)

        # Tenta converter para datetime com formato específico
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

        # Fallback para inferência se a conversão específica falhar para a maioria
        if df['DateTime'].isnull().sum() > len(df) / 2:
            st.warning(f"Aviso: Formato de data/hora específico falhou para a maioria das linhas em '{os.path.basename(caminho)}'. Tentando inferir o formato.")
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

        df.dropna(subset=['DateTime'], inplace=True)

        if df.empty:
            st.error(f"Erro: Nenhum dado válido com 'DateTime' pôde ser processado no arquivo '{os.path.basename(caminho)}'.")
            return pd.DataFrame()

        df.set_index('DateTime', inplace=True)
        df.sort_index(inplace=True)

        # Converter colunas numéricas (exceto Date, Time, DateTime)
        numeric_cols = [col for col in df.columns if col not in ['Date', 'Time']]
        for col in numeric_cols:
            if col in df.columns:
                # Substituir vírgula por ponto para conversão numérica
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except FileNotFoundError:
        st.error(f"Erro: Arquivo '{os.path.basename(caminho)}' não encontrado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(caminho)}': {e}")
        return pd.DataFrame()

# =========================
#  Listagem e Filtragem de Arquivos
# =========================

# Caminho base para os arquivos CSV
# Certifique-se de que este caminho está correto no Streamlit Share
# Use um caminho relativo ao diretório raiz do seu projeto no GitHub
BASE_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"
csv_files_path = os.path.join(BASE_DIR, "*.csv")

# Função para listar arquivos CSV
@st.cache_data(ttl=3600)
def listar_arquivos_csv(path):
    files = glob.glob(path)
    arquivos_info = []
    for f in files:
        filename = os.path.basename(f)
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", filename)
        if match:
            ano, mes, dia, hora, operacao, modelo = match.groups()
            data_str = f"{dia}/{mes}/{ano}"
            hora_str = f"{hora[:2]}:{hora[2:]}"
            try:
                data_obj = datetime.strptime(f"{ano}-{mes}-{dia} {hora[:2]}:{hora[2:]}", "%Y-%m-%d %H:%M")
            except ValueError:
                data_obj = None # Se a data/hora for inválida, define como None
            arquivos_info.append({
                'filename': filename,
                'path': f,
                'data': data_str,
                'hora': hora_str,
                'data_obj': data_obj,
                'operacao': operacao,
                'modelo': modelo
            })
        else:
            # st.warning(f"Arquivo '{filename}' não corresponde ao padrão esperado e será ignorado.")
            arquivos_info.append({
                'filename': filename,
                'path': f,
                'data': 'N/D',
                'hora': 'N/D',
                'data_obj': None,
                'operacao': 'N/D',
                'modelo': 'N/D'
            })

    # Ordenar por data_obj (mais recente primeiro), tratando None como o mais antigo
    arquivos_info.ordenar(key=lambda x: x['data_obj'] if x['data_obj'] is not None else datetime.min, reverse=True)
    return arquivos_info

# =========================
#  Layout da Sidebar
# =========================
st.sidebar.title("FromTherm")
st.sidebar.header("Filtros de Arquivos")

arquivos_disponiveis = listar_arquivos_csv(csv_files_path)

if not arquivos_disponiveis:
    st.sidebar.warning(f"Nenhum arquivo CSV encontrado no diretório especificado: `{BASE_DIR}`. Verifique o caminho e as permissões.")
    st.stop() # Para a execução se não houver arquivos

# Extrair opções únicas para os filtros
modelos = sorted(list(set([a['modelo'] for a in arquivos_disponiveis])))
operacoes = sorted(list(set([a['operacao'] for a in arquivos_disponiveis])))
anos = sorted(list(set([a['data'].split('/')[2] for a in arquivos_disponiveis if a['data'] != 'N/D'])), reverse=True)
meses = sorted(list(set([a['data'].split('/')[1] for a in arquivos_disponiveis if a['data'] != 'N/D'])))

# Adicionar opções "Todos"
modelos.insert(0, "Todos")
operacoes.insert(0, "Todos")
anos.insert(0, "Todos")
meses.insert(0, "Todos")

# Criar os filtros na sidebar
filtro_modelo = st.sidebar.selectbox("Modelo (ex: FT1165HBR):", modelos)
filtro_operacao = st.sidebar.selectbox("N° Operação (ex: OP987):", operacoes)
filtro_ano = st.sidebar.selectbox("Ano:", anos)
filtro_mes = st.sidebar.selectbox("Mês:", meses)

# Aplicar filtros
arquivos_filtrados = arquivos_disponiveis
if filtro_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == filtro_modelo]
if filtro_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == filtro_operacao]
if filtro_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data'].split('/')[2] == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data'].split('/')[1] == filtro_mes]

# =========================
#  Painel de Última Leitura Registrada
# =========================
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: 600;">Última Leitura Registrada</p>', unsafe_allow_html=True)

df_ultima_leitura = pd.DataFrame()
ultima_linha = {}
ultima_leitura_info = "N/D"
ultima_leitura_arquivo = "N/D"

if arquivos_filtrados:
    # O arquivo mais recente já está no topo da lista devido à ordenação em listar_arquivos_csv
    arquivo_mais_recente = arquivos_filtrados[0]
    ultima_leitura_arquivo = arquivo_mais_recente['filename']

    # Tenta carregar o CSV do arquivo mais recente
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['path'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1].to_dict()
        if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']):
            ultima_leitura_info = ultima_linha['DateTime'].strftime("%d/%m/%Y %H:%M")
        elif 'data_obj' in arquivo_mais_recente and arquivo_mais_recente['data_obj']:
            ultima_leitura_info = arquivo_mais_recente['data_obj'].strftime("%d/%m/%Y %H:%M")
        else:
            ultima_leitura_info = f"{arquivo_mais_recente['data']} {arquivo_mais_recente['hora']}"
    else:
        st.warning(f"Não foi possível carregar os dados do arquivo mais recente para o painel de última leitura: {ultima_leitura_arquivo}")
else:
    st.info("Nenhum arquivo disponível para exibir a última leitura.")

st.markdown(f'<p style="color: #e0e0e0; font-size: 1em;">Arquivo: <span style="color: #00bfff;">{ultima_leitura_arquivo}</span></p>', unsafe_allow_html=True)
st.markdown(f'<p style="color: #e0e0e0; font-size: 1em;">Última leitura: <span style="color: #00bfff;">{ultima_leitura_info}</span></p>', unsafe_allow_html=True)

# Exibir métricas da última leitura
if not df_ultima_leitura.empty and ultima_linha:
    metric_titles = {
        "Ambiente": "T-Ambiente", "Entrada": "T-Entrada", "Saída": "T-Saída", "ΔT": "ΔT",
        "Tensão (V)": "Tensão", "Corrente (A)": "Corrente", "Kcal/h": "Kcal/h",
        "Vazão (L/h)": "Vazão", "Kw Aquecimento": "Kw Aquecimento",
        "Kw Consumo": "Kw Consumo", "COP": "COP"
    }
    metric_units = {
        "Ambiente": " °C", "Entrada": " °C", "Saída": " °C", "ΔT": " °C",
        "Tensão (V)": " V", "Corrente (A)": " A", "Kcal/h": " Kcal/h",
        "Vazão (L/h)": " L/h", "Kw Aquecimento": " Kw",
        "Kw Consumo": " Kw", "COP": ""
    }

    cols_metrics = st.columns(4) # 4 colunas para desktop, empilha em mobile via CSS

    for i, (metric_name_df, display_title) in enumerate(metric_titles.items()):
        with cols_metrics[i % 4]:
            valor = ultima_linha.get(metric_name_df)
            display_value = format_br_number(valor, decimals=2, unit=metric_units.get(metric_name_df, ""))

            if metric_name_df == "Entrada":
                value_class = "temp-entrada-value"
            elif metric_name_df == "Saída":
                value_class = "temp-saida-value"
            else:
                value_class = "metric-value"

            st.markdown(
                f"""
                <div class="metric-card">
                    <h4>{display_title}</h4>
                    <p class="{value_class}">{display_value}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
else:
    st.warning("Não foi possível exibir as métricas da última leitura. Verifique o arquivo selecionado ou os dados.")


st.markdown("---") # Separador visual

# =========================
#  Visualização de Arquivos e Gráficos
# =========================
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: 600;">Máquina de Teste Fromtherm</p>', unsafe_allow_html=True)
st.subheader("Arquivos Disponíveis")

if arquivos_filtrados:
    # Cria botões para cada arquivo filtrado
    cols = st.columns(2) # 2 colunas para botões, empilha em mobile
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols[i % 2]:
            if st.button(f"{arquivo['filename']}", key=f"file_button_{arquivo['filename']}"):
                st.session_state['selected_file'] = arquivo['filename']
                st.session_state['selected_file_path'] = arquivo['path']
                st.session_state['selected_file_data_obj'] = arquivo['data_obj']
                st.rerun() # Recarrega a página para exibir o arquivo selecionado

    selected_filename = st.session_state.get('selected_file')
    selected_file_path = st.session_state.get('selected_file_path')

    if selected_filename and selected_file_path:
        st.markdown(f'<p style="color: #00bfff; font-size: 1.2em; border-bottom: 1px solid rgba(0, 191, 255, 0.3);">Visualizando: {selected_filename}</p>', unsafe_allow_html=True)

        df_graf = carregar_csv_caminho(selected_file_path)

        if not df_graf.empty:
            st.subheader("Dados Brutos")
            st.dataframe(df_graf)

            st.subheader("Gráfico de Tendência")

            # Exclui 'Date' e 'Time' (já que 'DateTime' é o índice)
            variaveis_opcoes = [col for col in df_graf.columns if col not in ['Date', 'Time']]

            if not variaveis_opcoes:
                st.warning("Nenhuma variável numérica disponível para plotar.")
            else:
                vars_selecionadas = st.multiselect(
                    "Selecione as variáveis para o gráfico:",
                    options=variaveis_opcoes,
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
        st.info("Por favor, selecione um arquivo na lista acima para visualizar os dados e gerar gráficos.")
else:
    st.warning("Nenhum arquivo disponível para seleção. Verifique os filtros ou o diretório de arquivos.")
