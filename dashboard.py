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
        st.error(f"Diretório de dados não encontrado: {DADOS_DIR}")
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)

        # Padrão mais flexível para capturar OP e o final do nome
        # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
        # Ex: historico_L1_20260306_1717_OP9090_FT55L.csv
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9]+)\.csv", nome)

        data, ano, mes, hora, operacao, modelo = None, None, None, None, None, None
        data_obj = None

        if match:
            ano = match.group(1)
            mes = match.group(2)
            dia = match.group(3)
            hora = match.group(4)
            operacao = match.group(5)
            modelo = match.group(6)
            data = f"{ano}-{mes}-{dia}"
            try:
                data_obj = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H%M")
            except ValueError:
                data_obj = None # Se a data/hora for inválida, define como None
        else:
            # Tenta um padrão mais simples se o primeiro falhar (apenas data e hora)
            simple_match = re.match(r"historico_L1_(\d{8})_(\d{4})\.csv", nome)
            if simple_match:
                data_str = simple_match.group(1)
                hora_str = simple_match.group(2)
                ano = data_str[:4]
                mes = data_str[4:6]
                dia = data_str[6:8]
                data = f"{ano}-{mes}-{dia}"
                hora = hora_str
                try:
                    data_obj = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H%M")
                except ValueError:
                    data_obj = None
            else:
                # Se nenhum padrão funcionar, tenta extrair data/hora do nome do arquivo
                # de forma mais genérica, ou define como None
                try:
                    # Ex: 20260310_120832.csv (data e hora no início)
                    generic_match = re.match(r"(\d{8})_(\d{6})", nome)
                    if generic_match:
                        data_str = generic_match.group(1)
                        hora_str = generic_match.group(2)
                        ano = data_str[:4]
                        mes = data_str[4:6]
                        dia = data_str[6:8]
                        data = f"{ano}-{mes}-{dia}"
                        hora = hora_str[:4] # Pega apenas HHMM
                        data_obj = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H%M")
                except ValueError:
                    data_obj = None


        info_arquivos.append({
            "caminho": caminho,
            "nome_arquivo": nome,
            "data": data_obj.date() if data_obj else None,
            "hora": data_obj.strftime("%H:%M") if data_obj else None,
            "data_obj": data_obj, # Objeto datetime para ordenação
            "ano": ano,
            "mes": mes,
            "operacao": operacao,
            "modelo": modelo,
        })

    # Ordena os arquivos por data e hora (mais recente primeiro)
    # Arquivos sem data válida (data_obj é None) serão colocados no final
    info_arquivos.sort(key=lambda x: x['data_obj'] if x['data_obj'] is not None else datetime.min, reverse=True)
    return info_arquivos

# --- Função para carregar e pré-processar o CSV ---
@st.cache_data(ttl=60)
def carregar_csv_caminho(file_path):
    """
    Carrega um arquivo CSV do caminho especificado,
    pré-processa para lidar com o formato de barras e
    garante que as colunas 'Date' e 'Time' sejam tratadas.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        header_found = False
        header_line = ""
        data_start_index = -1

        # 1. Pré-processamento: converter formato de barras para CSV com vírgulas
        for i, line in enumerate(lines):
            stripped_line = line.strip()

            # Ignora linhas vazias
            if not stripped_line:
                continue

            # Procura pelo cabeçalho (linha que começa com '|' e contém 'Date' e 'Time')
            if not header_found and stripped_line.startswith('|') and 'Date' in stripped_line and 'Time' in stripped_line:
                # Remove as barras das extremidades e divide os valores
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                # Limpa espaços vazios e junta tudo com VÍRGULA
                cleaned_parts = [p for p in parts if p]
                header_line = ','.join(cleaned_parts)
                header_found = True
                continue # Pula para a próxima linha

            # Ignora a linha de separação
            if stripped_line.startswith('|---'):
                if header_found and data_start_index == -1: # Se o cabeçalho já foi encontrado, esta é a linha de separação
                    data_start_index = i + 1 # A próxima linha é o início dos dados
                continue

            # Processa as linhas de dados após o cabeçalho e separador
            if header_found and stripped_line.startswith('|') and data_start_index != -1:
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                cleaned_parts = [p for p in parts if p]
                processed_lines.append(','.join(cleaned_parts))

        if not header_line or not processed_lines:
            st.error(f"Erro: O arquivo '{os.path.basename(file_path)}' não tem um cabeçalho ou dados válidos após o pré-processamento.")
            return pd.DataFrame()

        # Junta o cabeçalho e as linhas processadas em uma única string CSV
        final_csv_string = header_line + "\n" + "\n".join(processed_lines)

        # Usa StringIO para ler a string como um arquivo CSV
        df = pd.read_csv(StringIO(final_csv_string), sep=',')

        # Mapeamento de nomes de colunas para padronização
        column_mapping = {
            'date': 'Date',
            'time': 'Time',
            't-ambiente': 'Ambiente',
            't-entrada': 'Entrada',
            't-saida': 'Saída',
            'dif': 'ΔT',
            'tensao': 'Tensão (V)',
            'corrente': 'Corrente (A)',
            'kcal/h': 'Kcal/h',
            'vazao': 'Vazão (L/h)',
            'kw aquecimento': 'Kw Aquecimento',
            'kw consumo': 'Kw Consumo',
            'cop': 'COP'
        }

        # Renomeia as colunas, ignorando as que não existem
        df.columns = df.columns.str.strip() # Remove espaços em branco dos nomes das colunas
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns.str.lower()})

        # Verifica se as colunas essenciais 'Date' e 'Time' existem após o renomeio
        if 'Date' not in df.columns or 'Time' not in df.columns:
            st.error(f"Erro: Colunas 'Date' ou 'Time' não encontradas no arquivo '{os.path.basename(file_path)}' após o pré-processamento e renomeio. Colunas disponíveis: {df.columns.tolist()}")
            return pd.DataFrame()

        # Cria a coluna 'DateTime'
        df['Date'] = df['Date'].astype(str).str.replace('/', '-', regex=False)
        df['Time'] = df['Time'].astype(str)

        # Tenta converter para datetime com formato específico
        df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')

        # Fallback para inferência se o formato específico falhar para a maioria
        if df['DateTime'].isnull().sum() > len(df) / 2:
            st.warning(f"Aviso: Formato de data/hora '%Y-%m-%d %H:%M:%S' falhou para a maioria das linhas em '{os.path.basename(file_path)}'. Tentando inferir o formato.")
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')

        df.dropna(subset=['DateTime'], inplace=True)

        if df.empty:
            st.error(f"Erro: Nenhum dado válido restante no arquivo '{os.path.basename(file_path)}' após a limpeza de datas/horas inválidas.")
            return pd.DataFrame()

        # Converte colunas numéricas (exceto Date, Time, DateTime)
        for col in df.columns:
            if col not in ['Date', 'Time', 'DateTime']:
                # Converte vírgula para ponto e depois para numérico
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(file_path)}': {e}")
        return pd.DataFrame()

# --- Função para formatar números para exibição no Brasil ---
def format_br_number(value, decimals=2):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =====================================================
#  ÁREA PRINCIPAL: Última Leitura Registrada
# =====================================================
st.header("Última Leitura Registrada")

todos_arquivos_info = listar_arquivos_csv()

if todos_arquivos_info:
    # O arquivo mais recente já está no topo da lista devido à ordenação em listar_arquivos_csv
    arquivo_mais_recente = todos_arquivos_info[0]
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente['caminho'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha do DataFrame

        st.markdown(f"**Arquivo:** `{arquivo_mais_recente['nome_arquivo']}`")
        if 'data_obj' in arquivo_mais_recente and arquivo_mais_recente['data_obj']:
            st.markdown(f"**Última Leitura:** {arquivo_mais_recente['data_obj'].strftime('%d/%m/%Y %H:%M:%S')}")
        else:
            st.markdown("**Última Leitura:** Data/Hora não disponível")

        st.markdown("---")

        # Exibição das métricas em 4 colunas
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(label="T-Ambiente", value=format_br_number(ultima_linha.get('Ambiente')), delta=None)
        with col2:
            st.metric(label="T-Entrada", value=format_br_number(ultima_linha.get('Entrada')), delta=None)
        with col3:
            st.metric(label="T-Saída", value=format_br_number(ultima_linha.get('Saída')), delta=None)
        with col4:
            st.metric(label="ΔT", value=format_br_number(ultima_linha.get('ΔT')), delta=None)

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric(label="Tensão (V)", value=format_br_number(ultima_linha.get('Tensão (V)')), delta=None)
        with col6:
            st.metric(label="Corrente (A)", value=format_br_number(ultima_linha.get('Corrente (A)')), delta=None)
        with col7:
            st.metric(label="Kcal/h", value=format_br_number(ultima_linha.get('Kcal/h')), delta=None)
        with col8:
            st.metric(label="Vazão (L/h)", value=format_br_number(ultima_linha.get('Vazão (L/h)')), delta=None)

        col9, col10, col11, col12 = st.columns(4)
        with col9:
            st.metric(label="Kw Aquecimento", value=format_br_number(ultima_linha.get('Kw Aquecimento')), delta=None)
        with col10:
            st.metric(label="Kw Consumo", value=format_br_number(ultima_linha.get('Kw Consumo')), delta=None)
        with col11:
            st.metric(label="COP", value=format_br_number(ultima_linha.get('COP')), delta=None)
        with col12:
            st.empty() # Coluna vazia para alinhar

    else:
        st.warning("Não foi possível carregar os dados da última leitura do arquivo mais recente.")
else:
    st.info("Nenhum arquivo CSV encontrado no diretório especificado para a última leitura.")


# =====================================================
#  BARRA LATERAL: Filtros de Arquivos
# =====================================================
st.sidebar.header("Filtros de Arquivos")

# 1. Filtro por Modelo
all_modelos = sorted(list(set([a["modelo"] for a in todos_arquivos_info if a["modelo"] is not None])))
selected_modelo = st.sidebar.selectbox(
    "Modelo:",
    ["Todos"] + all_modelos,
    key="filter_modelo"
)

# 2. Filtro por Operação (dinâmico com base no modelo)
arquivos_filtrados_por_modelo = [
    a for a in todos_arquivos_info
    if selected_modelo == "Todos" or a["modelo"] == selected_modelo
]
all_operacoes_for_modelo = sorted(list(set([a["operacao"] for a in arquivos_filtrados_por_modelo if a["operacao"] is not None])))
selected_operacao = st.sidebar.selectbox(
    "Operação:",
    ["Todos"] + all_operacoes_for_modelo,
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

# Mapeamento de números de mês para nomes
mes_label_map = {
    '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
    '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
    '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
}

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
# Garante que 'data' e 'hora' sejam tratados como None se não existirem
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
                    colorway=px.colors.qualitative.Plotly, # Garante cores padrão do Plotly
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