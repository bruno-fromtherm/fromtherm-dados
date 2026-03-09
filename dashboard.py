import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
# from reportlab.lib.units import inch  # <-- REMOVIDO PARA EVITAR NameError

from io import BytesIO
import plotly.express as px

# -------------------------------------------------
# Configuração básica
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS simples (mantém layout, não mexe em nada estrutural)
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde o botão de menu do Streamlit, que geralmente contém o "0" */
    button[data-testid="stSidebarNavToggle"] {
        display: none !important;
    }
    /* Esconde o elemento que pode conter o "0" em alguns casos */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Outras tentativas de esconder elementos que podem aparecer */
    summary {
        display: none !important;
    }
    div[data-testid="stAppViewContainer"] > div:first-child span {
        display: none !important;
    }

    /* Estilo dos cards */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .ft-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .ft-icon {
        font-size: 28px;
        margin-right: 12px;
        color: #0d6efd;
    }
    .ft-content {
        flex-grow: 1;
    }
    .ft-label {
        font-size: 11px;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .ft-value {
        font-size: 18px;
        color: #343a40;
        font-weight: 700;
    }

    /* Estilo para os botões de download */
    .stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #0d6efd;
        color: #0d6efd;
        background-color: #e9f0ff;
        padding: 8px 12px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stDownloadButton > button:hover {
        background-color: #0d6efd;
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Estilo para abas */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: 600;
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

# -------------------------------------------------
# Funções Auxiliares
# -------------------------------------------------

# Função para exibir cards
def mostra_valor(label, value, unit, icon):
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon">{icon}</span>
            <div class="ft-content">
                <div class="ft-label">{label}</div>
                <div class="ft-value">{value} {unit}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 3. CONFIGURAÇÃO DE DADOS
# DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"
# Ajuste para o caminho correto que você mencionou
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150" # A pasta 'datalog' será adicionada no glob

@st.cache_data(ttl=5)
def buscar_arquivos():
    # Ajusta o glob para procurar em 'datalog' dentro do DADOS_DIR
    caminho_completo_datalog = os.path.join(DADOS_DIR, "datalog")
    if not os.path.exists(caminho_completo_datalog):
        st.error(f"Diretório de dados não encontrado: {caminho_completo_datalog}")
        return []

    caminhos = glob.glob(os.path.join(caminho_completo_datalog, "*.csv"))
    lista = []
    for c in caminhos:
        n = os.path.basename(c)

        # Novo padrão de regex para extrair informações do nome do arquivo
        # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
        # Ex: historico_L1_20260307_TESTE_NOVO.csv (será tratado como N/D para OP e Modelo)
        match = re.match(r"historico_L1_(\d{8})_(\d{4})_?([A-Za-z0-9]+)?_?([A-Za-z0-9]+)?\.csv", n)

        data_str = "N/D"
        hora_str = "N/D"
        operacao_str = "N/D"
        modelo_str = "N/D"

        if match:
            data_str = match.group(1)
            hora_str = match.group(2)
            if match.group(3):
                operacao_str = match.group(3)
            if match.group(4):
                modelo_str = match.group(4)

            try:
                data_obj = datetime.strptime(data_str, "%Y%m%d").date()
                data_formatada = data_obj.strftime("%d/%m/%Y")
                ano = data_obj.year
                mes = data_obj.month
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido: {n}. Não foi possível extrair a data. Ignorando.")
                continue # Pula este arquivo se a data for inválida
        else:
            st.warning(f"Nome de arquivo CSV inválido: {n}. Não segue o padrão esperado. Ignorando.")
            continue # Pula este arquivo se o padrão não for encontrado

        lista.append({
            "caminho": c,
            "nome_arquivo": n,
            "data_raw": data_obj,
            "data_f": data_formatada,
            "hora": hora_str,
            "operacao": operacao_str,
            "modelo": modelo_str,
            "ano": ano,
            "mes": mes
        })
    return sorted(lista, key=lambda x: x['data_raw'], reverse=True)

@st.cache_data(ttl=5)
def carregar_csv(caminho_arquivo):
    try:
        # Tenta ler com o separador '|'
        df = pd.read_csv(caminho_arquivo, sep='|', skipinitialspace=True)

        # Limpar espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Converte colunas numéricas, tratando '000.0' como 0.0
        for col in ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']:
            if col in df.columns:
                # Substitui vírgulas por pontos para números decimais (se houver)
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                # Converte para numérico, forçando erros para NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Preenche NaN com 0, se for o caso de valores como '000.0' que viraram NaN
                df[col] = df[col].fillna(0.0)

        # Remove a linha de separação '---' se ela foi lida como dados
        df = df[df['Date'] != '---']

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

# -------------------------------------------------
# Layout do Dashboard
# -------------------------------------------------

st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

# Sidebar para filtros
st.sidebar.header("Filtros de Busca")

arquivos_disponiveis = buscar_arquivos()

if not arquivos_disponiveis:
    st.warning("Nenhum histórico disponível para análise. Verifique o diretório de dados.")
    st.stop() # Para a execução do script se não houver arquivos

# Extrair opções únicas para os filtros
modelos_unicos = sorted(list(set([a['modelo'] for a in arquivos_disponiveis if a['modelo'] != 'N/D'])))
operacoes_unicas = sorted(list(set([a['operacao'] for a in arquivos_disponiveis if a['operacao'] != 'N/D'])))
anos_unicos = sorted(list(set([a['ano'] for a in arquivos_disponiveis])), reverse=True)
meses_unicos = sorted(list(set([a['mes'] for a in arquivos_disponiveis])))

# Mapeamento de número do mês para nome
meses_nomes = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
meses_nomes_invertido = {v: k for k, v in meses_nomes.items()}

# Filtros na sidebar
sel_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
sel_operacao = st.sidebar.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
sel_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
sel_mes_nome = st.sidebar.selectbox("Mês", ["Todos"] + [meses_nomes[m] for m in meses_unicos])
sel_mes = meses_nomes_invertido.get(sel_mes_nome, "Todos")

# Filtrar arquivos com base nas seleções
arquivos_filtrados = arquivos_disponiveis
if sel_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == sel_modelo]
if sel_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == sel_operacao]
if sel_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == sel_ano]
if sel_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == sel_mes]

# Ordenar arquivos filtrados por data (mais recente primeiro)
arquivos_filtrados = sorted(arquivos_filtrados, key=lambda x: x['data_raw'], reverse=True)

# --- Última Leitura Registrada (Cards) ---
st.subheader("Última Leitura Registrada")
if arquivos_filtrados:
    ultimo_arquivo = arquivos_filtrados[0]
    df_ultima_leitura = carregar_csv(ultimo_arquivo['caminho'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha do CSV

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            mostra_valor("Temperatura Ambiente", f"{ultima_linha.get('ambiente', 'N/D'):.2f}", "°C", "bi-thermometer-half")
            mostra_valor("Temperatura Entrada", f"{ultima_linha.get('entrada', 'N/D'):.2f}", "°C", "bi-arrow-down-circle")
        with col2:
            mostra_valor("Temperatura Saída", f"{ultima_linha.get('saida', 'N/D'):.2f}", "°C", "bi-arrow-up-circle")
            mostra_valor("Diferença Temp.", f"{ultima_linha.get('dif', 'N/D'):.2f}", "°C", "bi-arrow-left-right")
        with col3:
            mostra_valor("Tensão", f"{ultima_linha.get('tensao', 'N/D'):.1f}", "V", "bi-lightning-charge")
            mostra_valor("Corrente", f"{ultima_linha.get('corrente', 'N/D'):.1f}", "A", "bi-lightning")
        with col4:
            mostra_valor("Vazão", f"{ultima_linha.get('vazao', 'N/D'):.0f}", "L/min", "bi-droplet-half")
            mostra_valor("COP", f"{ultima_linha.get('cop', 'N/D'):.2f}", "", "bi-bar-chart-line")
    else:
        st.info("Não foi possível carregar dados para a última leitura com os filtros aplicados.")
else:
    st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")

st.markdown("---")

# --- Abas para Históricos e Gráficos ---
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Históricos Disponíveis")
    if arquivos_filtrados:
        # Filtro de data específico para a lista de históricos
        datas_para_lista = sorted(list(set([a['data_f'] for a in arquivos_filtrados])), reverse=True)
        sel_data_lista = st.selectbox("Filtrar por Data", ["Todos"] + datas_para_lista, key="data_lista")

        arquivos_para_exibir = arquivos_filtrados
        if sel_data_lista != "Todos":
            arquivos_para_exibir = [a for a in arquivos_filtrados if a['data_f'] == sel_data_lista]

        if arquivos_para_exibir:
            for arquivo_info in arquivos_para_exibir:
                expander_title = f"**{arquivo_info['data_f']} - {arquivo_info['hora']}** | Modelo: **{arquivo_info['modelo']}** | Operação: **{arquivo_info['operacao']}**"
                with st.expander(expander_title):
                    df_historico = carregar_csv(arquivo_info['caminho'])
                    if not df_historico.empty:
                        st.dataframe(df_historico, use_container_width=True)

                        # Botões de download
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            # Download PDF
                            pdf_buffer = criar_pdf(df_historico, arquivo_info)
                            st.download_button(
                                label="Baixar PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"relatorio_{arquivo_info['modelo']}_{arquivo_info['operacao']}_{arquivo_info['data_f'].replace('/', '-')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        with col_dl2:
                            # Download Excel
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                df_historico.to_excel(writer, index=False, sheet_name='Dados')
                            st.download_button(
                                label="Baixar Excel",
                                data=excel_buffer.getvalue(),
                                file_name=f"dados_{arquivo_info['modelo']}_{arquivo_info['operacao']}_{arquivo_info['data_f'].replace('/', '-')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    else:
                        st.warning(f"Não foi possível exibir os dados para {arquivo_info['nome_arquivo']}.")
        else:
            st.info("Nenhum histórico encontrado para a data selecionada.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico Personalizado")
    if arquivos_disponiveis:
        modelos_unicos_g = sorted(list(set([a['modelo'] for a in arquivos_disponiveis if a['modelo'] != 'N/D'])))
        operacoes_unicas_g = sorted(list(set([a['operacao'] for a in arquivos_disponiveis if a['operacao'] != 'N/D'])))

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            sel_modelo_g = st.selectbox("Modelo", ["Selecione"] + modelos_unicos_g, key="modelo_grafico")
        with col_g2:
            sel_op_g = st.selectbox("Operação (OP)", ["Selecione"] + operacoes_unicas_g, key="operacao_grafico")
        with col_g3:
            datas_unicas = []
            if sel_modelo_g != "Selecione" and sel_op_g != "Selecione":
                datas_unicas = sorted(list(set([
                    a['data_f'] for a in arquivos_disponiveis if a['modelo'] == sel_modelo_g and a['operacao'] == sel_op_g
                ])), reverse=True)

            sel_data_g = st.selectbox("Data", ["Selecione"] + datas_unicas, key="data_grafico")

        if sel_modelo_g != "Selecione" and sel_op_g != "Selecione" and sel_data_g != "Selecione":
            # Encontra o arquivo correspondente aos filtros
            arquivo_para_grafico = next((a for a in arquivos_disponiveis if a['modelo'] == sel_modelo_g and a['operacao'] == sel_op_g and a['data_f'] == sel_data_g), None)

            if arquivo_para_grafico:
                df_grafico = carregar_csv(arquivo_para_grafico['caminho'])
                if not df_grafico.empty:
                    # Concatena Date e Time para criar um índice de tempo antes de identificar numéricas
                    df_grafico['DateTime'] = pd.to_datetime(df_grafico['Date'] + ' ' + df_grafico['Time'], errors='coerce')
                    df_grafico = df_grafico.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
                    df_grafico = df_grafico.sort_values('DateTime')

                    # Identifica colunas numéricas para o gráfico
                    numeric_cols_for_plot = [col for col in df_grafico.columns if pd.api.types.is_numeric_dtype(df_grafico[col]) and col not in ["Date", "Time"]]

                    if numeric_cols_for_plot:
                        variaveis_selecionadas = st.multiselect(
                            "Selecione as variáveis para o gráfico",
                            options=numeric_cols_for_plot,
                            default=numeric_cols_for_plot[:2] if len(numeric_cols_for_plot) >= 2 else numeric_cols_for_plot # Seleciona as duas primeiras por padrão
                        )

                        if variaveis_selecionadas:
                            fig = px.line(
                                df_grafico,
                                x="DateTime",
                                y=variaveis_selecionadas,
                                title=f"Gráfico de Variáveis para {arquivo_para_grafico['modelo']} - {arquivo_para_grafico['operacao']} em {arquivo_para_grafico['data_f']}",
                                labels={"DateTime": "Data e Hora", "value": "Valor"},
                                hovermode="x unified",
                                legend_title="Variáveis",
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            st.markdown(
                                "- Use o botão de **fullscreen** no gráfico (canto superior direito do gráfico) para tela cheia.\n"
                                "- Use o ícone de **câmera** para baixar como imagem (PNG).\n"
                                "- A imagem pode ser enviada por WhatsApp, e-mail, etc., em PC ou celular."
                            )
                        else:
                            st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                    else:
                        st.info("Nenhuma variável numérica encontrada para gerar gráficos neste histórico.")
                else:
                    st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados ou dados inválidos.")
            else:
                st.info("Selecione um Modelo, Operação e Data para gerar o gráfico.")
        else:
            st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados.")