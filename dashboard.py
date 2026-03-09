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
        r"(?:(\d{4})_)?"         # Grupo 3: Hora (ex: 0016), opcional (?: para não capturar se não existir)
        r"OP([A-Z0-9]+)_"        # Grupo 4: Operação (ex: 456, 7777, HHH)
        r"(FT([A-Z0-9]+))?"      # Grupo 5: FT completo (ex: FT123L), Grupo 6: Identificador FT (ex: 123L), ambos opcionais
        r"\.csv"
    )

    for arquivo_path in arquivos_encontrados:
        nome_arquivo = os.path.basename(arquivo_path)
        match = regex_padrao.match(nome_arquivo)

        if match:
            modelo = match.group(1)
            data_str = match.group(2)
            hora_str = match.group(3) if match.group(3) else "0000" # Se hora for opcional, use 0000
            operacao = match.group(4)
            identificador_ft = match.group(6) if match.group(6) else "N/D" # Se FT for opcional, use N/D

            try:
                data_hora_obj = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")
                todos_arquivos_meta.append({
                    "nome_arquivo": nome_arquivo,
                    "caminho_completo": arquivo_path,
                    "modelo": modelo if modelo else "N/D",
                    "data": data_hora_obj.date(),
                    "hora": data_hora_obj.time(),
                    "ano": data_hora_obj.year,
                    "mes": data_hora_obj.strftime("%B").capitalize(), # Nome do mês
                    "operacao": operacao if operacao else "N/D",
                    "identificador_ft": identificador_ft,
                    "timestamp": data_hora_obj.timestamp() # Para ordenação
                })
            except ValueError:
                st.warning(f"Erro ao processar data/hora do arquivo: {nome_arquivo}. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.")

    # Ordenar os arquivos pelo timestamp (mais recente primeiro)
    todos_arquivos_meta.sort(key=lambda x: x['timestamp'], reverse=True)
    return todos_arquivos_meta

@st.cache_data(ttl=3600) # Cacheia os dados por 1 hora
def carregar_csv(caminho_arquivo):
    """
    Carrega um arquivo CSV, tenta detectar o delimitador e converte colunas para numérico/datetime.
    """
    try:
        # Tenta ler com vírgula, depois com ponto e vírgula
        try:
            df = pd.read_csv(caminho_arquivo, sep=',')
        except Exception:
            df = pd.read_csv(caminho_arquivo, sep=';')

        # Limpeza de nomes de coluna (remover espaços, caracteres especiais)
        df.columns = df.columns.str.strip().str.replace(r'[^\w\s]', '', regex=True).str.replace(' ', '_', regex=False).str.lower()

        # Tentar converter colunas para numérico, tratando erros
        for col in df.columns:
            # Tenta converter para datetime primeiro
            if 'data' in col or 'hora' in col or 'timestamp' in col:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    pass # Se falhar, tenta como numérico ou deixa como está

            # Tenta converter para numérico (float), tratando erros
            try:
                # Substitui vírgula por ponto para números decimais antes da conversão
                if df[col].dtype == 'object': # Só tenta se for string/object
                    df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass # Se falhar, deixa a coluna como está

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# -------------------------------------------------
# 4. FUNÇÕES DE GERAÇÃO DE PDF E EXCEL
# -------------------------------------------------

def gerar_pdf(df, nome_arquivo_base):
    """
    Gera um PDF a partir de um DataFrame usando fpdf2.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(200, 10, txt=f"Relatório de Dados - {nome_arquivo_base}", ln=True, align='C')
    pdf.ln(10)

    # Adicionar o DataFrame ao PDF
    # Cabeçalhos
    pdf.set_font("Arial", 'B', size=10)
    col_widths = [pdf.w / (len(df.columns) + 1)] * len(df.columns) # Distribui larguras igualmente
    if len(df.columns) > 0:
        for i, col in enumerate(df.columns):
            pdf.cell(col_widths[i], 10, str(col), border=1, align='C')
        pdf.ln()

        # Dados
        pdf.set_font("Arial", size=8)
        for index, row in df.iterrows():
            for i, col in enumerate(df.columns):
                cell_value = str(row[col])
                # Limita o tamanho da célula para evitar estouro
                if len(cell_value) > 20:
                    cell_value = cell_value[:17] + "..."
                pdf.cell(col_widths[i], 8, cell_value, border=1, align='C')
            pdf.ln()
    else:
        pdf.cell(200, 10, "Nenhum dado para exibir.", ln=True, align='C')

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    return pdf_output.getvalue()

def to_excel(df):
    """
    Converte um DataFrame para um arquivo Excel (BytesIO).
    """
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close() # Use .close() para versões mais recentes do pandas/xlsxwriter
    processed_data = output.getvalue()
    return processed_data

# -------------------------------------------------
# 5. LAYOUT DO STREAMLIT
# -------------------------------------------------

st.markdown('<div class="main-header">Dashboard de Teste de Máquinas Fromtherm</div>', unsafe_allow_html=True)

# BARRA LATERAL (FILTROS)
# -------------------------------------------------
# Substitua pela URL da sua logo. Se não tiver, comente a linha.
st.sidebar.image("https://i.imgur.com/7gZ0G22.png", use_column_width=True)
st.sidebar.title("Filtros de Busca")

todos_arquivos_meta = buscar_arquivos()

if todos_arquivos_meta:
    # Extrair opções únicas para os filtros
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos_meta if a['modelo'] != 'N/D'])))
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos_meta if a['operacao'] != 'N/D'])))
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos_meta])), reverse=True)
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos_meta])))
    datas_unicas = sorted(list(set([a['data'] for a in todos_arquivos_meta])), reverse=True)

    # Adicionar "Todos" como opção para os filtros
    modelos_filtro = ["Todos"] + modelos_unicos
    operacoes_filtro = ["Todos"] + operacoes_unicas
    anos_filtro = ["Todos"] + anos_unicos
    meses_filtro = ["Todos"] + meses_unicos
    datas_filtro = ["Todos"] + [d.strftime("%d/%m/%Y") for d in datas_unicas]

    # Widgets de filtro
    modelo_selecionado = st.sidebar.selectbox("Modelo", modelos_filtro)
    operacao_selecionada = st.sidebar.selectbox("Operação", operacoes_filtro)
    ano_selecionado = st.sidebar.selectbox("Ano", anos_filtro)
    mes_selecionado = st.sidebar.selectbox("Mês", meses_filtro)
    data_selecionada = st.sidebar.selectbox("Data", datas_filtro)

    # Aplicar filtros
    arquivos_filtrados = todos_arquivos_meta
    if modelo_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == modelo_selecionado]
    if operacao_selecionada != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == operacao_selecionada]
    if ano_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == ano_selecionado]
    if mes_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == mes_selecionado]
    if data_selecionada != "Todos":
        data_obj_selecionada = datetime.strptime(data_selecionada, "%d/%m/%Y").date()
        arquivos_filtrados = [a for a in arquivos_filtrados if a['data'] == data_obj_selecionada]

    # Exibir cards de última leitura (se houver arquivos filtrados)
    if arquivos_filtrados:
        st.subheader("Últimas Leituras")
        col1, col2, col3, col4 = st.columns(4)

        # O arquivo mais recente já está no topo da lista ordenada
        ultimo_arquivo_meta = arquivos_filtrados[0]
        df_ultimo = carregar_csv(ultimo_arquivo_meta['caminho_completo'])

        if not df_ultimo.empty:
            # Tenta pegar a última linha para os valores mais recentes
            ultima_linha = df_ultimo.iloc[-1]

            # Mapeamento de colunas para exibição nos cards
            # Ajuste os nomes das colunas conforme o seu CSV real
            cards_info = {
                "Temperatura": ultima_linha.get('temperatura', 'N/D'),
                "Pressão": ultima_linha.get('pressao', 'N/D'),
                "Vazão": ultima_linha.get('vazao', 'N/D'),
                "Status": ultima_linha.get('status', 'N/D')
            }

            with col1:
                st.markdown(f"""
                    <div class="ft-card">
                        <span class="ft-icon">🌡️</span>
                        <span class="ft-label">Temperatura</span>
                        <span class="ft-value">{cards_info['Temperatura'] if cards_info['Temperatura'] != 'N/D' else 'N/D'}</span>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                    <div class="ft-card">
                        <span class="ft-icon">壓力</span>
                        <span class="ft-label">Pressão</span>
                        <span class="ft-value">{cards_info['Pressão'] if cards_info['Pressão'] != 'N/D' else 'N/D'}</span>
                    </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                    <div class="ft-card">
                        <span class="ft-icon">💧</span>
                        <span class="ft-label">Vazão</span>
                        <span class="ft-value">{cards_info['Vazão'] if cards_info['Vazão'] != 'N/D' else 'N/D'}</span>
                    </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                    <div class="ft-card">
                        <span class="ft-icon">✅</span>
                        <span class="ft-label">Status</span>
                        <span class="ft-value">{cards_info['Status'] if cards_info['Status'] != 'N/D' else 'N/D'}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não foi possível carregar dados do último arquivo para os cards.")
    else:
        st.info("Nenhum arquivo encontrado para as últimas leituras com os filtros aplicados.")

    # Abas para Históricos e Gráficos
    tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

    with tab1:
        st.subheader("Históricos Disponíveis")
        if arquivos_filtrados:
            for arquivo_meta in arquivos_filtrados:
                with st.expander(f"**{arquivo_meta['nome_arquivo']}** (Modelo: {arquivo_meta['modelo']}, Data: {arquivo_meta['data'].strftime('%d/%m/%Y')}, Operação: {arquivo_meta['operacao']})"):
                    df_exibir = carregar_csv(arquivo_meta['caminho_completo'])
                    if not df_exibir.empty:
                        st.dataframe(df_exibir)

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            # Botão de Download PDF
                            pdf_data = gerar_pdf(df_exibir, arquivo_meta['nome_arquivo'].replace('.csv', ''))
                            st.download_button(
                                label="Download PDF",
                                data=pdf_data,
                                file_name=f"{arquivo_meta['nome_arquivo'].replace('.csv', '')}.pdf",
                                mime="application/pdf"
                            )
                        with col_dl2:
                            # Botão de Download Excel
                            excel_data = to_excel(df_exibir)
                            st.download_button(
                                label="Download Excel",
                                data=excel_data,
                                file_name=f"{arquivo_meta['nome_arquivo'].replace('.csv', '')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning(f"Não foi possível exibir dados para {arquivo_meta['nome_arquivo']}.")
        else:
            st.info("Nenhum histórico encontrado com os filtros aplicados.")

    with tab2:
        st.subheader("Crie Seu Gráfico")
        if arquivos_filtrados:
            # Seleção de arquivo para o gráfico
            nomes_arquivos_para_selecao = [a['nome_arquivo'] for a in arquivos_filtrados]
            arquivo_selecionado_nome = st.selectbox("Selecione um arquivo para o gráfico", nomes_arquivos_para_selecao)

            if arquivo_selecionado_nome:
                arquivo_meta_selecionado = next((a for a in arquivos_filtrados if a['nome_arquivo'] == arquivo_selecionado_nome), None)
                if arquivo_meta_selecionado:
                    df_grafico = carregar_csv(arquivo_meta_selecionado['caminho_completo'])

                    if not df_grafico.empty:
                        # Tentar identificar colunas numéricas e de tempo
                        colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()
                        colunas_tempo = df_grafico.select_dtypes(include=['datetime64']).columns.tolist()

                        if not colunas_tempo:
                            st.warning("Nenhuma coluna de tempo (datetime) encontrada para o eixo X. O gráfico pode não ser ideal.")
                            # Se não houver coluna de tempo, use o índice ou a primeira coluna numérica como X
                            eixo_x_opcoes = ['(Índice)'] + colunas_numericas
                        else:
                            eixo_x_opcoes = colunas_tempo + colunas_numericas # Preferir tempo, mas aceitar numérico

                        if not colunas_numericas:
                            st.warning("Nenhuma coluna numérica encontrada para o eixo Y. Não é possível gerar o gráfico.")
                        else:
                            col_g1, col_g2 = st.columns(2)
                            with col_g1:
                                eixo_x = st.selectbox("Selecione a coluna para o Eixo X", eixo_x_opcoes)
                            with col_g2:
                                eixo_y = st.multiselect("Selecione as colunas para o Eixo Y", colunas_numericas)

                            if eixo_x and eixo_y:
                                if eixo_x == '(Índice)':
                                    df_grafico['index_col'] = df_grafico.index
                                    x_col = 'index_col'
                                else:
                                    x_col = eixo_x

                                fig = px.line(df_grafico, x=x_col, y=eixo_y,
                                              title=f"Gráfico de {', '.join(eixo_y)} por {eixo_x} para {arquivo_selecionado_nome}")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Selecione as colunas para os eixos X e Y para gerar o gráfico.")
                    else:
                        st.warning(f"Não foi possível carregar dados para o gráfico do arquivo {arquivo_selecionado_nome}.")
                else:
                    st.error("Erro interno: Metadados do arquivo selecionado não encontrados.")
            else:
                st.info("Selecione um arquivo para começar a criar seu gráfico.")
        else:
            st.info("Nenhum arquivo disponível para gerar gráficos com os filtros aplicados.")
else:
    st.warning("Nenhum arquivo CSV encontrado na pasta 'dados_brutos'. Certifique-se de que os arquivos estão lá e seguem o padrão de nome esperado.")
