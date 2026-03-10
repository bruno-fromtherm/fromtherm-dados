import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from io import BytesIO, StringIO
import plotly.express as px
import re

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
    .temp-entrada {
        color: #007bff; /* Azul */
    }
    .temp-saida {
        color: #dc3545; /* Vermelho */
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
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9]+)\.csv", nome)

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
        # Lendo o arquivo como texto para pré-processamento
        with open(caminho, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filtrar a linha '---' e remover espaços extras e o caractere '|'
        processed_lines = []
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith('|') and stripped_line.endswith('|'):
                # Ignora a linha de separação '---'
                if '---' in stripped_line:
                    continue
                # Remove o primeiro e último '|', e divide pelo '|' restante
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                # Filtra partes vazias que podem surgir de múltiplos delimitadores
                cleaned_parts = [p for p in parts if p]
                processed_lines.append(','.join(cleaned_parts))
            else:
                # Se a linha não estiver no formato '| ... |', tenta adicionar como está
                processed_lines.append(stripped_line)

        # Converte a lista de linhas processadas em um objeto StringIO para o pandas ler
        data_io = StringIO('\n'.join(processed_lines))

        # Agora, o pandas pode ler com vírgula como separador
        df = pd.read_csv(data_io, sep=',', decimal='.', encoding='utf-8')

        # Limpeza de espaços nos nomes das colunas lidas
        df.columns = [col.strip() for col in df.columns]

        # Renomear colunas para o padrão esperado no dashboard
        # Certifique-se que esta lista de colunas corresponde EXATAMENTE ao seu CSV
        expected_columns = [
            "Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT",
            "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento",
            "kW Consumo", "COP"
        ]

        # Verifica se o número de colunas corresponde antes de renomear
        if len(df.columns) == len(expected_columns):
            df.columns = expected_columns
        else:
            st.warning(f"O número de colunas no arquivo {os.path.basename(caminho)} ({len(df.columns)}) não corresponde ao esperado ({len(expected_columns)}). As colunas podem estar incorretas.")
            # Tenta renomear as que batem, ou deixa como está se for muito diferente
            new_columns = []
            for i, col_name in enumerate(df.columns):
                if i < len(expected_columns):
                    new_columns.append(expected_columns[i])
                else:
                    new_columns.append(col_name) # Mantém o nome original se não houver correspondência
            df.columns = new_columns


        # Criar coluna DateTime combinando Date e Time
        # Converte 'Date' para string e 'Time' para string antes de combinar
        df['DateTime'] = pd.to_datetime(
            df['Date'].astype(str) + ' ' + df['Time'].astype(str),
            errors='coerce' # Coerce para NaT (Not a Time) se houver erro na conversão
        )

        # Mover 'DateTime' para a primeira coluna
        if 'DateTime' in df.columns:
            cols = ['DateTime'] + [col for col in df.columns if col != 'DateTime']
            df = df[cols]

        # Converter colunas numéricas para float, tratando erros
        for col in df.columns:
            if col not in ["Date", "Time", "DateTime"]: # Não tenta converter data/hora
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(caminho)}': {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro


# --- Função para obter os dados da última leitura do CSV mais recente ---
@st.cache_data(ttl=10)
def get_latest_csv_data():
    todos_arquivos_info = listar_arquivos_csv()

    if not todos_arquivos_info:
        return None, None, None

    # Filtra arquivos com data válida para encontrar o mais recente
    arquivos_com_data = [a for a in todos_arquivos_info if a['data'] is not None]
    if not arquivos_com_data:
        return None, None, None

    # Encontra o arquivo mais recente com base na data e hora
    arquivo_mais_recente = max(arquivos_com_data, key=lambda x: (x['data'], x['hora']))

    if arquivo_mais_recente:
        df_latest = carregar_csv_caminho(arquivo_mais_recente['caminho'])
        if not df_latest.empty:
            last_row = df_latest.iloc[-1]
            return last_row, arquivo_mais_recente['nome_arquivo'], arquivo_mais_recente['data'], arquivo_mais_recente['hora']
    return None, None, None


# =====================================================
#  PAINEL: Última Leitura Registrada
# =====================================================
st.subheader("Último Dashboard Enviado")

last_row_data, latest_filename, latest_date, latest_time = get_latest_csv_data()

if last_row_data is not None:
    st.write(f"Dados do arquivo: **{latest_filename}**")
    st.write(f"Última leitura registrada em: **{latest_date.strftime('%d/%m/%Y')} às {latest_time}**")

    st.markdown("---")

    # Mapeamento de nomes de colunas para exibição e ícones
    metric_display_names = {
        "Ambiente": "T-Ambiente",
        "Entrada": "T-Entrada",
        "Saída": "T-Saída",
        "ΔT": "ΔT",
        "Tensão": "Tensão",
        "Corrente": "Corrente",
        "kcal/h": "Kcal/h",
        "Vazão": "Vazão",
        "kW Aquecimento": "Kw aquecimento",
        "kW Consumo": "Kw consumo",
        "COP": "COP"
    }

    # Mapeamento de ícones (emojis)
    metric_icons = {
        "Ambiente": "🌍",
        "Entrada": "➡️", # Seta para entrada
        "Saída": "⬅️",  # Seta para saída
        "ΔT": "🌡️",
        "Tensão": "⚡",
        "Corrente": "🔌",
        "kcal/h": "🔥",
        "Vazão": "💧", # Gota d'água para vazão
        "kW Aquecimento": "♨️",
        "kW Consumo": "💡",
        "COP": "📈" # Gráfico para coeficiente de performance
    }

    # Unidades para cada métrica
    metric_units = {
        "Ambiente": "°C",
        "Entrada": "°C",
        "Saída": "°C",
        "ΔT": "°C",
        "Tensão": "V",
        "Corrente": "A",
        "kcal/h": "kcal/h",
        "Vazão": "L/h", # Litros por hora
        "kW Aquecimento": "kW",
        "kW Consumo": "kW",
        "COP": "" # COP não tem unidade comum, ou é adimensional
    }

    # Exibir as métricas em 4 colunas
    cols = st.columns(4)
    metrics_to_display = [
        "Ambiente", "Entrada", "Saída", "ΔT",
        "Tensão", "Corrente", "kcal/h", "Vazão",
        "kW Aquecimento", "kW Consumo", "COP"
    ]

    for i, metric_key in enumerate(metrics_to_display):
        with cols[i % 4]:
            valor = last_row_data.get(metric_key)

            # Garante que o valor é numérico antes de formatar
            if pd.isna(valor):
                display_value = "N/D"
            else:
                display_value = f"{valor:.2f}".replace('.', ',') # Formata para 2 casas e usa vírgula decimal

            label = metric_display_names.get(metric_key, metric_key)
            icon = metric_icons.get(metric_key, "📊")
            unit = metric_units.get(metric_key, "")

            # Adiciona a unidade ao valor exibido
            full_display_value = f"{display_value} {unit}".strip()

            # Usar st.markdown para aplicar cores específicas para T-Entrada e T-Saída
            if metric_key == "Entrada":
                st.markdown(f"<div class='metric-card'><h4 class='temp-entrada'>{icon} {label}</h4><p class='temp-entrada'>{full_display_value}</p></div>", unsafe_allow_html=True)
            elif metric_key == "Saída":
                st.markdown(f"<div class='metric-card'><h4 class='temp-saida'>{icon} {label}</h4><p class='temp-saida'>{full_display_value}</p></div>", unsafe_allow_html=True)
            else:
                # Para outras métricas, usa o st.metric padrão ou um card genérico
                st.markdown(f"<div class='metric-card'><h4>{icon} {label}</h4><p>{full_display_value}</p></div>", unsafe_allow_html=True)

else:
    st.info("Nenhum arquivo CSV encontrado ou dados válidos para a última leitura.")

st.markdown("---") # Separador visual

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# =====================================================
#  FILTROS DE ARQUIVOS (BARRA LATERAL)
# =====================================================
st.sidebar.header("Filtros de Arquivos")

todos_arquivos_info = listar_arquivos_csv()

# Extrair todos os modelos, operações, anos e meses únicos (incluindo N/D)
all_modelos = sorted(list(set([a["modelo"] for a in todos_arquivos_info])))
all_operacoes = sorted(list(set([a["operacao"] for a in todos_arquivos_info])))
all_anos = sorted(list(set([a["ano"] for a in todos_arquivos_info if a["ano"] is not None])), reverse=True)
all_meses = sorted(list(set([a["mes"] for a in todos_arquivos_info if a["mes"] is not None])))

mes_label_map = {
    1: "01 - Janeiro", 2: "02 - Fevereiro", 3: "03 - Março", 4: "04 - Abril",
    5: "05 - Maio", 6: "06 - Junho", 7: "07 - Julho", 8: "08 - Agosto",
    9: "09 - Setembro", 10: "10 - Outubro", 11: "11 - Novembro", 12: "12 - Dezembro"
}
mes_options_labels = ["Todos"] + [mes_label_map[m] for m in all_meses]
mes_options_values = [None] + all_meses

# 1. Filtro por Modelo
selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    ["Todos"] + all_modelos,
    key="filter_modelo"
)

# 2. Filtro por N° Operação (dinâmico com base no modelo)
# Primeiro, filtra os arquivos pelo modelo selecionado
arquivos_filtrados_por_modelo = [
    a for a in todos_arquivos_info
    if selected_modelo == "Todos" or a["modelo"] == selected_modelo
]
all_operacoes_for_model = sorted(list(set([a["operacao"] for a in arquivos_filtrados_por_modelo])))

selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    ["Todos"] + all_operacoes_for_model,
    key="filter_operacao"
)

# 3. Filtro por Ano (dinâmico com base no modelo e operação)
arquivos_filtrados_por_op = [
    a for a in arquivos_filtrados_por_modelo
    if selected_operacao == "Todos" or a["operacao"] == selected_operacao
]
all_anos_for_op = sorted(list(set([a["ano"] for a in arquivos_filtrados_por_op if a["ano"] is not None])), reverse=True)

selected_ano = st.sidebar.selectbox(
    "Ano:",
    ["Todos"] + all_anos_for_op,
    key="filter_ano"
)

# 4. Filtro por Mês (dinâmico com base no modelo, operação e ano)
arquivos_filtrados_por_ano = [
    a for a in arquivos_filtrados_por_op
    if selected_ano == "Todos" or a["ano"] == selected_ano
]
all_meses_for_ano = sorted(list(set([a["mes"] for a in arquivos_filtrados_por_ano if a["mes"] is not None])))
mes_options_labels_filtered = ["Todos"] + [mes_label_map[m] for m in all_meses_for_ano]
mes_options_values_filtered = [None] + all_meses_for_ano

selected_mes_label = st.sidebar.selectbox(
    "Mês:",
    mes_options_labels_filtered,
    key="filter_mes"
)
selected_mes = mes_options_values_filtered[mes_options_labels_filtered.index(selected_mes_label)]


# Aplicar todos os filtros para a lista final de arquivos
arquivos_filtrados = [
    a for a in todos_arquivos_info
    if (selected_modelo == "Todos" or a["modelo"] == selected_modelo)
    and (selected_operacao == "Todos" or a["operacao"] == selected_operacao)
    and (selected_ano == "Todos" or a["ano"] == selected_ano)
    and (selected_mes is None or a["mes"] == selected_mes)
]

# Ordenar os arquivos filtrados por data e hora (mais recente primeiro)
arquivos_filtrados.sort(key=lambda x: (x['data'] if x['data'] else datetime.min.date(), x['hora'] if x['hora'] else '00:00'), reverse=True)


# =====================================================
#  ÁREA PRINCIPAL: Arquivos Disponíveis
# =====================================================
st.subheader("Arquivos Disponíveis")

if not arquivos_filtrados:
    st.info("Nenhum arquivo encontrado com os filtros selecionados.")
else:
    # Armazena o arquivo selecionado na session_state
    if 'selected_file_path' not in st.session_state:
        st.session_state.selected_file_path = None

    # Exibe os arquivos em colunas
    cols = st.columns(3) # 3 botões por linha
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols[i % 3]: # Distribui os botões nas colunas
            display_name = arquivo['nome_arquivo'] # Exibe o nome original do CSV

            if st.button(display_name, key=f"file_button_{i}"):
                st.session_state.selected_file_path = arquivo['caminho']
                st.rerun() # Força a atualização para mostrar o arquivo selecionado

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

            # Usar os nomes de colunas do DataFrame carregado, exceto 'DateTime'
            variaveis_opcoes = [col for col in df_graf.columns if col != 'DateTime']

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
