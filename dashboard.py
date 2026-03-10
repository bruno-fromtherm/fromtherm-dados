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

        processed_lines = []
        header_found = False
        for line in lines:
            line = line.strip()
            if not line: # Ignora linhas vazias
                continue
            if line.startswith('| ---'): # Ignora a linha de separação do cabeçalho
                continue
            if line.startswith('|'):
                # Remove as barras externas, divide pelas barras internas e limpa espaços
                parts = [p.strip() for p in line.strip('|').split('|')]
                processed_lines.append(','.join(parts))
                if not header_found: # A primeira linha processada é o cabeçalho
                    header_found = True
            else: # Se houver linhas que não seguem o padrão com barras, tenta adicionar como está
                processed_lines.append(line)

        if not processed_lines:
            return pd.DataFrame()

        # Usar StringIO para que pandas possa ler o texto processado como um arquivo CSV
        data_io = StringIO("\n".join(processed_lines))

        df = pd.read_csv(data_io, sep=',', decimal='.', encoding='utf-8')

        # Mapeamento de nomes de colunas do CSV para o padrão do dashboard
        column_mapping = {
            'Date': 'Date', 'Time': 'Time',
            'ambiente': 'Ambiente',
            'entrada': 'Entrada',
            'saida': 'Saída',
            'dif': 'ΔT', # Diferença de Temperatura
            'tensao': 'Tensão',
            'corrente': 'Corrente',
            'kacl/h': 'Kcal/h',
            'vazao': 'Vazão',
            'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo',
            'cop': 'COP'
        }

        # Renomear colunas existentes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Combinar 'Date' e 'Time' em uma única coluna 'DateTime'
        if 'Date' in df.columns and 'Time' in df.columns:
            # Tenta diferentes formatos de data
            def parse_datetime(row):
                try:
                    # Formato YYYY/MM/DD HH:MM:SS
                    return datetime.strptime(f"{row['Date']} {row['Time']}", "%Y/%m/%d %H:%M:%S")
                except ValueError:
                    try:
                        # Formato YYYY-MM-DD HH:MM:SS
                        return datetime.strptime(f"{row['Date']} {row['Time']}", "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return pd.NaT # Not a Time (para datas inválidas)

            df['DateTime'] = df.apply(parse_datetime, axis=1)
            df = df.drop(columns=['Date', 'Time'])

            # Mover 'DateTime' para a primeira coluna
            df = df[['DateTime'] + [col for col in df.columns if col != 'DateTime']]

        # Converter colunas numéricas para float, tratando erros
        for col in df.columns:
            if col not in ['DateTime']: # Não tentar converter DateTime para numérico
                df[col] = pd.to_numeric(df[col], errors='coerce') # 'coerce' transforma erros em NaN

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV: {e}")
        return pd.DataFrame()

# --- Inicialização do estado da sessão ---
if 'selected_file_path' not in st.session_state:
    st.session_state.selected_file_path = None

# =====================================================
#  PAINEL: Última Leitura Registrada
# =====================================================
st.subheader("Último Dashboard Enviado:", help="Exibe os valores da última leitura do arquivo CSV mais recente.")
st.markdown(
    """
    <style>
    .st-emotion-cache-10trblm { /* Alvo para o st.subheader */
        color: #003366 !important; /* Cor azul escura */
    }
    .st-emotion-cache-1r6dm1x { /* Alvo para o st.write/st.markdown */
        color: #333333 !important; /* Cor cinza escuro para o texto */
    }
    </style>
    """, unsafe_allow_html=True
)

all_files_info = listar_arquivos_csv()

if all_files_info:
    # Encontrar o arquivo mais recente com base na data e hora extraídas do nome
    arquivo_mais_recente = max(
        (f for f in all_files_info if f['data'] and f['hora']),
        key=lambda x: (x['data'], x['hora']),
        default=None
    )

    if arquivo_mais_recente:
        df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['caminho'])

        if not df_ultima_leitura.empty:
            ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha

            st.write(f"**Arquivo:** `{arquivo_mais_recente['nome_arquivo']}`")
            st.write(f"**Última leitura:** {ultima_linha['DateTime'].strftime('%d/%m/%Y %H:%M:%S') if 'DateTime' in ultima_linha and pd.notna(ultima_linha['DateTime']) else 'N/D'}")

            st.markdown("---")

            # Definição das métricas a serem exibidas e seus ícones/unidades
            metric_configs = [
                {"label": "T-Ambiente", "col_name": "Ambiente", "icon": "🌍", "unit": "°C"},
                {"label": "T-Entrada", "col_name": "Entrada", "icon": "⬅️", "unit": "°C", "color_class": "temp-entrada"},
                {"label": "T-Saída", "col_name": "Saída", "icon": "➡️", "unit": "°C", "color_class": "temp-saida"},
                {"label": "ΔT", "col_name": "ΔT", "icon": "🌡️", "unit": "°C"},
                {"label": "Tensão", "col_name": "Tensão", "icon": "⚡", "unit": "V"},
                {"label": "Corrente", "col_name": "Corrente", "icon": "🔌", "unit": "A"},
                {"label": "Kcal/h", "col_name": "Kcal/h", "icon": "🔥", "unit": "Kcal/h"},
                {"label": "Vazão", "col_name": "Vazão", "icon": "💧", "unit": "L/h"},
                {"label": "Kw Aquecimento", "col_name": "Kw Aquecimento", "icon": "♨️", "unit": "kW"},
                {"label": "Kw Consumo", "col_name": "Kw Consumo", "icon": "💡", "unit": "kW"},
                {"label": "COP", "col_name": "COP", "icon": "📈", "unit": ""},
            ]

            # Exibir as métricas em colunas responsivas
            # Em telas grandes, 2 colunas. Em mobile, o CSS vai empilhar.
            cols_metrics = st.columns(2) 

            for i, config in enumerate(metric_configs):
                with cols_metrics[i % 2]: # Alterna entre as 2 colunas
                    col_name = config["col_name"]
                    label = config["label"]
                    icon = config["icon"]
                    unit = config["unit"]
                    color_class = config.get("color_class", "")

                    valor = ultima_linha.get(col_name)

                    # Formatação robusta do valor
                    if pd.notna(valor): # Verifica se não é NaN
                        valor_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') # Formato BR
                        display_value = f"{valor_formatado} {unit}"
                    else:
                        display_value = "N/D" # Se for NaN ou None, exibe N/D

                    # Aplica a cor se houver uma classe definida
                    if color_class:
                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <h4>{icon} {label}</h4>
                                <p class="{color_class}" style="font-size: 1.5em; font-weight: bold;">{display_value}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <h4>{icon} {label}</h4>
                                <p style="font-size: 1.5em; font-weight: bold;">{display_value}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
        else:
            st.warning("Não foi possível carregar os dados da última leitura do arquivo mais recente.")
    else:
        st.info("Nenhum arquivo de histórico válido encontrado para a última leitura.")
else:
    st.info("Nenhum arquivo de histórico encontrado na pasta de dados.")

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# =====================================================
#  BARRA LATERAL: Filtros de Arquivos
# =====================================================
st.sidebar.subheader("Filtros de Arquivos")

# Coleta todos os modelos, operações, anos e meses disponíveis
all_modelos = sorted(list(set(f['modelo'] for f in all_files_info if f['modelo'] != "N/D")))
all_operacoes = sorted(list(set(f['operacao'] for f in all_files_info if f['operacao'] != "N/D")))
all_anos = sorted(list(set(f['ano'] for f in all_files_info if f['ano'] is not None)), reverse=True)
all_meses = sorted(list(set(f['mes'] for f in all_files_info if f['mes'] is not None)))

# Adiciona "Todos" como opção padrão
modelos_filtro_opcoes = ["Todos"] + all_modelos
anos_filtro_opcoes = ["Todos"] + [str(a) for a in all_anos]
meses_filtro_opcoes = ["Todos"] + [str(m).zfill(2) for m in all_meses] # Garante 2 dígitos

# Filtro de Modelo
selected_modelo = st.sidebar.selectbox(
    "Modelo (ex: FTI165HBR):",
    options=modelos_filtro_opcoes,
    key="modelo_filter"
)

# Filtra operações com base no modelo selecionado
operacoes_filtradas_por_modelo = [
    f['operacao'] for f in all_files_info 
    if (selected_modelo == "Todos" or f['modelo'] == selected_modelo) and f['operacao'] != "N/D"
]
operacoes_filtro_opcoes = ["Todos"] + sorted(list(set(operacoes_filtradas_por_modelo)))

# Filtro de N° Operação
selected_operacao = st.sidebar.selectbox(
    "N° Operação (ex: OP987):",
    options=operacoes_filtro_opcoes,
    key="operacao_filter"
)

# Filtro de Ano
selected_ano = st.sidebar.selectbox(
    "Ano:",
    options=anos_filtro_opcoes,
    key="ano_filter"
)

# Filtro de Mês
selected_mes = st.sidebar.selectbox(
    "Mês:",
    options=meses_filtro_opcoes,
    key="mes_filter"
)

# Aplica os filtros aos arquivos
arquivos_filtrados = []
for arquivo in all_files_info:
    match_modelo = (selected_modelo == "Todos" or arquivo['modelo'] == selected_modelo)
    match_operacao = (selected_operacao == "Todos" or arquivo['operacao'] == selected_operacao)
    match_ano = (selected_ano == "Todos" or (arquivo['ano'] is not None and str(arquivo['ano']) == selected_ano))
    match_mes = (selected_mes == "Todos" or (arquivo['mes'] is not None and str(arquivo['mes']).zfill(2) == selected_mes))

    if match_modelo and match_operacao and match_ano and match_mes:
        arquivos_filtrados.append(arquivo)

# Ordena os arquivos filtrados pelo nome (ou data/hora se disponível)
arquivos_filtrados.sort(key=lambda x: (x['data'] if x['data'] else datetime.min.date(), x['hora'] if x['hora'] else "00:00"), reverse=True)

# =====================================================
#  ÁREA PRINCIPAL: Arquivos Disponíveis (Botões)
# =====================================================
st.markdown("---")
st.subheader("Arquivos Disponíveis")

if arquivos_filtrados:
    # Exibir os botões em colunas responsivas (2 colunas em telas maiores, empilha em mobile)
    cols = st.columns(2) 
    for i, arquivo in enumerate(arquivos_filtrados):
        with cols[i % 2]: # Alterna entre as 2 colunas
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
