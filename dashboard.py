import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re # Importar re para expressões regulares

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# =========================
#  CSS GLOBAL (fundo + correção do "0")
# =========================
st.markdown(
    """
    <style>
    /* Fundo geral da página (tom próximo ao site Fromtherm) */
    .stApp {
        background-color: #f4f6f9;
    }

    /* Container principal - deixa conteúdo sobre "cartão branco" */
    .main > div {
        background-color: #ffffff;
        padding: 10px 25px 40px 25px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-top: 5px;
    }

    /* Título principal */
    h1 {
        color: #003366 !important;  /* azul escuro Fromtherm */
        font-weight: 800 !important;
        letter-spacing: 0.02em;
    }

    /* Linha abaixo do título */
    h1 + div {
        border-bottom: 1px solid #dde2eb;
        margin-bottom: 8px;
        padding-bottom: 4px;
    }

    /* Sidebar com leve separação */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #dde2eb;
    }

    /* Esconder qualquer pequeno span/ícone no topo esquerdo
       que esteja causando o "0" indesejado */
    div[data-testid="stAppViewContainer"] > div:first-child span {
        font-size: 0px !important;
        color: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_20260308_0939_OP987_FTA987BR.csv
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        # Ajustado para o novo padrão de nome de arquivo
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d{3})_(FTA\d{3}BR)\.csv", nome)

        if match:
            year_str, month_str, day_str, time_str, operacao, modelo = match.groups()

            try:
                data = datetime.strptime(f"{year_str}{month_str}{day_str}", "%Y%m%d").date()
                ano = int(year_str)
                mes = int(month_str)
                hora = f"{time_str[:2]}:{time_str[2:]}"
            except ValueError:
                data, ano, mes, hora = None, None, None, None
        else:
            data, ano, mes, hora, operacao, modelo = None, None, None, None, "N/D", "N/D"

        info_arquivos.append(
            {
                "nome_arquivo": nome,
                "caminho": caminho,
                "linha": "L1", # Hardcoded como L1, ajuste se for dinâmico
                "data": data,
                "ano": ano,
                "mes": mes,
                "hora": hora,
                "operacao": operacao,
                "modelo": modelo,
            }
        )

    return info_arquivos


# --- Função para carregar um CSV e processar (com tratamento aprimorado) ---
@st.cache_data(ttl=600) # Cache por 10 minutos
def carregar_csv_caminho(caminho: str) -> pd.DataFrame:
    try:
        # **Ajuste CRÍTICO AQUI:** Usando 'delim_whitespace=True' para múltiplos espaços
        # e 'decimal='.' para o separador decimal.
        df = pd.read_csv(caminho, delim_whitespace=True, decimal='.', encoding='utf-8')

        # Renomear colunas para o padrão esperado no dashboard
        # Certifique-se que esta lista de colunas corresponde EXATAMENTE ao seu CSV
        expected_columns = [
            "Date", "Time", "ambiente", "entrada", "saida", "dif",
            "tensao", "corrente", "kacl/h", "vazao", "kw aquecimento",
            "kw consumo", "cop"
        ]

        # Renomeia as colunas do DataFrame para os nomes esperados
        # Primeiro, limpa os nomes das colunas lidas para remover espaços extras
        df.columns = [col.strip() for col in df.columns]

        # Verifica se o número de colunas corresponde antes de renomear
        if len(df.columns) == len(expected_columns):
            df.columns = expected_columns
        else:
            st.warning(f"O número de colunas no arquivo {os.path.basename(caminho)} ({len(df.columns)}) não corresponde ao esperado ({len(expected_columns)}). As colunas podem estar incorretas.")
            st.info(f"Colunas lidas: {df.columns.tolist()}")
            st.info(f"Colunas esperadas: {expected_columns}")
            # Se não corresponder, podemos tentar mapear as que batem ou deixar como está
            # Por enquanto, vamos prosseguir e ver o que acontece.

        # Limpeza e conversão de tipos para numérico
        for col in df.columns:
            # Tentar converter para numérico (float)
            # 'errors='coerce'' transformará valores não numéricos em NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Combinar 'Date' e 'Time' em uma única coluna de datetime
        if 'Date' in df.columns and 'Time' in df.columns:
            # Ajuste o formato da data para 'YYYY/MM/DD HH:MM:SS' conforme o CSV
            df['DateTime'] = pd.to_datetime(
                df['Date'].astype(str) + ' ' + df['Time'].astype(str),
                errors='coerce',
                format='%Y/%m/%d %H:%M:%S' # Formato exato do seu CSV
            )
            df = df.drop(columns=['Date', 'Time']) # Remove as colunas originais
            # Mover 'DateTime' para o início do DataFrame
            cols = ['DateTime'] + [col for col in df.columns if col != 'DateTime']
            df = df[cols]

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo {caminho}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo .csv de histórico encontrado na pasta '{DADOS_DIR}'.")
    st.info("Verifique se os arquivos .csv foram sincronizados corretamente para o GitHub.")
    st.stop()

# --- Sidebar para filtros ---
st.sidebar.header("Filtros de Arquivos")

# Mapeamento de números de mês para nomes
mes_label_map = {
    1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
    5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
    9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
}

# Coleta de opções para os filtros
modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])))
meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
operacoes_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))

# Adiciona "Todos" como opção para os filtros
modelos_filtro = ["Todos"] + modelos_disponiveis
anos_filtro = ["Todos"] + anos_disponiveis
meses_filtro = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis]
operacoes_filtro = ["Todos"] + operacoes_disponiveis

# Filtros na sidebar
selected_modelo = st.sidebar.selectbox("Modelo (ex: FTA987BR):", modelos_filtro)
selected_ano = st.sidebar.selectbox("Ano:", anos_filtro)
selected_mes_label = st.sidebar.selectbox("Mês:", meses_filtro)
selected_operacao = st.sidebar.selectbox("Operação (ex: OP987_FTA987BR):", operacoes_filtro)

# Converte o label do mês de volta para número
selected_mes = None
if selected_mes_label != "Todos":
    selected_mes = int(selected_mes_label.split(" ")[0])

# Aplica os filtros
arquivos_filtrados = [
    a for a in todos_arquivos_info
    if (selected_modelo == "Todos" or a["modelo"] == selected_modelo) and
       (selected_ano == "Todos" or a["ano"] == selected_ano) and
       (selected_mes is None or a["mes"] == selected_mes) and
       (selected_operacao == "Todos" or a["operacao"] == selected_operacao)
]

st.sidebar.markdown("---")
st.sidebar.subheader("Arquivos Disponíveis")

if not arquivos_filtrados:
    st.sidebar.info("Nenhum arquivo encontrado com os filtros selecionados.")
else:
    # Armazena o arquivo selecionado na session_state
    if 'selected_file_path' not in st.session_state:
        st.session_state.selected_file_path = None

    for i, arquivo in enumerate(arquivos_filtrados):
        display_name = f"{arquivo['modelo']} - {arquivo['operacao']} - {arquivo['data'].strftime('%d/%m/%Y')} {arquivo['hora']}"
        if st.sidebar.button(display_name, key=f"file_button_{i}"):
            st.session_state.selected_file_path = arquivo['caminho']
            st.rerun() # Força a atualização para mostrar o arquivo selecionado

# =====================================================
#  ÁREA PRINCIPAL: Exibição do arquivo selecionado
# =====================================================

if st.session_state.selected_file_path:
    selected_file_path = st.session_state.selected_file_path
    selected_filename = os.path.basename(selected_file_path)

    st.subheader(f"Dados do Arquivo: {selected_filename}")

    df_dados = carregar_csv_caminho(selected_file_path)

    if not df_dados.empty:
        st.dataframe(df_dados, use_container_width=True)
    else:
        st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo no menu lateral para começar.")
