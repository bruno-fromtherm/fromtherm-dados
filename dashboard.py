import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

# Importações para FPDF2
from fpdf import FPDF
from io import BytesIO

import plotly.express as px

# -------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# 2. CSS PARA DASHBOARD ATRATIVO (Remoção do "0" e ajuste mobile)
# -------------------------------------------------
st.markdown("""
    <style>
    /* Esconder elementos estranhos do Streamlit e o "0" teimoso */
    header {visibility: hidden;}
    div[data-testid="stAppViewContainer"] > div:first-child span { display: none !important; }
    button[data-testid="stSidebarNavToggle"] { display: none !important; }
    summary { display: none !important; }

    .stApp { background-color: #f4f7f6; }

    /* Cabeçalho Principal */
    .main-header {
        color: #003366; font-size: 26px; font-weight: 800; text-align: center;
        padding: 15px; border-bottom: 4px solid #003366; margin-bottom: 25px;
        background-color: white; border-radius: 10px;
    }

    /* Estilo dos Cards (Dashboards) */
    .ft-card {
        background: white; border-radius: 12px; padding: 15px; text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 15px;
        border-top: 6px solid #003366; transition: 0.3s;
        display: flex; align-items: center; justify-content: center; flex-direction: column;
    }
    .ft-card:hover { transform: translateY(-5px); }
    .ft-icon { font-size: 35px; margin-bottom: 8px; display: block; color: #003366; }
    .ft-label { font-size: 12px; font-weight: 700; color: #666; text-transform: uppercase; }
    .ft-value { font-size: 24px; font-weight: 800; color: #333; margin-top: 5px; }

    /* Estilo para tabelas e expansores */
    .stExpander { border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander > div > div > div > div > p { font-weight: 600; color: #003366; } /* Título do Expander */

    /* Ajustes para botões de download */
    .stDownloadButton > button {
        background-color: #003366; color: white; border-radius: 5px; border: none;
        padding: 8px 15px; font-size: 14px; cursor: pointer; transition: 0.3s;
        margin-right: 10px;
    }
    .stDownloadButton > button:hover { background-color: #0055aa; }

    /* Estilo para abas */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. FUNÇÕES DE CARREGAMENTO E PROCESSAMENTO DE DADOS
# -------------------------------------------------

# Caminho para a pasta de dados brutos (no Streamlit Cloud, é a pasta 'dados_brutos' no mesmo nível do app)
DADOS_BRUTOS_PATH = "dados_brutos"

@st.cache_data(ttl=3600) # Cacheia os dados por 1 hora
def buscar_arquivos():
    """
    Busca arquivos CSV na pasta DADOS_BRUTOS_PATH e extrai metadados.
    O regex foi ajustado para ser mais flexível.
    """
    arquivos_encontrados = glob.glob(os.path.join(DADOS_BRUTOS_PATH, "*.csv"))
    todos_arquivos_meta = []

    # Regex mais flexível para capturar os componentes do nome do arquivo
    # Exemplo: historico_L1_20260307_0016_OP456_FT123L.csv
    # Exemplo: historico_L1_20260307_TESTE_NOVO.csv
    # Exemplo: historico_L1_20260305_2257_OP7777_FT140KK.csv
    # Exemplo: historico_L1_20260305_1848_OP555_195HH.csv
    # Exemplo: historico_L1_20260306_2250_OPHHH_FT888.csv
    # O regex tenta ser mais genérico para os campos de OP e FT, aceitando letras e números.
    # A parte de data e hora é mais estrita para garantir que seja uma data/hora válida.
    # O grupo para 'hora' agora é opcional, e o grupo para 'identificador_ft' também.
    # O grupo para 'operacao' também é mais flexível.
    regex_padrao = re.compile(
        r"historico_([A-Z0-9]+)_" # Grupo 1: Modelo (ex: L1)
        r"(\d{8})_"              # Grupo 2: Data (ex: 20260307)
        r"(?:(\d{4})_)?"         # Grupo 3: Hora (ex: 0016) - Opcional (?:...)
        r"OP([A-Z0-9]+)_"        # Grupo 4: Operação (ex: OP456, OP7777, OPHHH)
        r"FT([A-Z0-9]+)\.csv"    # Grupo 5: Identificador FT (ex: FT123L, FT140KK, FT888)
    )

    for arquivo_path in arquivos_encontrados:
        nome_arquivo = os.path.basename(arquivo_path)
        match = regex_padrao.match(nome_arquivo)

        if match:
            modelo = match.group(1)
            data_str = match.group(2)
            hora_str = match.group(3) if match.group(3) else "0000" # Se hora for opcional e não existir, usa 0000
            operacao = match.group(4)
            identificador_ft = match.group(5)

            try:
                data_hora_obj = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")
                todos_arquivos_meta.append({
                    "nome_arquivo": nome_arquivo,
                    "caminho_completo": arquivo_path,
                    "modelo": modelo,
                    "data": data_hora_obj.date(),
                    "ano": data_hora_obj.year,
                    "mes": data_hora_obj.month,
                    "hora": data_hora_obj.time(),
                    "operacao": operacao,
                    "identificador_ft": identificador_ft
                })
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.")
    return pd.DataFrame(todos_arquivos_meta)

@st.cache_data(ttl=3600) # Cacheia os dados por 1 hora
def carregar_csv(caminho_arquivo):
    """
    Carrega um arquivo CSV, tenta inferir o separador e converte colunas para numérico/data.
    """
    try:
        # Tenta carregar com o separador padrão (vírgula)
        df = pd.read_csv(caminho_arquivo, sep=',')
    except Exception:
        # Se falhar, tenta com ponto e vírgula
        try:
            df = pd.read_csv(caminho_arquivo, sep=';')
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
            return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

    # Converte colunas para numérico, tratando erros
    for col in df.columns:
        # Tenta converter para numérico, se falhar, mantém o tipo original
        df[col] = pd.to_numeric(df[col], errors='coerce')

        # Tenta converter para datetime, se falhar, mantém o tipo original
        # Isso é mais seguro do que usar errors='coerce' diretamente em to_datetime para todas as colunas
        try:
            df[col] = pd.to_datetime(df[col], errors='raise') # 'raise' para pegar erros específicos
        except (ValueError, TypeError):
            pass # Não é uma coluna de data, ignora

    return df

# -------------------------------------------------
# 4. LAYOUT DA BARRA LATERAL
# -------------------------------------------------
st.sidebar.image("https://i.imgur.com/7gZ0G22.png", use_column_width=True) # Sua logo Fromtherm

st.sidebar.markdown("## Filtros de Histórico")

# Carrega metadados de todos os arquivos
df_meta = buscar_arquivos()

# Verifica se há arquivos encontrados
if not df_meta.empty:
    # Filtros baseados nos metadados
    modelos_disponiveis = ["Todos"] + sorted(df_meta["modelo"].unique().tolist())
    modelo_selecionado = st.sidebar.selectbox("Selecione o Modelo", modelos_disponiveis)

    anos_disponiveis = ["Todos"] + sorted(df_meta["ano"].unique().tolist(), reverse=True)
    ano_selecionado = st.sidebar.selectbox("Selecione o Ano", anos_disponiveis)

    meses_disponiveis = ["Todos"] + sorted(df_meta["mes"].unique().tolist())
    mes_selecionado = st.sidebar.selectbox("Selecione o Mês", meses_disponiveis, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else x)

    datas_disponiveis = ["Todas"] + sorted(df_meta["data"].unique().tolist(), reverse=True)
    data_selecionada = st.sidebar.selectbox("Selecione a Data", datas_disponiveis)

    operacoes_disponiveis = ["Todas"] + sorted(df_meta["operacao"].unique().tolist())
    operacao_selecionada = st.sidebar.selectbox("Selecione a Operação", operacoes_disponiveis)

    # Aplica os filtros
    df_filtrado = df_meta.copy()
    if modelo_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["modelo"] == modelo_selecionado]
    if ano_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["ano"] == ano_selecionado]
    if mes_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes"] == mes_selecionado]
    if data_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["data"] == data_selecionada]
    if operacao_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["operacao"] == operacao_selecionada]

    # Ordena por data e hora (mais recente primeiro)
    df_filtrado = df_filtrado.sort_values(by=["data", "hora"], ascending=False)

    # Última Leitura
    if not df_filtrado.empty:
        ultimo_arquivo_meta = df_filtrado.iloc[0]
        ultimo_df = carregar_csv(ultimo_arquivo_meta["caminho_completo"])
        if not ultimo_df.empty:
            ultima_leitura_temp = ultimo_df["Temperatura"].iloc[-1] if "Temperatura" in ultimo_df.columns else "N/D"
            ultima_leitura_pressao = ultimo_df["Pressao"].iloc[-1] if "Pressao" in ultimo_df.columns else "N/D"
            ultima_leitura_vazao = ultimo_df["Vazao"].iloc[-1] if "Vazao" in ultimo_df.columns else "N/D"
        else:
            ultima_leitura_temp = "N/D"
            ultima_leitura_pressao = "N/D"
            ultima_leitura_vazao = "N/D"
    else:
        ultima_leitura_temp = "N/D"
        ultima_leitura_pressao = "N/D"
        ultima_leitura_vazao = "N/D"

else:
    st.sidebar.warning("Nenhum arquivo CSV encontrado para filtrar.")
    ultima_leitura_temp = "N/D"
    ultima_leitura_pressao = "N/D"
    ultima_leitura_vazao = "N/D"
    df_filtrado = pd.DataFrame() # Garante que df_filtrado seja um DataFrame vazio

# -------------------------------------------------
# 5. LAYOUT PRINCIPAL
# -------------------------------------------------
st.markdown('<div class="main-header">Dashboard de Teste de Máquinas Fromtherm</div>', unsafe_allow_html=True)

# Cards de Última Leitura
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon">🌡️</span>
            <span class="ft-label">Última Temperatura</span>
            <span class="ft-value">{ultima_leitura_temp:.2f} °C</span>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon">壓力</span>
            <span class="ft-label">Última Pressão</span>
            <span class="ft-value">{ultima_leitura_pressao:.2f} bar</span>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon">💧</span>
            <span class="ft-label">Última Vazão</span>
            <span class="ft-value">{ultima_leitura_vazao:.2f} L/min</span>
        </div>
    """, unsafe_allow_html=True)

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("### Históricos Disponíveis")
    if not df_filtrado.empty:
        for index, row in df_filtrado.iterrows():
            with st.expander(f"**{row['nome_arquivo']}** - Modelo: {row['modelo']}, Data: {row['data']}, Operação: {row['operacao']}"):
                df_exibir = carregar_csv(row["caminho_completo"])
                if not df_exibir.empty:
                    st.dataframe(df_exibir)

                    # Botões de Download
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Download PDF
                        pdf_buffer = gerar_pdf(df_exibir, row['nome_arquivo'])
                        st.download_button(
                            label="Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{row['nome_arquivo'].replace('.csv', '')}.pdf",
                            mime="application/pdf",
                            key=f"pdf_dl_{index}"
                        )
                    with col_dl2:
                        # Download Excel
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            df_exibir.to_excel(writer, index=False, sheet_name='Dados')
                        st.download_button(
                            label="Download Excel",
                            data=excel_buffer.getvalue(),
                            file_name=f"{row['nome_arquivo'].replace('.csv', '')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"excel_dl_{index}"
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para {row['nome_arquivo']}.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.markdown("### Crie Seu Gráfico")
    if not df_filtrado.empty:
        # Seleção de arquivo para o gráfico
        arquivos_para_grafico = df_filtrado["nome_arquivo"].tolist()
        arquivo_selecionado_grafico = st.selectbox("Selecione um arquivo para gerar o gráfico", arquivos_para_grafico)

        if arquivo_selecionado_grafico:
            caminho_completo_grafico = df_filtrado[df_filtrado["nome_arquivo"] == arquivo_selecionado_grafico]["caminho_completo"].iloc[0]
            df_grafico = carregar_csv(caminho_completo_grafico)

            if not df_grafico.empty:
                colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()
                if "Tempo" in colunas_numericas:
                    colunas_numericas.remove("Tempo") # 'Tempo' geralmente é o eixo X

                if colunas_numericas:
                    variavel_y = st.selectbox("Selecione a variável para o eixo Y", colunas_numericas)

                    if "Tempo" in df_grafico.columns:
                        fig = px.line(df_grafico, x="Tempo", y=variavel_y,
                                      title=f"Gráfico de {variavel_y} ao longo do Tempo para {arquivo_selecionado_grafico}",
                                      labels={"Tempo": "Tempo (segundos)", variavel_y: variavel_y})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("A coluna 'Tempo' não foi encontrada no arquivo para gerar o gráfico de linha. Por favor, verifique o CSV.")
                else:
                    st.warning("Nenhuma coluna numérica encontrada no arquivo selecionado para gerar gráficos.")
            else:
                st.warning("Não foi possível carregar os dados do arquivo selecionado para o gráfico.")
        else:
            st.info("Selecione um arquivo para começar a criar seu gráfico.")
    else:
        st.info("Nenhum arquivo disponível para gerar gráficos com os filtros aplicados.")
