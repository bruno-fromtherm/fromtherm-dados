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
    .stDataFrame div[data-testid="stTable"] div[role="rowheader"] div {
        font-weight: bold;
    }
    .stDataFrame div[data-testid="stTable"] div[role="columnheader"] div {
        color: #00bfff; /* Cor do cabeçalho da tabela */
        font-weight: bold;
        background-color: rgba(0, 191, 255, 0.05);
        border-bottom: 1px solid rgba(0, 191, 255, 0.2);
    }

    /* Responsividade para telas menores */
    @media (max-width: 768px) {
        .main > div {
            padding: 10px 15px 20px 15px;
        }
        h1 {
            font-size: 1.8em !important;
        }
        .metric-card h4 {
            font-size: 0.9em;
        }
        .metric-card .metric-value {
            font-size: 1.3em;
        }
        /* Empilha os cards de métricas */
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card) {
            width: 100% !important;
            margin-bottom: 10px;
        }
        /* Empilha os botões de arquivo */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button) {
            width: 100% !important;
            margin-bottom: 5px;
        }
        /* Empilha os gráficos */
        .stPlotlyChart {
            width: 100% !important;
        }
    }
    </style>
    """
)

# --- Funções Auxiliares ---

# Mapeamento de nomes de colunas do CSV para nomes padronizados no dashboard
column_mapping = {
    'date': 'Date', 'time': 'Time', 'ambiente': 'Ambiente', 'entrada': 'Entrada',
    'saida': 'Saída', 'dif': 'ΔT', 'tensao': 'Tensão', 'corrente': 'Corrente',
    'kacl/h': 'Kcal/h', 'vazao': 'Vazão', 'kw aquecimento': 'Kw Aquecimento',
    'kw consumo': 'Kw Consumo', 'cop': 'COP'
}

def format_br_number(value, decimals=2, unit=""):
    """Formata um número para o padrão brasileiro (vírgula decimal, ponto de milhar)
       e trata valores NaN."""
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float, formata, e substitui . por ,
        formatted_value = f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted_value} {unit}".strip()
    except (ValueError, TypeError):
        return "N/D"

@st.cache_data(ttl=3600) # Cache para evitar recarregar o CSV toda vez
def carregar_csv_caminho(file_path):
    """
    Carrega um arquivo CSV, pré-processa para remover a linha de separação e
    garante que as colunas Date e Time sejam usadas para criar DateTime.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        header_found = False
        data_started = False

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line: # Ignora linhas completamente vazias
                continue

            # Identifica a linha de cabeçalho (primeira linha que começa e termina com | e contém 'Date')
            if not header_found and stripped_line.startswith('|') and stripped_line.endswith('|') and 'Date' in stripped_line:
                # Remove as barras das extremidades e divide os valores
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                # Limpa espaços vazios e junta tudo com VÍRGULA
                cleaned_parts = [p for p in parts if p]
                processed_lines.append(','.join(cleaned_parts))
                header_found = True
                continue

            # Ignora a linha de separação |---|---|...
            if re.match(r'^\|-+\|-+\|.*\|$', stripped_line):
                continue

            # Processa as linhas de dados (após o cabeçalho e a linha de separação)
            if header_found and stripped_line.startswith('|') and stripped_line.endswith('|'):
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                cleaned_parts = [p for p in parts if p]
                processed_lines.append(','.join(cleaned_parts))
                data_started = True # Indica que começamos a coletar dados

        if not processed_lines:
            st.error(f"Erro: O arquivo '{os.path.basename(file_path)}' está vazio ou não contém dados válidos após o pré-processamento.")
            return pd.DataFrame()

        # Converte as linhas processadas em um StringIO para o pandas ler como CSV
        csv_data = StringIO('\n'.join(processed_lines))
        df = pd.read_csv(csv_data, sep=',')

        # Limpa espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Renomeia colunas para o padrão esperado
        df = df.rename(columns={k.lower(): v for k, v in column_mapping.items() if k.lower() in df.columns})

        # Verifica se as colunas essenciais 'Date' e 'Time' existem após o renomeio
        if 'Date' not in df.columns or 'Time' not in df.columns:
            st.error(f"Erro: O arquivo '{os.path.basename(file_path)}' não tem as colunas 'Date' ou 'Time' após o pré-processamento e renomeio. Colunas encontradas: {df.columns.tolist()}")
            return pd.DataFrame()

        # Garante que 'Date' e 'Time' são strings
        df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
        df['Time'] = df['Time'].astype(str)

        # Tenta criar a coluna 'DateTime'
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

        # Fallback para inferência se o formato específico falhar para a maioria
        if df['DateTime'].isnull().sum() > len(df) / 2:
            st.warning(f"Aviso: Formato de data/hora específico falhou para a maioria das linhas em '{os.path.basename(file_path)}'. Tentando inferir o formato.")
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

        df.dropna(subset=['DateTime'], inplace=True)

        if df.empty:
            st.error(f"Erro: O arquivo '{os.path.basename(file_path)}' não contém dados válidos de data/hora após o processamento.")
            return pd.DataFrame()

        # Converte colunas numéricas, tratando vírgulas como decimais
        numeric_cols = [col for col in df.columns if col not in ['Date', 'Time', 'DateTime']]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df.set_index('DateTime').sort_index()

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(file_path)}': {e}")
        return pd.DataFrame()


# --- Listar arquivos CSV disponíveis ---
def listar_arquivos_csv(base_path):
    arquivos_encontrados = []
    # Caminho para os arquivos CSV dentro da estrutura
    search_path = os.path.join(base_path, 'dados_brutos', 'historico_L1', '*', 'datalog', '*.csv')

    for file_path in glob.glob(search_path, recursive=True):
        filename = os.path.basename(file_path)
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", filename)
        if match:
            ano, mes, dia, hora, operacao, modelo = match.groups()
            data_str = f"{ano}-{mes}-{dia} {hora[:2]}:{hora[2:]}:00"
            try:
                data_obj = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                data_obj = None # Caso a data/hora não seja válida

            arquivos_encontrados.append({
                'filename': filename,
                'file_path': file_path,
                'data_obj': data_obj,
                'modelo': modelo,
                'operacao': operacao,
                'ano': ano,
                'mes': mes
            })

    # Ordena os arquivos pelo mais recente primeiro
    arquivos_encontrados.sort(key=lambda x: x['data_obj'] if x['data_obj'] else datetime.min, reverse=True)
    return arquivos_encontrados

# --- Interface do Streamlit ---

st.title("Máquina de Teste Fromtherm")

# --- Sidebar para filtros ---
st.sidebar.header("Filtros de Arquivos")

# Carrega a lista de arquivos
base_dir = os.path.dirname(__file__) # Pega o diretório atual do script
arquivos_csv = listar_arquivos_csv(base_dir)

if not arquivos_csv:
    st.sidebar.warning("Nenhum arquivo CSV encontrado na estrutura esperada.")
    st.stop() # Para a execução se não houver arquivos

# Extrai opções únicas para os filtros
modelos = sorted(list(set([a['modelo'] for a in arquivos_csv])))
operacoes = sorted(list(set([a['operacao'] for a in arquivos_csv])))
anos = sorted(list(set([a['ano'] for a in arquivos_csv])))
meses = sorted(list(set([a['mes'] for a in arquivos_csv])))

# Adiciona opções "Todos"
modelos.insert(0, "Todos")
operacoes.insert(0, "Todos")
anos.insert(0, "Todos")
meses.insert(0, "Todos")

# Cria os seletores na sidebar
filtro_modelo = st.sidebar.selectbox("Modelo (exc: FT1163HBR):", modelos)
filtro_operacao = st.sidebar.selectbox("N° Operação (exc: OP987):", operacoes)
filtro_ano = st.sidebar.selectbox("Ano:", anos)
filtro_mes = st.sidebar.selectbox("Mês:", meses)

# Aplica os filtros
arquivos_filtrados = arquivos_csv
if filtro_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == filtro_modelo]
if filtro_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == filtro_operacao]
if filtro_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == filtro_mes]

# --- Painel de Última Leitura Registrada ---
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Última Leitura Registrada</p>', unsafe_allow_html=True)

df_ultima_leitura = pd.DataFrame()
ultima_linha = {}
ultima_leitura_info = "N/D"

if arquivos_csv: # Usa a lista completa de arquivos para a última leitura
    arquivo_mais_recente = arquivos_csv[0]
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['file_path'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1].to_dict() # Pega a última linha
        if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']):
            ultima_leitura_info = f"{ultima_linha['DateTime'].strftime('%d/%m/%Y %H:%M:%S')} - {arquivo_mais_recente['filename']}"
        else:
            ultima_leitura_info = f"Data/Hora N/D - {arquivo_mais_recente['filename']}"
    else:
        st.error(f"Não foi possível carregar os dados do arquivo mais recente para o painel de última leitura: {arquivo_mais_recente['filename']}")
else:
    st.info("Nenhum arquivo disponível para a última leitura.")

st.markdown(f'<p style="color: #e0e0e0; font-size: 1em;">{ultima_leitura_info}</p>', unsafe_allow_html=True)

if not df_ultima_leitura.empty:
    col1, col2, col3, col4 = st.columns(4) # 4 colunas para desktop, empilha em mobile

    # Métricas e suas unidades
    metrics_display = [
        ("T-Ambiente", "Ambiente", "°C", "🌡️"),
        ("T-Entrada", "Entrada", "°C", "➡️", "temp-entrada-value"),
        ("T-Saída", "Saída", "°C", "⬅️", "temp-saida-value"),
        ("ΔT", "ΔT", "°C", "↔️"),
        ("Tensão", "Tensão", "V", "⚡"),
        ("Corrente", "Corrente", "A", " 전류"), # Ícone de corrente
        ("Kcal/h", "Kcal/h", "Kcal/h", "🔥"),
        ("Vazão", "Vazão", "L/h", "💧"),
        ("Kw Aquecimento", "Kw Aquecimento", "kW", "♨️"),
        ("Kw Consumo", "Kw Consumo", "kW", "💡"),
        ("COP", "COP", "", "📈"),
    ]

    cols_metrics = st.columns(4) # Define 4 colunas para as métricas

    for i, (title, metric_name, unit, icon, css_class) in enumerate(metrics_display):
        with cols_metrics[i % 4]: # Distribui as métricas nas 4 colunas
            value = ultima_linha.get(metric_name, np.nan)
            display_value = format_br_number(value, 2, unit)

            # Usa st.markdown para controle total sobre o estilo
            value_class = f"metric-value {css_class}" if css_class else "metric-value"
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
    st.info("Nenhum dado disponível para a última leitura registrada.")

st.markdown("---") # Separador visual

# --- Visualização de Arquivos Disponíveis e Gráficos ---
st.markdown('<p style="color: #00bfff; font-size: 1.5em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Arquivos Disponíveis</p>', unsafe_allow_html=True)

if arquivos_filtrados:
    # Cria botões para cada arquivo filtrado
    selected_filename = None
    cols_buttons = st.columns(2) # 2 colunas para os botões de arquivo

    for i, arquivo in enumerate(arquivos_filtrados):
        with cols_buttons[i % 2]:
            if st.button(f"{arquivo['filename']} ({arquivo['data_obj'].strftime('%d/%m/%Y %H:%M') if arquivo['data_obj'] else 'N/D'})", key=arquivo['filename']):
                selected_filename = arquivo['filename']
                selected_file_path = arquivo['file_path']

    if selected_filename:
        st.markdown(f'<p style="color: #00bfff; font-size: 1.2em; font-weight: bold; text-shadow: 0 0 3px rgba(0, 191, 255, 0.3);">Visualizando: {selected_filename}</p>', unsafe_allow_html=True)

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
            st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo na lista acima para visualizar os dados e gerar gráficos.")
