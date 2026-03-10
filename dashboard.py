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
    .temp-entrada {
        color: #007bff; /* Azul */
    }
    .temp-saida {
        color: #dc3545; /* Vermelho */
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
        .st-emotion-cache-1r6dm1x { /* Valor da métrica */
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

        # --- Mapeamento e Renomeação de Colunas ---
        # Mapeia os nomes do CSV para os nomes padronizados no dashboard
        column_mapping = {
            "Date": "Date",
            "Time": "Time",
            "ambiente": "Ambiente",
            "entrada": "Entrada",
            "saida": "Saída",
            "dif": "ΔT",
            "tensao": "Tensão",
            "corrente": "Corrente",
            "kacl/h": "Kcal/h",
            "vazao": "Vazão",
            "kw aquecimento": "Kw Aquecimento",
            "kw consumo": "Kw Consumo",
            "cop": "COP",
        }
        # Renomeia apenas as colunas que existem no DataFrame
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # --- Conversão de Tipos ---
        # Converte colunas numéricas para float, tratando erros
        numeric_cols = [
            "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente",
            "Kcal/h", "Vazão", "Kw Aquecimento", "Kw Consumo", "COP"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') # 'coerce' transforma erros em NaN

        # --- Criação da coluna DateTime ---
        if 'Date' in df.columns and 'Time' in df.columns:
            # Tenta converter 'Date' para o formato YYYY-MM-DD ou YYYY/MM/DD
            df['Date'] = df['Date'].astype(str).str.replace('/', '-')
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')
            # Move DateTime para o início
            df = df[['DateTime'] + [col for col in df.columns if col not in ['DateTime', 'Date', 'Time']]]
        else:
            st.warning("Colunas 'Date' ou 'Time' não encontradas para criar 'DateTime'.")
            df['DateTime'] = pd.NaT # Not a Time

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro


# --- Painel de Última Leitura Registrada ---
st.subheader("Último Dashboard Enviado")

all_files_info = listar_arquivos_csv()

# Encontra o arquivo mais recente com base na data e hora do nome
arquivo_mais_recente = None
if all_files_info:
    # Filtra arquivos com data e hora válidas para comparação
    valid_files = [f for f in all_files_info if f['data'] and f['hora']]
    if valid_files:
        # Ordena por data e hora (mais recente primeiro)
        arquivo_mais_recente = max(valid_files, key=lambda x: (x['data'], x['hora']))

if arquivo_mais_recente:
    last_file_path = arquivo_mais_recente['caminho']
    last_filename = arquivo_mais_recente['nome_arquivo']

    df_last_read = carregar_csv_caminho(last_file_path)

    if not df_last_read.empty:
        ultima_linha = df_last_read.iloc[-1] # Pega a última linha do DataFrame

        st.write(f"**Arquivo:** {last_filename}")
        if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']):
            st.write(f"**Última Leitura:** {ultima_linha['DateTime'].strftime('%d/%m/%Y %H:%M:%S')}")
        else:
            st.write(f"**Última Leitura:** N/D")

        # Mapeamento de títulos para as métricas e unidades
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

        # Mapeamento de ícones para as métricas
        metric_icons = {
            "Ambiente": "🌍",
            "Entrada": "➡️",
            "Saída": "⬅️",
            "ΔT": "🌡️",
            "Tensão": "⚡",
            "Corrente": "🔌",
            "Kcal/h": "🔥",
            "Vazão": "💧",
            "Kw Aquecimento": "♨️",
            "Kw Consumo": "💡",
            "COP": "📈",
        }

        # Mapeamento de unidades para as métricas
        metric_units = {
            "Ambiente": "°C",
            "Entrada": "°C",
            "Saída": "°C",
            "ΔT": "°C",
            "Tensão": "V",
            "Corrente": "A",
            "Kcal/h": "Kcal/h",
            "Vazão": "L/h",
            "Kw Aquecimento": "kW",
            "Kw Consumo": "kW",
            "COP": "", # COP não tem unidade específica
        }

        # Organiza as métricas em colunas responsivas
        # Para mobile, queremos que as colunas se empilhem. st.columns já faz isso,
        # mas podemos controlar o número de colunas para telas maiores.
        # Em telas pequenas, o CSS fará com que cada coluna ocupe 100% da largura.
        cols_per_row = 4 # Em desktop, 4 métricas por linha
        metrics_to_display = [
            "Ambiente", "Entrada", "Saída", "ΔT",
            "Tensão", "Corrente", "Kcal/h", "Vazão",
            "Kw Aquecimento", "Kw Consumo", "COP"
        ]

        # Cria as colunas para as métricas
        metric_cols = st.columns(cols_per_row)

        for i, original_col_name in enumerate(metrics_to_display):
            with metric_cols[i % cols_per_row]:
                valor = ultima_linha.get(original_col_name)

                # Formata o valor
                display_value = "N/D"
                if pd.notna(valor):
                    # Formata para 2 casas decimais e substitui '.' por ',' para padrão BR
                    display_value = f"{valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

                # Adiciona a unidade
                unit = metric_units.get(original_col_name, "")
                if unit:
                    display_value += f" {unit}"

                # Adiciona o ícone
                icon = metric_icons.get(original_col_name, "")

                # Aplica cor específica para T-Entrada e T-Saída
                if original_col_name == "Entrada":
                    st.markdown(f"<div class='metric-card'><h4 class='temp-entrada'>{icon} {metric_titles.get(original_col_name, original_col_name)}</h4><p class='temp-entrada'>{display_value}</p></div>", unsafe_allow_html=True)
                elif original_col_name == "Saída":
                    st.markdown(f"<div class='metric-card'><h4 class='temp-saida'>{icon} {metric_titles.get(original_col_name, original_col_name)}</h4><p class='temp-saida'>{display_value}</p></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='metric-card'><h4>{icon} {metric_titles.get(original_col_name, original_col_name)}</h4><p>{display_value}</p></div>", unsafe_allow_html=True)
    else:
        st.warning("Não foi possível carregar os dados da última leitura.")
else:
    st.info("Nenhum arquivo CSV encontrado para exibir a última leitura.")

st.markdown("---") # Separador visual

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# =====================================================
#  SIDEBAR: Filtros de Arquivos
# =====================================================
st.sidebar.subheader("Filtros de Arquivos")

# Obtém todos os arquivos para popular os filtros iniciais
all_files_info_for_filters = listar_arquivos_csv()

# Extrai opções únicas para os filtros
all_modelos = sorted(list(set([a["modelo"] for a in all_files_info_for_filters if a["modelo"] != "N/D"])))
all_anos = sorted(list(set([a["ano"] for a in all_files_info_for_filters if a["ano"] is not None])), reverse=True)
all_meses = sorted(list(set([a["mes"] for a in all_files_info_for_filters if a["mes"] is not None])))
all_operacoes = sorted(list(set([a["operacao"] for a in all_files_info_for_filters if a["operacao"] != "N/D"])))

mes_label_map = {
    1: "01 - Janeiro", 2: "02 - Fevereiro", 3: "03 - Março", 4: "04 - Abril",
    5: "05 - Maio", 6: "06 - Junho", 7: "07 - Julho", 8: "08 - Agosto",
    9: "09 - Setembro", 10: "10 - Outubro", 11: "11 - Novembro", 12: "12 - Dezembro"
}

# --- Filtros na Sidebar ---
selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    options=["Todos"] + all_modelos,
    key="filter_modelo"
)

# Filtra operações com base no modelo selecionado
filtered_operacoes_by_model = [
    a["operacao"] for a in all_files_info_for_filters 
    if (selected_modelo == "Todos" or a["modelo"] == selected_modelo) and a["operacao"] != "N/D"
]
all_operacoes_for_model = sorted(list(set(filtered_operacoes_by_model)))

selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    options=["Todas"] + all_operacoes_for_model,
    key="filter_operacao"
)

selected_ano = st.sidebar.selectbox(
    "Ano:",
    options=["Todos"] + all_anos,
    key="filter_ano"
)

# Filtra meses com base no ano e modelo selecionados
filtered_meses_by_year_model = [
    a["mes"] for a in all_files_info_for_filters 
    if (selected_modelo == "Todos" or a["modelo"] == selected_modelo) and
       (selected_operacao == "Todas" or a["operacao"] == selected_operacao) and
       (selected_ano == "Todos" or a["ano"] == selected_ano) and
       a["mes"] is not None
]
all_meses_for_filters = sorted(list(set(filtered_meses_by_year_model)))
meses_labels = ["Todos"] + [mes_label_map[m] for m in all_meses_for_filters]

selected_mes_label = st.sidebar.selectbox(
    "Mês:",
    options=meses_labels,
    key="filter_mes"
)
selected_mes = None
if selected_mes_label != "Todos":
    selected_mes = int(selected_mes_label.split(' ')[0])


# --- Aplica os filtros aos arquivos ---
arquivos_filtrados = []
for arquivo in all_files_info:
    match_modelo = (selected_modelo == "Todos" or arquivo["modelo"] == selected_modelo)
    match_operacao = (selected_operacao == "Todas" or arquivo["operacao"] == selected_operacao)
    match_ano = (selected_ano == "Todos" or arquivo["ano"] == selected_ano)
    match_mes = (selected_mes is None or arquivo["mes"] == selected_mes)

    if match_modelo and match_operacao and match_ano and match_mes:
        arquivos_filtrados.append(arquivo)

# Ordena os arquivos filtrados pelo nome (mais recente primeiro)
arquivos_filtrados = sorted(arquivos_filtrados, key=lambda x: x['nome_arquivo'], reverse=True)


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

    # Exibe os arquivos em colunas responsivas
    # Em telas pequenas, st.columns(3) vai empilhar automaticamente,
    # mas o CSS adicional garante que ocupem 100% da largura.
    cols = st.columns(3) # 3 botões por linha para desktop
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
