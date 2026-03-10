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
#  CSS GLOBAL (fundo + correção do "0" e responsividade)
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

    /* Estilo para os cards de métricas */
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-card h4 {
        color: #003366;
        font-size: 1.1em;
        margin-bottom: 5px;
    }
    /* Estilo para os valores dentro do st.metric */
    .st-emotion-cache-1r6dm1x { /* Alvo para o valor do st.metric */
        font-size: 1.5em;
        font-weight: bold;
        color: #333;
    }
    /* Estilo para o ícone dentro do st.metric */
    .st-emotion-cache-1r6dm1x svg { /* Alvo para o ícone do st.metric */
        font-size: 1.2em;
        margin-right: 5px;
    }

    /* Cores específicas para T-Entrada e T-Saída */
    .temp-entrada-value {
        color: #007bff; /* Azul */
        font-size: 1.5em;
        font-weight: bold;
    }
    .temp-saida-value {
        color: #dc3545; /* Vermelho */
        font-size: 1.5em;
        font-weight: bold;
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
        .st-emotion-cache-1r6dm1x, .temp-entrada-value, .temp-saida-value { /* Valor da métrica */
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
                hora = f"{time_str[:2]}:{time_str[2:]}"
            except ValueError:
                pass # Se a conversão de data/hora falhar, mantém como None

        info_arquivos.append(
            {
                "nome_arquivo": nome,
                "caminho": caminho,
                "linha": "L1", # Hardcoded como L1, ajuste se necessário
                "modelo": modelo,
                "operacao": operacao,
                "data": data,
                "ano": ano,
                "mes": mes,
                "hora": hora,
            }
        )

    # Ordena os arquivos pelo nome (que contém data e hora) para pegar o mais recente
    info_arquivos.sort(key=lambda x: x['nome_arquivo'], reverse=True)
    return info_arquivos


# --- Função para carregar e pré-processar o CSV ---
@st.cache_data(ttl=10)
def carregar_csv_caminho(caminho_arquivo):
    """
    Carrega um arquivo CSV, pré-processa as linhas, renomeia colunas,
    cria coluna DateTime e converte tipos.
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        header_found = False
        for line in lines:
            line = line.strip()
            if not line: # Ignora linhas vazias
                continue

            # Ignora a linha de separação de cabeçalho "| --- | --- |"
            if re.match(r"^\|\s*-+\s*(\|\s*-+\s*)*\|$", line):
                continue

            # Processa linhas que começam e terminam com '|'
            if line.startswith('|') and line.endswith('|'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if parts:
                    processed_lines.append(','.join(parts))
                    if not header_found: # A primeira linha processada é o cabeçalho
                        header_found = True
            else: # Adiciona linhas que não seguem o padrão '| ... |' diretamente, se houver
                processed_lines.append(line)

        if not processed_lines:
            st.error(f"O arquivo '{os.path.basename(caminho_arquivo)}' está vazio ou não contém dados válidos.")
            return pd.DataFrame()

        # Usa StringIO para ler as linhas processadas como um CSV
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
            'cop': 'COP'
        }

        # Renomeia as colunas existentes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Garante que as colunas Date e Time existam antes de tentar combiná-las
        if 'Date' in df.columns and 'Time' in df.columns:
            # Tenta converter a coluna 'Date' para o formato YYYY-MM-DD se estiver em YYYY/MM/DD
            df['Date'] = df['Date'].astype(str).str.replace('/', '-')

            # Combina 'Date' e 'Time' em uma única coluna 'DateTime'
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

            # Move 'DateTime' para a primeira coluna
            df = df[['DateTime'] + [col for col in df.columns if col != 'DateTime']]
        else:
            st.warning(f"Colunas 'Date' ou 'Time' não encontradas no arquivo '{os.path.basename(caminho_arquivo)}'. Gráficos podem não funcionar.")
            df['DateTime'] = pd.NaT # Not a Time

        # Converte colunas numéricas para float, tratando erros
        for col in df.columns:
            if col not in ['Date', 'Time', 'DateTime']: # Não tenta converter colunas de data/hora
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

# --- Função para formatar números para o padrão brasileiro ---
def format_br_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/D"
    # Formata para float com 2 casas decimais, depois converte para string
    # e substitui '.' por ',' para decimal, e adiciona '.' para milhar (se necessário)
    formatted_value = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted_value} {unit}"

# =====================================================
#  PAINEL: Última Leitura Registrada
# =====================================================
st.markdown('<h3 style="color: #003366;">Último Dashboard Enviado</h3>', unsafe_allow_html=True)

all_files_info = listar_arquivos_csv()
arquivo_mais_recente = all_files_info[0] if all_files_info else None

if arquivo_mais_recente:
    st.markdown(f'<p style="color: #333333;">Arquivo: <strong>{arquivo_mais_recente["nome_arquivo"]}</strong></p>', unsafe_allow_html=True)

    ultima_leitura_dt = "N/D"
    if arquivo_mais_recente['data'] and arquivo_mais_recente['hora']:
        ultima_leitura_dt = f"{arquivo_mais_recente['data'].strftime('%d/%m/%Y')} {arquivo_mais_recente['hora']}"
    st.markdown(f'<p style="color: #333333;">Última leitura: <strong>{ultima_leitura_dt}</strong></p>', unsafe_allow_html=True)

    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['caminho'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1].to_dict()

        # Mapeamento de métricas para exibição
        metric_display_info = {
            "T-Ambiente": {"label": "T-Ambiente", "icon": "🌍", "unit": "°C", "color_class": ""},
            "Tensão": {"label": "Tensão", "icon": "⚡", "unit": "V", "color_class": ""},
            "Corrente": {"label": "Corrente", "icon": "🔌", "unit": "A", "color_class": ""},
            "Kcal/h": {"label": "Kcal/h", "icon": "🔥", "unit": "Kcal/h", "color_class": ""},
            "Vazão": {"label": "Vazão", "icon": "💧", "unit": "L/h", "color_class": ""},
            "Kw Aquecimento": {"label": "Kw Aquecimento", "icon": "♨️", "unit": "kW", "color_class": ""},
            "Kw Consumo": {"label": "Kw Consumo", "icon": "💡", "unit": "kW", "color_class": ""},
            "COP": {"label": "COP", "icon": "📈", "unit": "", "color_class": ""},
            "ΔT": {"label": "ΔT", "icon": "🌡️", "unit": "°C", "color_class": ""},
            "Entrada": {"label": "T-Entrada", "icon": "➡️", "unit": "°C", "color_class": "temp-entrada-value"},
            "Saída": {"label": "T-Saída", "icon": "⬅️", "unit": "°C", "color_class": "temp-saida-value"},
        }

        # Organiza as métricas em 2 colunas para melhor visualização em mobile
        cols_metrics = st.columns(2)
        col_idx = 0

        for original_col_name in ["Ambiente", "Tensão", "Corrente", "Kcal/h", "Vazão", "Kw Aquecimento", "Kw Consumo", "COP", "ΔT", "Entrada", "Saída"]:
            if original_col_name in ultima_linha:
                valor = ultima_linha[original_col_name]
                display_info = metric_display_info.get(original_col_name, {})
                label = display_info.get("label", original_col_name)
                icon = display_info.get("icon", "")
                unit = display_info.get("unit", "")
                color_class = display_info.get("color_class", "")

                with cols_metrics[col_idx]:
                    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
                    st.markdown(f'<h4>{icon} {label}</h4>', unsafe_allow_html=True)

                    # Formata o valor usando a nova função
                    formatted_value = format_br_number(valor, decimals=2, unit=unit)

                    if color_class: # Se tiver classe de cor, usa markdown com span
                        st.markdown(f'<span class="{color_class}">{formatted_value}</span>', unsafe_allow_html=True)
                    else: # Caso contrário, usa st.markdown simples para o valor
                        st.markdown(f'<span style="font-size: 1.5em; font-weight: bold; color: #333;">{formatted_value}</span>', unsafe_allow_html=True)

                    st.markdown('</div>', unsafe_allow_html=True)

                col_idx = (col_idx + 1) % 2 # Alterna entre as duas colunas
    else:
        st.warning("Não foi possível carregar os dados da última leitura do arquivo mais recente.")
else:
    st.info("Nenhum arquivo de histórico encontrado para exibir a última leitura.")

st.markdown("---") # Separador visual

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# =====================================================
#  BARRA LATERAL: Filtros de Arquivos
# =====================================================
st.sidebar.header("Filtros de Arquivos")

# Inicializa selected_file_path se não existir
if 'selected_file_path' not in st.session_state:
    st.session_state.selected_file_path = None

# Obtém todos os arquivos para popular os filtros
all_files_for_filters = listar_arquivos_csv()

# Extrai opções únicas para os filtros
all_modelos = sorted(list(set(a["modelo"] for a in all_files_for_filters if a["modelo"] != "N/D")))
all_operacoes = sorted(list(set(a["operacao"] for a in all_files_for_filters if a["operacao"] != "N/D")))
all_anos = sorted(list(set(a["ano"] for a in all_files_for_filters if a["ano"] is not None)), reverse=True)
all_meses = sorted(list(set(a["mes"] for a in all_files_for_filters if a["mes"] is not None)))

# Adiciona "Todos" como opção padrão
modelos_opcoes = ["Todos"] + all_modelos
operacoes_opcoes = ["Todos"] + all_operacoes
anos_opcoes = ["Todos"] + [str(a) for a in all_anos]
meses_opcoes = ["Todos"] + [f"{m:02d}" for m in all_meses] # Formata mês com 2 dígitos

# Filtros na sidebar
selected_modelo = st.sidebar.selectbox("Modelo (ex: FTI165HBR):", modelos_opcoes, key="filter_modelo")

# Filtra operações com base no modelo selecionado
operacoes_filtradas_por_modelo = ["Todos"]
if selected_modelo != "Todos":
    operacoes_filtradas_por_modelo = sorted(list(set(a["operacao"] for a in all_files_for_filters if a["modelo"] == selected_modelo and a["operacao"] != "N/D")))
    operacoes_filtradas_por_modelo = ["Todos"] + operacoes_filtradas_por_modelo

selected_operacao = st.sidebar.selectbox("N° Operação (ex: OP987):", operacoes_filtradas_por_modelo, key="filter_operacao")

selected_ano = st.sidebar.selectbox("Ano:", anos_opcoes, key="filter_ano")
selected_mes = st.sidebar.selectbox("Mês:", meses_opcoes, key="filter_mes")

# Aplica os filtros aos arquivos
arquivos_filtrados = []
for arquivo in all_files_info:
    match_modelo = (selected_modelo == "Todos" or arquivo["modelo"] == selected_modelo)
    match_operacao = (selected_operacao == "Todos" or arquivo["operacao"] == selected_operacao)
    match_ano = (selected_ano == "Todos" or str(arquivo["ano"]) == selected_ano)
    match_mes = (selected_mes == "Todos" or f"{arquivo['mes']:02d}" == selected_mes) if arquivo['mes'] is not None else (selected_mes == "Todos")

    if match_modelo and match_operacao and match_ano and match_mes:
        arquivos_filtrados.append(arquivo)

# =====================================================
#  ÁREA PRINCIPAL: Arquivos Disponíveis (Botões)
# =====================================================
st.subheader("Arquivos Disponíveis")

if arquivos_filtrados:
    # Cria colunas para os botões de arquivo
    # O Streamlit já é responsivo, mas 3 colunas é um bom padrão para desktop
    # Em mobile, o CSS @media (max-width: 768px) fará com que se empilhem
    cols_buttons = st.columns(3) 

    for i, arquivo in enumerate(arquivos_filtrados):
        with cols_buttons[i % 3]: # Distribui os botões entre as 3 colunas
            display_name = arquivo['nome_arquivo'] # Exibe o nome original do arquivo
            if st.button(display_name, key=f"file_button_{i}"):
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
