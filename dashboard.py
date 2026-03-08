import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re # Importar módulo de expressões regulares
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import plotly.express as px

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm") # Título da aba do navegador

# =========================
#  CSS GLOBAL (para o "0" e cards com animação suave)
# =========================
st.markdown(
    """
    <style>
    /* Estilo dos cards de métricas */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd; /* Cor padrão da borda */
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd; /* Cor padrão do ícone */
        animation: ft-pulse 1.5s ease-in-out infinite; /* Animação de pulso suave para todos */
    }
    .ft-card-icon.red {
        color: #dc3545; /* Cor vermelha para T-Saída */
    }
    .ft-card-content {
        display: flex;
        flex-direction: column;
    }
    .ft-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #444444;
        margin: 0;
        padding: 0;
    }
    .ft-card-value {
        font-size: 18px;
        font-weight: 700;
        color: #111111;
        margin: 0;
        padding: 0;
    }

    /* Animação de pulso suave (única para todos os ícones) */
    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 0.9; }
        50%  { transform: scale(1.05); opacity: 1; }
        100% { transform: scale(1);   opacity: 0.9; }
    }
    </style>

    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# --- Diretório onde os arquivos CSV estão (ajuste conforme a estrutura do seu repositório) ---
# DADOS_DIR = "./dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"
# Usando o caminho mais genérico para a raiz do repositório para testes
DADOS_DIR = "." # Procura na raiz do repositório
# Se os arquivos estiverem em uma subpasta específica, ajuste aqui:
# DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para carregar CSV ---
@st.cache_data
def carregar_csv_caminho(caminho_arquivo):
    try:
        df = pd.read_csv(caminho_arquivo, sep=";")
        # Tenta converter 'Date' e 'Time' para um único 'DateTime'
        if "Date" in df.columns and "Time" in df.columns:
            df["DateTime"] = pd.to_datetime(
                df["Date"].astype(str) + " " + df["Time"].astype(str),
                errors="coerce",
            )
        elif "Time" in df.columns: # Se só tiver 'Time', usa 'Time' como 'DateTime'
            df["DateTime"] = pd.to_datetime(df["Time"], errors="coerce")
        else: # Se não tiver nenhum, cria um DateTime básico ou deixa sem
            df["DateTime"] = pd.to_datetime(df.index, unit='s') # Cria um DateTime a partir do índice

        # Converte colunas numéricas para float, tratando erros
        for col in [
            "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
            "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV {caminho_arquivo}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# --- Função para listar arquivos CSV e extrair informações ---
@st.cache_data
def listar_arquivos_csv():
    # Ajusta o padrão para procurar em subdiretórios se DADOS_DIR for '.'
    if DADOS_DIR == ".":
        # Procura em qualquer subdiretório dentro da raiz
        arquivos_encontrados = glob.glob("./**/*.csv", recursive=True)
    else:
        arquivos_encontrados = glob.glob(os.path.join(DADOS_DIR, "*.csv"))

    todos_arquivos_info = []
    padrao_nome_arquivo = re.compile(
        r"historico_L1_(?P<data>\d{8})_(?P<hora>\d{4})_OP(?P<operacao>\d+)_FT(?P<modelo>\w+)\.csv"
    )

    for caminho_completo in arquivos_encontrados:
        nome_arquivo = os.path.basename(caminho_completo)
        match = padrao_nome_arquivo.match(nome_arquivo)

        info_arquivo = {
            "caminho": caminho_completo,
            "nome_arquivo": nome_arquivo,
            "modelo": "N/D",
            "operacao": "N/D",
            "data_arquivo": "N/D",
            "hora_arquivo": "N/D",
            "data_modificacao": datetime.fromtimestamp(os.path.getmtime(caminho_completo)),
        }

        if match:
            info_arquivo["modelo"] = match.group("modelo")
            info_arquivo["operacao"] = match.group("operacao")
            try:
                data_str = match.group("data")
                info_arquivo["data_arquivo"] = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")
            except ValueError:
                pass # Mantém "N/D"
            try:
                hora_str = match.group("hora")
                info_arquivo["hora_arquivo"] = datetime.strptime(hora_str, "%H%M").strftime("%H:%M")
            except ValueError:
                pass # Mantém "N/D"

        todos_arquivos_info.append(info_arquivo)

    # Ordena os arquivos pelo nome (que contém data e hora) para que o mais recente seja o primeiro
    # Ou pela data de modificação se o nome não for confiável
    todos_arquivos_info.sort(key=lambda x: x["data_modificacao"], reverse=True)
    return todos_arquivos_info

# --- Função para exibir cards de métricas ---
def exibir_card(titulo, valor, unidade="", icone="bi bi-info-circle", cor_borda="", cor_icone=""):
    card_class = "ft-card"
    icon_class = "ft-card-icon"
    if cor_borda:
        card_class += f" border-left-{cor_borda}"
    if cor_icone:
        icon_class += f" {cor_icone}"

    st.markdown(
        f"""
        <div class="{card_class}">
            <i class="{icone} {icon_class}"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Função para mostrar valor com tratamento de N/D ---
def mostra_valor(df, coluna, formato="{:.2f}", default="N/D"):
    if not df.empty and coluna in df.columns and pd.notna(df[coluna].iloc[-1]):
        return formato.format(df[coluna].iloc[-1])
    return default

# =========================
#  LAYOUT PRINCIPAL DO APP
# =========================

# --- Carregar todos os arquivos CSV disponíveis ---
# Usamos st.session_state para armazenar os arquivos e evitar recarregar a cada interação
if "todos_arquivos_info" not in st.session_state:
    st.session_state.todos_arquivos_info = listar_arquivos_csv()

todos_arquivos_info = st.session_state.todos_arquivos_info

# --- Filtros na barra lateral ---
st.sidebar.header("Filtros")

# Extrair opções únicas para os filtros
modelos = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info if arq["modelo"] != "N/D"])))
anos = sorted(list(set([datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").year for arq in todos_arquivos_info if arq["data_arquivo"] != "N/D"])))
meses_nomes = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]
meses_numeros = [f"{i:02d}" for i in range(1, 13)]
meses_map = {nome: num for nome, num in zip(meses_nomes, meses_numeros)}
meses_map_reverse = {num: nome for nome, num in zip(meses_nomes, meses_numeros)}

ops = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info if arq["operacao"] != "N/D"])))
datas_unicas = sorted(list(set([arq["data_arquivo"] for arq in todos_arquivos_info if arq["data_arquivo"] != "N/D"])))


filtro_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos)
filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos)
filtro_mes_label = st.sidebar.selectbox("Mês", ["Todos"] + meses_nomes)
filtro_mes = meses_map.get(filtro_mes_label, "Todos")
filtro_data = st.sidebar.selectbox("Data", ["Todas"] + datas_unicas)
filtro_op = st.sidebar.selectbox("Operação", ["Todas"] + ops)


# Aplicar filtros
arquivos_filtrados = todos_arquivos_info
if filtro_modelo != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["modelo"] == filtro_modelo]
if filtro_ano != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["data_arquivo"] != "N/D" and datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").year == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["data_arquivo"] != "N/D" and datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").month == int(filtro_mes)]
if filtro_data != "Todas":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["data_arquivo"] == filtro_data]
if filtro_op != "Todas":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["operacao"] == filtro_op]


# --- Exibir Última Leitura (se houver arquivos filtrados) ---
st.header("Última Leitura Registrada")

if not arquivos_filtrados:
    st.info("Nenhum arquivo CSV encontrado com os filtros aplicados para exibir a última leitura.")
    ultima_linha = None
    info_ultimo_arquivo = None
else:
    info_ultimo_arquivo = arquivos_filtrados[0] # O primeiro é o mais recente após a ordenação
    df_ultimo = carregar_csv_caminho(info_ultimo_arquivo["caminho"])
    if not df_ultimo.empty:
        ultima_linha = df_ultimo.iloc[-1]
    else:
        ultima_linha = None

if ultima_linha is not None:
    st.markdown(
        f"**Modelo:** {info_ultimo_arquivo['modelo']} | "
        f"**OP:** {info_ultimo_arquivo['operacao']} | "
        f"**Data:** {info_ultimo_arquivo['data_arquivo']} | "
        f"**Hora:** {info_ultimo_arquivo['hora_arquivo']}"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        exibir_card("T-Ambiente", mostra_valor(df_ultimo, "Ambiente"), "°C", "bi bi-thermometer-half")
    with col2:
        exibir_card("T-Entrada", mostra_valor(df_ultimo, "Entrada"), "°C", "bi bi-arrow-down-circle")
    with col3:
        exibir_card("T-Saída", mostra_valor(df_ultimo, "Saída"), "°C", "bi bi-arrow-up-circle", "red", "red")
    with col4:
        exibir_card("DIF", mostra_valor(df_ultimo, "DeltaT"), "°C", "bi bi-arrow-down-up")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        exibir_card("Tensão", mostra_valor(df_ultimo, "Tensao"), "V", "bi bi-lightning-charge")
    with col6:
        exibir_card("Corrente", mostra_valor(df_ultimo, "Corrente"), "A", "bi bi-lightning")
    with col7:
        exibir_card("kcal/h", mostra_valor(df_ultimo, "Kcal_h"), "", "bi bi-fire")
    with col8:
        exibir_card("Vazão", mostra_valor(df_ultimo, "Vazao"), "L/min", "bi bi-water")

    col9, col10 = st.columns(2)
    with col9:
        exibir_card("kW Aquecimento", mostra_valor(df_ultimo, "KWAquecimento"), "kW", "bi bi-sun")
    with col10:
        exibir_card("kW Consumo", mostra_valor(df_ultimo, "KWConsumo"), "kW", "bi bi-power")

    # Card para COP
    st.markdown("---")
    st.subheader("Performance")
    col_cop, _, _, _ = st.columns(4) # Usar colunas para centralizar ou alinhar
    with col_cop:
        exibir_card("COP", mostra_valor(df_ultimo, "COP"), "", "bi bi-graph-up")

else:
    st.info("Não foi possível carregar a última leitura. Verifique se há arquivos CSV válidos na pasta de dados ou com os filtros aplicados.")


st.markdown("---")
st.header("Históricos Disponíveis")

if not arquivos_filtrados:
    st.info("Nenhum histórico encontrado com os filtros aplicados.")
else:
    for arq in arquivos_filtrados:
        with st.expander(f"{arq['nome_arquivo']} (Modelo: {arq['modelo']}, OP: {arq['operacao']}, Data: {arq['data_arquivo']} {arq['hora_arquivo']})", expanded=False):
            st.write(f"Caminho: {arq['caminho']}")
            st.write(f"Data modificação: {arq['data_modificacao'].strftime('%d/%m/%Y %H:%M:%S')}")
            # Aqui você pode adicionar um botão para ver o conteúdo completo do CSV ou gerar PDF/Excel
            # Por enquanto, vamos focar em listar e ler.

# =========================
#  ABA DE GRÁFICOS (Simplificada por enquanto)
# =========================
st.markdown("---")
st.header("Visualização Gráfica")

if not arquivos_filtrados:
    st.info("Nenhum dado disponível para gerar gráficos com os filtros aplicados.")
else:
    # Seleção de arquivo para o gráfico
    nomes_arquivos_para_grafico = [arq["nome_arquivo"] for arq in arquivos_filtrados]
    arquivo_selecionado_graf = st.selectbox(
        "Selecione um arquivo para visualizar o gráfico:",
        nomes_arquivos_para_grafico
    )

    if arquivo_selecionado_graf:
        info_graf = next((arq for arq in arquivos_filtrados if arq["nome_arquivo"] == arquivo_selecionado_graf), None)
        if info_graf:
            try:
                df_graf = carregar_csv_caminho(info_graf["caminho"])
                if df_graf.empty:
                    st.warning("O arquivo selecionado está vazio ou não pôde ser carregado.")
                else:
                    st.markdown("### Variáveis para o gráfico")

                    # Garante que apenas as variáveis presentes no DF sejam mostradas
                    variaveis_disponiveis_no_df = [
                        v for v in [
                            "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                            "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
                        ] if v in df_graf.columns
                    ]

                    vars_selecionadas = st.multiselect(
                        "Selecione uma ou mais variáveis:",
                        variaveis_disponiveis_no_df,
                        default=[v for v in ["Ambiente", "Entrada", "Saída"] if v in variaveis_disponiveis_no_df],
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
                            title=f"Gráfico - Modelo {info_graf['modelo']} | OP {info_graf['operacao']} | {info_graf['data_arquivo']}",
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
            except Exception as e:
                st.error(f"Erro ao carregar dados para o gráfico: {e}")
                st.info("Verifique se o arquivo CSV está no formato correto.")