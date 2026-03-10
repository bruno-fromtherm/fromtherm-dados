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
    .stDataFrame .dataframe th {
        background-color: #003366; /* Cabeçalho da tabela */
        color: #00bfff;
        border-bottom: 1px solid #00bfff;
    }
    .stDataFrame .dataframe td {
        color: #e0e0e0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Estilo para o multiselect de variáveis do gráfico */
    .stMultiSelect > label {
        color: #00bfff; /* Rótulo azul neon */
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
        .metric-value, .temp-entrada-value, .temp-saida-value { /* Valor da métrica */
            font-size: 1.2em; /* Reduz o tamanho da fonte dos valores */
        }
        /* Força o empilhamento vertical de todos os elementos em colunas */
        div[data-testid="stVerticalBlock"] > div > div > div:has(button),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.metric-card),
        div[data-testid="stHorizontalBlock"] > div > div > div:has(.stPlotlyChart) {
            width: 100% !important; /* Faz os elementos ocuparem a largura total */
            margin-bottom: 10px; /* Adiciona espaçamento entre eles */
        }
        /* Garante que os gráficos ocupem 100% da largura */
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
st.sidebar.markdown("<h2 style='color: #00bfff;'>FromTherm</h2>", unsafe_allow_html=True)

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para formatar números para o padrão brasileiro ---
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    try:
        # Converte para float, arredonda e formata com vírgula decimal e ponto de milhar
        formatted_value = f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
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
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)

        # Padrão mais flexível para capturar OP e o final do nome
        # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
        # Ex: historico_L1_20260306_1717_OP9090_FT55L.csv
        # Ex: historico_L1_20260306_1717_OP9090_FT55L.csv (com .csvl no final)
        # Ajuste para o final do nome ser mais genérico e capturar o que vier depois de OP\d+
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9\._-]+)\.csv", nome)

        data, ano, mes, hora, operacao, modelo = None, None, None, None, "N/D", "N/D"

        if match:
            year_str, month_str, day_str, time_str, operacao, modelo = match.groups()
            try:
                data = datetime.strptime(f"{year_str}{month_str}{day_str}", "%Y%m%d").date()
                ano = int(year_str)
                mes = int(month_str)
                hora = time_str[:2] + ":" + time_str[2:] # Formata HH:MM
            except ValueError:
                pass # Se a data/hora não puder ser parseada, mantém como None

        info_arquivos.append({
            "nome_arquivo": nome,
            "caminho": caminho,
            "data": data,
            "ano": ano,
            "mes": mes,
            "hora": hora,
            "operacao": operacao,
            "modelo": modelo,
        })

    # Ordena os arquivos pelo nome (que geralmente inclui data/hora) para pegar o mais recente
    info_arquivos.sort(key=lambda x: x['nome_arquivo'], reverse=True)
    return info_arquivos


# --- Função para carregar e pré-processar o CSV ---
@st.cache_data(ttl=10)
def carregar_csv_caminho(caminho_arquivo):
    try:
        # Lê o arquivo linha por linha para pré-processamento
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        header_found = False
        for line in lines:
            line = line.strip()
            if not line: # Ignora linhas vazias
                continue

            # Detecta o cabeçalho (primeira linha que não é a linha de separação)
            if not header_found and not re.match(r"^\|-+\|-+", line):
                # Remove barras externas e espaços extras, substitui barras internas por vírgulas
                processed_line = re.sub(r'^\s*\|\s*|\s*\|\s*$', '', line) # Remove | do início/fim
                processed_line = re.sub(r'\s*\|\s*', ',', processed_line) # Substitui | por ,
                processed_lines.append(processed_line)
                header_found = True
            elif header_found and not re.match(r"^\|-+\|-+", line): # Ignora a linha de separação
                # Processa linhas de dados
                processed_line = re.sub(r'^\s*\|\s*|\s*\|\s*$', '', line)
                processed_line = re.sub(r'\s*\|\s*', ',', processed_line)
                processed_lines.append(processed_lines)

        if not processed_lines:
            st.error(f"O arquivo {os.path.basename(caminho_arquivo)} está vazio ou não contém dados válidos.")
            return pd.DataFrame()

        # Usa StringIO para ler o conteúdo processado como um CSV
        df = pd.read_csv(StringIO("\n".join(processed_lines)), sep=',', decimal='.', encoding='utf-8')

        # Mapeamento de nomes de colunas do CSV para nomes padronizados
        column_mapping = {
            'Date': 'Date',
            'Time': 'Time',
            'ambiente': 'Ambiente',
            'entrada': 'Entrada',
            'saida': 'Saída',
            'dif': 'ΔT', # Delta T
            'tensao': 'Tensão',
            'corrente': 'Corrente',
            'kacl/h': 'Kcal/h',
            'vazao': 'Vazão',
            'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo',
            'cop': 'COP',
        }

        # Renomeia as colunas existentes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Cria a coluna DateTime combinando 'Date' e 'Time'
        if 'Date' in df.columns and 'Time' in df.columns:
            # Tenta converter 'Date' para o formato YYYY-MM-DD se estiver em YYYY/MM/DD
            df['Date'] = df['Date'].astype(str).str.replace('/', '-')
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
        else:
            df['DateTime'] = pd.NaT # Not a Time se as colunas não existirem

        # Converte colunas numéricas para float, tratando erros
        numeric_cols = [col for col in df.columns if col not in ['Date', 'Time', 'DateTime']]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Substitui 000.0 ou 00000 por 0.0
            df[col] = df[col].replace(0, 0.0) 

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        return pd.DataFrame()


# =====================================================
#  PAINEL DE ÚLTIMA LEITURA REGISTRADA
# =====================================================
st.markdown("<h3 style='color: #00bfff;'>Último Dashboard Enviado:</h3>", unsafe_allow_html=True)

arquivos_disponiveis = listar_arquivos_csv()
arquivo_mais_recente = arquivos_disponiveis[0] if arquivos_disponiveis else None

if arquivo_mais_recente:
    st.markdown(f"<p style='color: #e0e0e0;'>Arquivo: {arquivo_mais_recente['nome_arquivo']}</p>", unsafe_allow_html=True)

    ultima_leitura_dt = "N/D"
    if arquivo_mais_recente['data'] and arquivo_mais_recente['hora']:
        ultima_leitura_dt = f"{arquivo_mais_recente['data'].strftime('%d/%m/%Y')} {arquivo_mais_recente['hora']}"
    st.markdown(f"<p style='color: #e0e0e0;'>Última leitura: {ultima_leitura_dt}</p>", unsafe_allow_html=True)

    df_recente = carregar_csv_caminho(arquivo_mais_recente['caminho'])

    if not df_recente.empty:
        ultima_linha = df_recente.iloc[-1] # Pega a última linha do DataFrame

        # Definição das métricas a serem exibidas e suas unidades
        metrics_to_display = [
            ("Ambiente", "Ambiente", "°C", "🌡️"),
            ("T-Entrada", "Entrada", "°C", "➡️"),
            ("T-Saída", "Saída", "°C", "⬅️"),
            ("ΔT", "ΔT", "°C", "↔️"),
            ("Tensão", "Tensão", "V", "⚡"),
            ("Corrente", "Corrente", "A", "🔌"),
            ("Kcal/h", "Kcal/h", "Kcal/h", "🔥"),
            ("Vazão", "Vazão", "L/h", "💧"),
            ("Kw Aquecimento", "Kw Aquecimento", "kW", "♨️"),
            ("Kw Consumo", "Kw Consumo", "kW", "💡"),
            ("COP", "COP", "", "✅"),
        ]

        # Organiza as métricas em 4 colunas para desktop, empilhando em mobile
        cols_metrics = st.columns(4) 

        for i, (title, col_name, unit, icon) in enumerate(metrics_to_display):
            with cols_metrics[i % 4]: # Usa o módulo para distribuir em 4 colunas
                valor = ultima_linha.get(col_name, np.nan) # Pega o valor, default NaN se não existir
                display_value = format_br_number(valor, unit=unit)

                # Customiza a exibição para T-Entrada e T-Saída com cores e ícones específicos
                if col_name == "Entrada":
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <h4>{title}</h4>
                            <span class="temp-entrada-value">{icon} {display_value}</span>
                        </div>
                        """, unsafe_allow_html=True
                    )
                elif col_name == "Saída":
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <h4>{title}</h4>
                            <span class="temp-saida-value">{icon} {display_value}</span>
                        </div>
                        """, unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <h4>{title}</h4>
                            <span class="metric-icon">{icon}</span> <span class="metric-value">{display_value}</span>
                        </div>
                        """, unsafe_allow_html=True
                    )
    else:
        st.warning("Não foi possível carregar os dados do arquivo mais recente para o painel de última leitura.")
else:
    st.info("Nenhum arquivo CSV encontrado na pasta de dados para exibir a última leitura.")

st.markdown("---") # Separador visual

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# =====================================================
#  FILTROS DE ARQUIVOS (Sidebar)
# =====================================================
st.sidebar.markdown("<h3 style='color: #00bfff;'>Filtros de Arquivos:</h3>", unsafe_allow_html=True)

# Coleta todas as opções de filtros
all_modelos = sorted(list(set(a["modelo"] for a in arquivos_disponiveis if a["modelo"] != "N/D")))
all_operacoes = sorted(list(set(a["operacao"] for a in arquivos_disponiveis if a["operacao"] != "N/D")))
all_anos = sorted(list(set(a["ano"] for a in arquivos_disponiveis if a["ano"] is not None)), reverse=True)
all_meses = sorted(list(set(a["mes"] for a in arquivos_disponiveis if a["mes"] is not None)))

# Adiciona "Todos" como opção padrão
modelos_filtro_opcoes = ["Todos"] + all_modelos
operacoes_filtro_opcoes = ["Todos"] + all_operacoes
anos_filtro_opcoes = ["Todos"] + all_anos
meses_filtro_opcoes = ["Todos"] + all_meses

# Filtro: Modelo
selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    modelos_filtro_opcoes,
    key="modelo_filter"
)

# Filtro: N° Operação (dinâmico baseado no modelo)
# Filtra as operações que correspondem ao modelo selecionado
if selected_modelo != "Todos":
    operacoes_para_modelo = sorted(list(set(a["operacao"] for a in arquivos_disponiveis if a["modelo"] == selected_modelo and a["operacao"] != "N/D")))
    operacoes_filtro_opcoes_dinamico = ["Todos"] + operacoes_para_modelo
else:
    operacoes_filtro_opcoes_dinamico = operacoes_filtro_opcoes

selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    operacoes_filtro_opcoes_dinamico,
    key="operacao_filter"
)

# Filtro: Ano
selected_ano = st.sidebar.selectbox(
    "Ano:",
    anos_filtro_opcoes,
    key="ano_filter"
)

# Filtro: Mês
selected_mes = st.sidebar.selectbox(
    "Mês:",
    meses_filtro_opcoes,
    format_func=lambda x: datetime(2000, x, 1).strftime("%B") if x != "Todos" else "Todos", # Mostra nome do mês
    key="mes_filter"
)

# Aplica os filtros
arquivos_filtrados = []
for arquivo in arquivos_disponiveis:
    match_modelo = (selected_modelo == "Todos") or (arquivo["modelo"] == selected_modelo)
    match_operacao = (selected_operacao == "Todos") or (arquivo["operacao"] == selected_operacao)
    match_ano = (selected_ano == "Todos") or (arquivo["ano"] == selected_ano)
    match_mes = (selected_mes == "Todos") or (arquivo["mes"] == selected_mes)

    if match_modelo and match_operacao and match_ano and match_mes:
        arquivos_filtrados.append(arquivo)

# =====================================================
#  LISTA DE ARQUIVOS DISPONÍVEIS (Área Principal)
# =====================================================
st.markdown("---")
st.subheader("Arquivos Disponíveis")

if arquivos_filtrados:
    # Inicializa selected_file_path na session_state se não existir
    if 'selected_file_path' not in st.session_state:
        st.session_state.selected_file_path = None

    # Exibe os botões de arquivo em colunas
    cols_arquivos = st.columns(3) # 3 colunas para desktop, empilha em mobile
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols_arquivos[i % 3]: # Distribui os botões em 3 colunas
            display_name = arquivo['nome_arquivo'] # Exibe o nome original do arquivo
            if st.button(display_name, key=f"file_button_{arquivo['nome_arquivo']}"):
                st.session_state.selected_file_path = arquivo['caminho']
                st.rerun() # Força a atualização para mostrar o arquivo selecionado
else:
    st.info("Nenhum arquivo encontrado com os filtros selecionados.")

# =====================================================
#  ÁREA PRINCIPAL: Exibição do arquivo selecionado (Tabela e Gráfico)
# =====================================================

if st.session_state.selected_file_path:
    selected_file_path = st.session_state.selected_file_path
    selected_filename = os.path.basename(selected_file_path)

    st.markdown("---")
    st.subheader(f"Visualizando: {selected_filename}")

    df_dados = carregar_csv_caminho(selected_file_path)

    if not df_dados.empty:
        st.write("### Tabela de Dados")
        st.dataframe(df_dados, use_container_width=True)

        # Botão de download para Excel
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
