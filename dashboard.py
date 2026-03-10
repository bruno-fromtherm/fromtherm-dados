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
        # Mapeamento dos nomes de colunas do CSV (minúsculas, sem acento) para o padrão do dashboard
        column_mapping = {
            "date": "Date",
            "time": "Time",
            "ambiente": "Ambiente",
            "entrada": "Entrada",
            "saida": "Saída",
            "dif": "ΔT", # 'dif' no CSV vira 'ΔT' no dashboard
            "tensao": "Tensão",
            "corrente": "Corrente",
            "kacl/h": "kcal/h", # Correção de digitação se houver
            "vazao": "Vazão",
            "kw aquecimento": "kW Aquecimento",
            "kw consumo": "kW Consumo",
            "cop": "COP",
        }

        # Renomear colunas existentes usando o mapeamento
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # --- Criação da coluna DateTime ---
        if "Date" in df.columns and "Time" in df.columns:
            # Combina Date e Time para criar uma coluna DateTime
            # Ajusta o formato da data para YYYY/MM/DD e o tempo para HH:MM:SS
            df["DateTime"] = pd.to_datetime(
                df["Date"].astype(str).str.replace('-', '/') + " " + df["Time"].astype(str),
                format="%Y/%m/%d %H:%M:%S", errors="coerce"
            )
            # Move DateTime para a primeira coluna
            df = df[["DateTime"] + [col for col in df.columns if col != "DateTime"]]
        else:
            st.warning("Colunas 'Date' ou 'Time' não encontradas para criar 'DateTime'.")
            df["DateTime"] = pd.NaT # Define como Not a Time se não puder criar

        # --- Conversão de tipos numéricos ---
        # Lista de colunas que devem ser numéricas (excluindo Date, Time, DateTime)
        numeric_cols = [col for col in df.columns if col not in ["Date", "Time", "DateTime"]]
        for col in numeric_cols:
            # Converte para numérico, transformando erros em NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo CSV: {e}")
        return pd.DataFrame()


# --- Inicialização do estado da sessão ---
if 'selected_file_path' not in st.session_state:
    st.session_state.selected_file_path = None

# --- Listar todos os arquivos CSV e suas informações ---
todos_arquivos_info = listar_arquivos_csv()

# --- Painel de Última Leitura Registrada ---
st.subheader("Último Dashboard Enviado")

if todos_arquivos_info:
    # Encontra o arquivo mais recente com base na data e hora
    arquivo_mais_recente = max(
        (a for a in todos_arquivos_info if a['data'] and a['hora']),
        key=lambda x: (x['data'], x['hora']),
        default=None
    )

    if arquivo_mais_recente:
        st.write(f"**Arquivo:** {arquivo_mais_recente['nome_arquivo']}")
        st.write(f"**Data e Hora da Leitura:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} {arquivo_mais_recente['hora']}")

        df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['caminho'])

        if not df_ultima_leitura.empty:
            ultima_linha = df_ultima_leitura.iloc[-1]

            # Mapeamento de ícones e unidades para as métricas
            metric_icons = {
                "Ambiente": "🌡️", "Entrada": "💧⬆️", "Saída": "🔥⬇️", "ΔT": "↔️",
                "Tensão": "⚡", "Corrente": "🔌", "kcal/h": "♨️", "Vazão": "🌊",
                "kW Aquecimento": "🔥", "kW Consumo": "💡", "COP": "📈"
            }
            metric_units = {
                "Ambiente": "°C", "Entrada": "°C", "Saída": "°C", "ΔT": "°C",
                "Tensão": "V", "Corrente": "A", "kcal/h": "kcal/h", "Vazão": "L/h",
                "kW Aquecimento": "kW", "kW Consumo": "kW", "COP": ""
            }
            metric_titles = {
                "Ambiente": "T-Ambiente", "Entrada": "T-Entrada", "Saída": "T-Saída", "ΔT": "Dif",
                "Tensão": "Tensão", "Corrente": "Corrente", "kcal/h": "Kcal/h", "Vazão": "Vazão",
                "kW Aquecimento": "Kw Aquecimento", "kW Consumo": "Kw Consumo", "COP": "Coeficiente de Performance"
            }

            # Colunas para exibir as métricas
            cols = st.columns(4)
            metrics_to_display = [
                "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente",
                "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"
            ]

            for i, metric_name in enumerate(metrics_to_display):
                with cols[i % 4]:
                    valor = ultima_linha.get(metric_name) # Usar .get() para evitar KeyError

                    # Formatação do valor
                    if pd.isna(valor):
                        display_value = "N/D"
                    else:
                        display_value = f"{valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',') # Formato BR
                        display_value += f" {metric_units.get(metric_name, '')}"

                    # Título da métrica
                    title = metric_titles.get(metric_name, metric_name)
                    icon = metric_icons.get(metric_name, "📊")

                    # Aplica cores específicas para T-Entrada e T-Saída
                    if metric_name == "Entrada":
                        st.markdown(f"<div class='metric-card'><h4 class='temp-entrada'>{icon} {title}</h4><p class='temp-entrada' style='font-size: 1.5em; font-weight: bold;'>{display_value}</p></div>", unsafe_allow_html=True)
                    elif metric_name == "Saída":
                        st.markdown(f"<div class='metric-card'><h4 class='temp-saida'>{icon} {title}</h4><p class='temp-saida' style='font-size: 1.5em; font-weight: bold;'>{display_value}</p></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='metric-card'><h4>{icon} {title}</h4><p style='font-size: 1.5em; font-weight: bold;'>{display_value}</p></div>", unsafe_allow_html=True)
        else:
            st.warning("Não foi possível carregar os dados da última leitura do arquivo mais recente.")
    else:
        st.info("Nenhum arquivo com data e hora válidas encontrado para a última leitura.")
else:
    st.info("Nenhum arquivo CSV encontrado na pasta de dados.")

st.markdown("---") # Separador visual

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# =====================================================
#  BARRA LATERAL: Filtros de Arquivos
# =====================================================
st.sidebar.subheader("Filtros de Arquivos")

# 1. Modelo
modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))
selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    ["Todos"] + modelos_disponiveis,
    key="filter_modelo"
)

# Filtrar arquivos pelo modelo selecionado para popular a próxima seleção
arquivos_filtrados_por_modelo = [
    a for a in todos_arquivos_info
    if (selected_modelo == "Todos" or a["modelo"] == selected_modelo)
]

# 2. N° Operação (dinâmico com base no Modelo)
operacoes_disponiveis = sorted(list(set(a["operacao"] for a in arquivos_filtrados_por_modelo if a["operacao"] != "N/D")))
selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    ["Todos"] + operacoes_disponiveis,
    key="filter_operacao"
)

# Filtrar arquivos pelo modelo e operação selecionados para popular a próxima seleção
arquivos_filtrados_por_modelo_op = [
    a for a in arquivos_filtrados_por_modelo
    if (selected_operacao == "Todos" or a["operacao"] == selected_operacao)
]

# 3. Ano
anos_disponiveis = sorted(list(set(a["ano"] for a in arquivos_filtrados_por_modelo_op if a["ano"] is not None)), reverse=True)
selected_ano = st.sidebar.selectbox(
    "Ano:",
    ["Todos"] + anos_disponiveis,
    key="filter_ano"
)

# Filtrar arquivos pelo modelo, operação e ano selecionados para popular a próxima seleção
arquivos_filtrados_por_modelo_op_ano = [
    a for a in arquivos_filtrados_por_modelo_op
    if (selected_ano == "Todos" or a["ano"] == selected_ano)
]

# 4. Mês
mes_label_map = {
    1: "01 - Janeiro", 2: "02 - Fevereiro", 3: "03 - Março", 4: "04 - Abril",
    5: "05 - Maio", 6: "06 - Junho", 7: "07 - Julho", 8: "08 - Agosto",
    9: "09 - Setembro", 10: "10 - Outubro", 11: "11 - Novembro", 12: "12 - Dezembro"
}
meses_disponiveis_values = sorted(list(set(a["mes"] for a in arquivos_filtrados_por_modelo_op_ano if a["mes"] is not None)))
meses_disponiveis_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis_values]

selected_mes_label = st.sidebar.selectbox(
    "Mês:",
    meses_disponiveis_labels,
    key="filter_mes"
)
selected_mes = None
if selected_mes_label != "Todos":
    selected_mes = meses_disponiveis_values[meses_disponiveis_labels.index(selected_mes_label) - 1] # -1 porque "Todos" é o primeiro item

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
