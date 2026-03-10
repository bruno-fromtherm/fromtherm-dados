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
        color: #e0e0e0; /* Cor do texto da tabela */
    }
    .stDataFrame .dataframe th {
        background-color: #003366; /* Cabeçalho da tabela */
        color: #00bfff;
        font-weight: bold;
    }
    .stDataFrame .dataframe td {
        background-color: rgba(0, 0, 0, 0.05); /* Células da tabela */
        border-color: rgba(255, 255, 255, 0.05);
    }

    /* Estilo para o multiselect do gráfico */
    div[data-testid="stMultiSelect"] > label {
        color: #00bfff; /* Rótulo do multiselect */
    }
    div[data-testid="stMultiSelect"] > div > div {
        background-color: #003366;
        color: #e0e0e0;
        border: 1px solid #00bfff;
    }
    div[data-testid="stMultiSelect"] .st-bh { /* Itens selecionados */
        background-color: #00bfff;
        color: #001a33;
    }
    div[data-testid="stMultiSelect"] .st-bh:hover {
        background-color: #00ffff;
    }
    div[data-testid="stMultiSelect"] .st-er { /* Opções do dropdown */
        background-color: #003366;
        color: #e0e0e0;
    }
    div[data-testid="stMultiSelect"] .st-er:hover {
        background-color: #004080;
    }

    /* Responsividade para Mobile */
    @media (max-width: 768px) {
        .main > div {
            padding: 10px 15px 20px 15px; /* Reduz padding em mobile */
        }
        h1 {
            font-size: 1.8em !important;
        }
        .metric-card h4 {
            font-size: 1em;
        }
        .metric-card .metric-value {
            font-size: 1.4em;
        }
        /* Empilha colunas de métricas */
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card) {
            width: 100% !important;
            margin-bottom: 10px;
        }
        /* Empilha botões de arquivo */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button) {
            width: 100% !important;
            margin-bottom: 8px;
        }
        /* Garante que gráficos ocupem a largura total */
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

# Função para listar arquivos CSV no diretório
@st.cache_data(ttl=3600) # Cache para não re-listar toda hora
def listar_arquivos_csv(base_path):
    all_files_info = []
    # Caminho para a pasta específica onde os CSVs estão
    search_path = os.path.join(base_path, 'dados_brutos', 'historico_L1', 'IP_registro192.168.2.150', 'datalog', '*.csv')

    # st.write(f"Procurando arquivos em: {search_path}") # Debug

    for f_path in glob.glob(search_path):
        filename = os.path.basename(f_path)
        # Exemplo: historico_L1_20260308_0939_OP987_FTA987BR.csv
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", filename)
        if match:
            ano, mes, dia, hora_str, operacao, modelo = match.groups()
            data_str = f"{ano}-{mes}-{dia}"
            hora_obj = datetime.strptime(hora_str, "%H%M").time()
            data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()

            all_files_info.append({
                "filename": filename,
                "filepath": f_path,
                "data_str": data_str,
                "data_obj": data_obj,
                "hora_str": hora_str,
                "hora_obj": hora_obj,
                "operacao": operacao,
                "modelo": modelo,
                "timestamp": datetime.combine(data_obj, hora_obj).timestamp() # Para ordenação
            })

    # Ordena os arquivos pelo timestamp (mais recente primeiro)
    all_files_info.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_files_info

# Função para carregar e pré-processar o CSV
@st.cache_data(ttl=600) # Cache para os dados do CSV
def carregar_csv_caminho(caminho):
    df = pd.DataFrame()
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        header_found = False
        header_line = ""

        # Encontrar o cabeçalho e processar as linhas
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line: # Ignorar linhas completamente vazias
                continue

            # Identifica a linha de separação e ignora
            if re.match(r'^\|-+\|-+\|.*\|$', stripped_line):
                continue

            # Se a linha começa e termina com '|' e ainda não encontramos o cabeçalho
            if stripped_line.startswith('|') and stripped_line.endswith('|'):
                # Remove as barras das extremidades e divide os valores
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]

                # Limpa espaços vazios (colunas vazias)
                cleaned_parts = [p for p in parts if p]

                if not header_found:
                    # Assume que a primeira linha válida é o cabeçalho
                    header_line = ','.join(cleaned_parts)
                    processed_lines.append(header_line)
                    header_found = True
                else:
                    # Adiciona as linhas de dados
                    processed_lines.append(','.join(cleaned_parts))

        if not processed_lines:
            st.error(f"Erro: O arquivo '{os.path.basename(caminho)}' está vazio ou não contém dados válidos após o pré-processamento.")
            return pd.DataFrame()

        # Converte as linhas processadas em um StringIO para o pandas ler
        data_io = StringIO('\n'.join(processed_lines))

        # Tenta ler o CSV com vírgula como separador
        df = pd.read_csv(data_io, sep=',')

        # Limpa espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Mapeamento de nomes de colunas para padronização
        column_mapping = {
            'date': 'Date', 'time': 'Time', 'ambiente': 'Ambiente',
            'entrada': 'Entrada', 'saida': 'Saída', 'dif': 'ΔT',
            'tensao': 'Tensão', 'corrente': 'Corrente', 'kacl/h': 'Kcal/h',
            'vazao': 'Vazão', 'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo', 'cop': 'COP'
        }
        # Renomeia colunas, ignorando chaves que não existem no df
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns.str.lower()})

        # Verifica se as colunas essenciais 'Date' e 'Time' existem após o renomeio
        if 'Date' not in df.columns or 'Time' not in df.columns:
            st.error(f"Erro: Colunas 'Date' ou 'Time' não encontradas no arquivo '{os.path.basename(caminho)}' após o pré-processamento e renomeio. Colunas disponíveis: {df.columns.tolist()}")
            return pd.DataFrame()

        # Converte 'Date' para formato YYYY-MM-DD
        df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
        df['Time'] = df['Time'].astype(str)

        # Cria a coluna DateTime
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

        # Fallback para inferência se o formato explícito falhar para a maioria
        if df['DateTime'].isnull().sum() > len(df) / 2:
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
            if df['DateTime'].isnull().sum() > len(df) / 2: # Se ainda falhar, mostra erro
                st.error(f"Erro: Não foi possível converter 'Date' e 'Time' para 'DateTime' no arquivo '{os.path.basename(caminho)}'. Verifique os formatos de data/hora. Exemplo de Date: {df['Date'].iloc[0]}, Exemplo de Time: {df['Time'].iloc[0]}")
                return pd.DataFrame()

        df.dropna(subset=['DateTime'], inplace=True) # Remove linhas com DateTime inválido
        df.set_index('DateTime', inplace=True) # Define DateTime como índice

        # Converte colunas numéricas, tratando vírgulas como decimais
        numeric_cols = [col for col in df.columns if col not in ['Date', 'Time']]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                )

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(caminho)}': {e}")
        return pd.DataFrame()

# =========================
#  Layout do Dashboard
# =========================

st.title("Máquina de Teste Fromtherm")

# --- Sidebar para filtros e seleção de arquivos ---
st.sidebar.header("Filtros de Arquivos")

all_files_info = listar_arquivos_csv("C:/FROMTHERM_REPOS/fromtherm-dados") # Caminho base
if not all_files_info:
    st.sidebar.warning("Nenhum arquivo CSV encontrado no diretório especificado.")
    st.stop() # Para a execução se não houver arquivos

# Extrair opções únicas para os filtros
modelos = sorted(list(set([f['modelo'] for f in all_files_info])))
operacoes = sorted(list(set([f['operacao'] for f in all_files_info])))
anos = sorted(list(set([f['data_obj'].year for f in all_files_info])), reverse=True)
meses = sorted(list(set([f['data_obj'].month for f in all_files_info])))

# Adicionar opções "Todos"
modelos.insert(0, "Todos")
operacoes.insert(0, "Todos")
anos.insert(0, "Todos")
meses.insert(0, "Todos")

# Widgets de filtro
filtro_modelo = st.sidebar.selectbox("Modelo (exc: FT1163HBR):", modelos)
filtro_operacao = st.sidebar.selectbox("N° Operação (exc: OP987):", operacoes)
filtro_ano = st.sidebar.selectbox("Ano:", anos)
filtro_mes = st.sidebar.selectbox("Mês:", meses)

# Aplicar filtros
arquivos_filtrados = all_files_info
if filtro_modelo != "Todos":
    arquivos_filtrados = [f for f in arquivos_filtrados if f['modelo'] == filtro_modelo]
if filtro_operacao != "Todos":
    arquivos_filtrados = [f for f in arquivos_filtrados if f['operacao'] == filtro_operacao]
if filtro_ano != "Todos":
    arquivos_filtrados = [f for f in arquivos_filtrados if f['data_obj'].year == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [f for f in arquivos_filtrados if f['data_obj'].month == filtro_mes]

# --- Painel de Última Leitura Registrada ---
st.markdown(f'<p style="color: #00bfff; font-size: 1.8em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Última Leitura Registrada</p>', unsafe_allow_html=True)

df_ultima_leitura = pd.DataFrame()
ultima_linha = {}
arquivo_mais_recente = None

if arquivos_filtrados:
    arquivo_mais_recente = arquivos_filtrados[0]
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['filepath'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1].to_dict()

        st.markdown(f'<p style="color: #e0e0e0; font-size: 1em;">Arquivo: <span style="color: #00bfff; font-weight: bold;">{arquivo_mais_recente["filename"]}</span></p>', unsafe_allow_html=True)

        if 'DateTime' in df_ultima_leitura.index:
            ultima_leitura_dt = df_ultima_leitura.index[-1]
            st.markdown(f'<p style="color: #e0e0e0; font-size: 1em;">Última leitura: <span style="color: #00bfff; font-weight: bold;">{ultima_leitura_dt.strftime("%d/%m/%Y %H:%M")}</span></p>', unsafe_allow_html=True)
        else:
            st.warning("Coluna 'DateTime' não encontrada no índice do DataFrame para a última leitura.")
    else:
        st.warning("Não foi possível carregar os dados do arquivo mais recente para o painel de última leitura.")
else:
    st.info("Nenhum arquivo encontrado para a última leitura com os filtros aplicados.")

# Exibir métricas da última leitura
if ultima_linha:
    cols_metrics = st.columns(4) # 4 colunas para desktop, CSS empilha em mobile

    metrics_to_display = [
        ("T-Ambiente", "Ambiente", "°C", "🌡️"),
        ("T-Entrada", "Entrada", "°C", "🔵"),
        ("T-Saída", "Saída", "°C", "🔴"),
        ("ΔT", "ΔT", "°C", "↔️"),
        ("Tensão", "Tensão", "V", "⚡"),
        ("Corrente", "Corrente", "A", "🔌"),
        ("Kcal/h", "Kcal/h", "", "🔥"),
        ("Vazão", "Vazão", "L/h", "💧"),
        ("Kw Aquecimento", "Kw Aquecimento", "kW", "♨️"),
        ("Kw Consumo", "Kw Consumo", "kW", "💡"),
        ("COP", "COP", "", "📈"),
    ]

    for i, (title, key, unit, icon) in enumerate(metrics_to_display):
        with cols_metrics[i % 4]:
            value = ultima_linha.get(key, np.nan)
            display_value = format_br_number(value, unit=unit)

            value_class = "metric-value"
            if key == "Entrada":
                value_class = "metric-value temp-entrada-value"
            elif key == "Saída":
                value_class = "metric-value temp-saida-value"

            st.markdown(
                f"""
                <div class="metric-card">
                    <h4>{icon} {title}</h4>
                    <span class="{value_class}">{display_value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
else:
    st.info("Nenhum dado disponível para a última leitura registrada.")

st.markdown("---") # Separador visual

# --- Seção de Visualização de Arquivos e Gráficos ---
st.markdown(f'<p style="color: #00bfff; font-size: 1.8em; font-weight: bold; text-shadow: 0 0 5px rgba(0, 191, 255, 0.5);">Arquivos Disponíveis</p>', unsafe_allow_html=True)

# Botões para selecionar arquivos
if arquivos_filtrados:
    # Cria um layout de colunas para os botões
    num_cols_buttons = 2 # 2 colunas para desktop, CSS empilha em mobile
    button_cols = st.columns(num_cols_buttons)

    selected_filename = None
    for i, file_info in enumerate(arquivos_filtrados):
        with button_cols[i % num_cols_buttons]:
            if st.button(
                f"{file_info['filename']} ({file_info['data_obj'].strftime('%d/%m/%Y')} {file_info['hora_str']})",
                key=f"select_file_{file_info['filename']}"
            ):
                selected_filename = file_info['filename']
                selected_file_path = file_info['filepath']
                # st.session_state['selected_file_path'] = selected_file_path # Armazena na sessão se necessário
                # st.session_state['selected_filename'] = selected_filename # Armazena na sessão se necessário
                break # Sai do loop após o primeiro botão clicado

    # Se um arquivo foi selecionado (ou se é a primeira carga e há arquivos)
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
        else: # Este else estava causando o SyntaxError
            st.warning("Não há dados válidos ou coluna 'DateTime' para gerar o gráfico.")

    else: # Este else estava causando o SyntaxError
        st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo na lista acima para visualizar os dados e gerar gráficos.")
