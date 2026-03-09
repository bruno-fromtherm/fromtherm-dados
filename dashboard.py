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
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=5)
def buscar_arquivos():
    if not os.path.exists(DADOS_DIR):
        st.error(f"Diretório de dados não encontrado: {DADOS_DIR}")
        return []

    caminhos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    lista = []
    for c in caminhos:
        n = os.path.basename(c)
        parts = n.replace(".csv", "").split("_")

        # O nome do arquivo deve ter pelo menos 6 partes: L1_YYYYMMDD_HHMM_OPERACAO_MODELO
        if len(parts) >= 5: # Ajustado para 5 partes, pois o exemplo 'historico_L1_20260308_0939_OP987_FTA987BR.csv' tem 5 partes após o split
            try:
                # O formato do nome do arquivo é L1_YYYYMMDD_HHMM_OPERACAO_MODELO
                # parts[0] = "historico" ou "L1"
                # parts[1] = "L1" ou "20260308"
                # parts[2] = "20260308" ou "0939"
                # parts[3] = "0939" ou "OP987"
                # parts[4] = "OP987" ou "FTA987BR"

                # Vamos tentar uma lógica mais robusta para extrair a data e hora
                # Assumindo que a data está sempre na 3ª ou 2ª posição e a hora na 4ª ou 3ª

                dt_str = ""
                time_str = ""
                operacao = ""
                modelo = ""

                # Tenta encontrar a data (8 dígitos numéricos)
                for i in range(len(parts)):
                    if re.fullmatch(r'\d{8}', parts[i]):
                        dt_str = parts[i]
                        # Tenta encontrar a hora (4 dígitos numéricos) logo depois da data
                        if i + 1 < len(parts) and re.fullmatch(r'\d{4}', parts[i+1]):
                            time_str = parts[i+1]
                            # As próximas duas partes seriam operação e modelo
                            if i + 2 < len(parts): operacao = parts[i+2]
                            if i + 3 < len(parts): modelo = parts[i+3]
                        break # Encontrou a data, tenta processar o resto

                if not dt_str: # Se não encontrou a data, tenta outro padrão
                    # Ex: historico_L1_20260307_TESTE_NOVO.csv (data na 3a posição)
                    if len(parts) >= 3 and re.fullmatch(r'\d{8}', parts[2]):
                        dt_str = parts[2]
                        if len(parts) >= 4: time_str = parts[3] # Hora pode ser a 4a parte
                        if len(parts) >= 5: operacao = parts[4] # Operação pode ser a 5a parte
                        if len(parts) >= 6: modelo = parts[5] # Modelo pode ser a 6a parte

                if not dt_str: # Última tentativa, se o nome for muito simples
                    if len(parts) >= 2 and re.fullmatch(r'\d{8}', parts[1]):
                        dt_str = parts[1]
                        if len(parts) >= 3: time_str = parts[2]
                        if len(parts) >= 4: operacao = parts[3]
                        if len(parts) >= 5: modelo = parts[4]

                if dt_str:
                    dt_obj = datetime.strptime(dt_str, "%Y%m%d").date()
                    lista.append({
                        "nome": n, "caminho": c, "data": dt_obj,
                        "ano": str(dt_obj.year), "mes": dt_obj.strftime("%m"),
                        "data_f": dt_obj.strftime("%d/%m/%Y"),
                        "hora": f"{time_str[:2]}:{time_str[2:]}" if time_str and len(time_str) == 4 else "N/D",
                        "operacao": operacao if operacao else "N/D",
                        "modelo": modelo if modelo else "N/D"
                    })
                else:
                    st.warning(f"Nome de arquivo CSV inválido ou formato inesperado: {n}. Ignorando.")

            except Exception as e:
                st.warning(f"Erro ao processar nome de arquivo {n}: {e}. Ignorando.")
                continue
    return sorted(lista, key=lambda x: (x['data'], x['hora']), reverse=True)


def carregar_csv(caminho):
    try:
        # Tenta ler com separador '|' e ignora espaços em branco
        df = pd.read_csv(caminho, sep='|', skipinitialspace=True)

        # Remove colunas vazias que podem surgir do separador '|' no início/fim da linha
        df = df.dropna(axis=1, how='all')

        # Remove espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Verifica se a primeira coluna é um índice ou está vazia e remove se for o caso
        if df.columns[0] == '':
            df = df.iloc[:, 1:]
            df.columns = df.columns.str.strip() # Re-strip após remover a coluna

        # Renomeia as colunas para o padrão esperado, se necessário
        # Mapeamento de nomes de colunas do CSV para os nomes internos do código
        col_mapping = {
            "Date": "Date", "Time": "Time", "ambiente": "Ambiente",
            "entrada": "Entrada", "saida": "Saída", "dif": "ΔT",
            "tensao": "Tensão", "corrente": "Corrente", "kacl/h": "kcal/h",
            "vazao": "Vazão", "kw aquecimento": "kW Aquecimento",
            "kw consumo": "kW Consumo", "cop": "COP"
        }
        # Aplica o mapeamento, mantendo as colunas que não estão no mapeamento
        df = df.rename(columns=col_mapping)

        # Converte colunas numéricas para o tipo correto, tratando erros
        numeric_cols = ["Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]
        for col in numeric_cols:
            if col in df.columns:
                # Converte para numérico, tratando vírgulas como decimais e forçando erros para NaN
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Preenche NaN com 0 para evitar problemas de cálculo ou exibição, ou pode ser 'N/D' se preferir
                df[col] = df[col].fillna(0) # Ou df[col].fillna('N/D') se quiser manter como string para N/D

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho)}': {e}")
        return pd.DataFrame()


# 4. BARRA LATERAL (SIDEBAR) - SEQUÊNCIA SOLICITADA
arquivos_lista = buscar_arquivos()

with st.sidebar:
    # Logo via URL (Evita erro de arquivo inexistente)
    # Bruno, você pediu para não incluir a logo. Esta linha está comentada para remover a logo.
    # Se quiser reativar, descomente a linha abaixo e remova o '#'
    # st.image("https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png", use_container_width=True)
    st.markdown("---")
    st.subheader("FILTROS DE BUSCA")

    # Extrai valores únicos para os filtros
    modelos_unicos = sorted(list({a['modelo'] for a in arquivos_lista if a['modelo'] != 'N/D'}))
    operacoes_unicas = sorted(list({a['operacao'] for a in arquivos_lista if a['operacao'] != 'N/D'}))
    anos_unicos = sorted(list({a['ano'] for a in arquivos_lista}), reverse=True)
    meses_unicos = sorted(list({a['mes'] for a in arquivos_lista}), reverse=True)
    datas_unicas = sorted(list({a['data_f'] for a in arquivos_lista}), reverse=True)

    sel_modelo = st.selectbox("📦 Modelo", ["Todos"] + modelos_unicos)
    sel_op = st.selectbox("🔢 Operação", ["Todos"] + operacoes_unicas)
    sel_ano = st.selectbox("📅 Ano", ["Todos"] + anos_unicos)
    sel_mes = st.selectbox("🗓️ Mês", ["Todos"] + meses_unicos)
    sel_data = st.selectbox("📆 Data Específica", ["Todos"] + datas_unicas)

    st.markdown("---")
    st.markdown("Desenvolvido por **Inner AI**")

# 5. FILTRAGEM DOS ARQUIVOS
arquivos_filtrados = arquivos_lista
if sel_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == sel_modelo]
if sel_op != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == sel_op]
if sel_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == sel_ano]
if sel_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == sel_mes]
if sel_data != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == sel_data]

# 6. LAYOUT PRINCIPAL
st.markdown('<div class="main-header">Monitoramento de Máquinas Fromtherm</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Última Leitura Registrada")

    if arquivos_filtrados:
        ultimo_arquivo = arquivos_filtrados[0]
        df_ultimo = carregar_csv(ultimo_arquivo['caminho'])

        if not df_ultimo.empty:
            ultima_linha = df_ultimo.iloc[-1]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mostra_valor("T-Ambiente", f"{ultima_linha.get('Ambiente', 'N/D'):.2f}" if isinstance(ultima_linha.get('Ambiente'), (int, float)) else "N/D", "°C", "🌡️")
            with col2:
                mostra_valor("T-Entrada", f"{ultima_linha.get('Entrada', 'N/D'):.2f}" if isinstance(ultima_linha.get('Entrada'), (int, float)) else "N/D", "°C", "➡️")
            with col3:
                mostra_valor("T-Saída", f"{ultima_linha.get('Saída', 'N/D'):.2f}" if isinstance(ultima_linha.get('Saída'), (int, float)) else "N/D", "°C", "⬅️")
            with col4:
                mostra_valor("ΔT", f"{ultima_linha.get('ΔT', 'N/D'):.2f}" if isinstance(ultima_linha.get('ΔT'), (int, float)) else "N/D", "°C", "🔥")

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                mostra_valor("Tensão", f"{ultima_linha.get('Tensão', 'N/D'):.2f}" if isinstance(ultima_linha.get('Tensão'), (int, float)) else "N/D", "V", "⚡")
            with col6:
                mostra_valor("Corrente", f"{ultima_linha.get('Corrente', 'N/D'):.2f}" if isinstance(ultima_linha.get('Corrente'), (int, float)) else "N/D", "A", "🔌")
            with col7:
                mostra_valor("Vazão", f"{ultima_linha.get('Vazão', 'N/D'):.2f}" if isinstance(ultima_linha.get('Vazão'), (int, float)) else "N/D", "L/min", "💧")
            with col8:
                mostra_valor("COP", f"{ultima_linha.get('COP', 'N/D'):.2f}" if isinstance(ultima_linha.get('COP'), (int, float)) else "N/D", "", "📈")
        else:
            st.warning(f"Não foi possível carregar dados do último histórico: {ultimo_arquivo['nome']}. Verifique o formato do arquivo.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

    st.markdown("---")
    st.subheader("Históricos Disponíveis")

    if arquivos_filtrados:
        for arquivo in arquivos_filtrados:
            with st.expander(f"**{arquivo['data_f']} - {arquivo['hora']}** | Modelo: {arquivo['modelo']} | Operação: {arquivo['operacao']}"):
                df_exibir = carregar_csv(arquivo['caminho'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    # Botões de Download
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Download PDF
                        pdf_buffer = BytesIO()
                        criar_pdf(df_exibir, pdf_buffer, arquivo['nome'])
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{arquivo['nome'].replace('.csv', '')}.pdf",
                            mime="application/pdf",
                            key=f"pdf_{arquivo['nome']}"
                        )
                    with col_dl2:
                        # Download Excel
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            df_exibir.to_excel(writer, index=False, sheet_name='Dados')
                        st.download_button(
                            label="Baixar Excel",
                            data=excel_buffer.getvalue(),
                            file_name=f"{arquivo['nome'].replace('.csv', '')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"excel_{arquivo['nome']}"
                        )
                else:
                    st.warning(f"Não foi possível carregar dados para {arquivo['nome']}.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico Personalizado")

    if arquivos_filtrados:
        # Filtros para o gráfico
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            sel_modelo_g = st.selectbox("Modelo", ["Selecione"] + modelos_unicos, key="modelo_grafico")
        with col_g2:
            sel_op_g = st.selectbox("Operação (OP)", ["Selecione"] + operacoes_unicas, key="operacao_grafico")
        with col_g3:
            sel_data_g = st.selectbox("Data", ["Selecione"] + datas_unicas, key="data_grafico")

        if sel_modelo_g != "Selecione" and sel_op_g != "Selecione" and sel_data_g != "Selecione":
            # Encontra o arquivo correspondente aos filtros
            arquivo_para_grafico = next((a for a in arquivos_filtrados if a['modelo'] == sel_modelo_g and a['operacao'] == sel_op_g and a['data_f'] == sel_data_g), None)

            if arquivo_para_grafico:
                df_grafico = carregar_csv(arquivo_para_grafico['caminho'])
                if not df_grafico.empty:
                    # Identifica colunas numéricas para o gráfico
                    numeric_cols_for_plot = [col for col in df_grafico.columns if pd.api.types.is_numeric_dtype(df_grafico[col]) and col not in ["Date", "Time"]]

                    if numeric_cols_for_plot:
                        variaveis_selecionadas = st.multiselect(
                            "Selecione as variáveis para o gráfico",
                            options=numeric_cols_for_plot,
                            default=numeric_cols_for_plot[:2] # Seleciona as duas primeiras por padrão
                        )

                        if variaveis_selecionadas:
                            # Concatena Date e Time para criar um índice de tempo
                            df_grafico['DateTime'] = pd.to_datetime(df_grafico['Date'] + ' ' + df_grafico['Time'], errors='coerce')
                            df_grafico = df_grafico.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
                            df_grafico = df_grafico.sort_values('DateTime')

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