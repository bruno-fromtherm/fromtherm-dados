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

        # Adaptação para nomes de arquivo com 5 ou 6 partes
        # Ex: L1_20240307_1234_OP123_MOD1.csv (6 partes)
        # Ex: L1_20240307_TESTE_NOVO.csv (4 partes, precisa de tratamento)
        # Ex: L1_20240307_1234_OP123.csv (5 partes)

        data_str = None
        hora_str = "0000" # Default
        operacao = "N/D" # Default
        modelo = "N/D" # Default

        if len(parts) >= 2: # Pelo menos L1_20240307
            data_str = parts[1]

        if len(parts) >= 3: # L1_20240307_1234
            # Tenta interpretar a terceira parte como hora
            if re.fullmatch(r'\d{4}', parts[2]): # Verifica se são 4 dígitos (hora)
                hora_str = parts[2]
            else: # Se não for hora, pode ser a operação ou modelo
                operacao = parts[2]

        if len(parts) >= 4: # L1_20240307_1234_OP123 ou L1_20240307_OP123_MOD1
            if re.fullmatch(r'\d{4}', parts[2]): # Se parts[2] era hora
                operacao = parts[3]
            else: # Se parts[2] era operação, parts[3] pode ser modelo
                modelo = parts[3]

        if len(parts) >= 5: # L1_20240307_1234_OP123_MOD1
            if re.fullmatch(r'\d{4}', parts[2]): # Se parts[2] era hora
                modelo = parts[4]
            # else: já tratado acima

        # Tenta converter a data
        dt = None
        try:
            if data_str:
                dt = datetime.strptime(data_str, "%Y%m%d").date()
        except ValueError:
            st.warning(f"Nome de arquivo CSV inválido: {n}. Não foi possível extrair a data. Ignorando.")
            continue # Pula este arquivo se a data for inválida

        if dt:
            lista.append({
                "nome": n, "caminho": c, "data": dt,
                "ano": str(dt.year), "mes": dt.strftime("%m"),
                "data_f": dt.strftime("%d/%m/%Y"), 
                "hora": f"{hora_str[:2]}:{hora_str[2:]}",
                "operacao": operacao, "modelo": modelo
            })
        else:
            st.warning(f"Nome de arquivo CSV inválido: {n}. Não foi possível extrair informações suficientes. Ignorando.")

    return sorted(lista, key=lambda x: (x['data'], x['hora']), reverse=True)

@st.cache_data(ttl=5)
def carregar_csv(caminho_arquivo):
    try:
        # Tenta ler com separador '|' e pula a segunda linha (---)
        df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], skipinitialspace=True)

        # Remove espaços em branco dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Remove a primeira coluna vazia se existir (resultado do pipe inicial)
        if df.columns[0] == '':
            df = df.iloc[:, 1:]
            df.columns = df.columns.str.strip() # Re-strip após remover coluna

        # Remove a última coluna vazia se existir (resultado do pipe final)
        if df.columns[-1] == '':
            df = df.iloc[:, :-1]
            df.columns = df.columns.str.strip() # Re-strip após remover coluna

        # Converte colunas numéricas, tratando erros
        for col in ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

def criar_pdf(df, info_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para cabeçalhos de tabela
    styles.add(ParagraphStyle(name='TableHeader', fontSize=10, alignment=1, fontName='Helvetica-Bold'))
    # Estilo para células de tabela
    styles.add(ParagraphStyle(name='TableCell', fontSize=9, alignment=1, fontName='Helvetica'))

    elements = []

    # Título
    elements.append(Paragraph(f"Relatório de Histórico - Máquina de Teste Fromtherm", styles['h1']))
    elements.append(Spacer(1, 0.2 * cm)) # Usando cm em vez de inch

    # Informações do arquivo
    elements.append(Paragraph(f"<b>Modelo:</b> {info_arquivo['modelo']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Operação:</b> {info_arquivo['operacao']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Data:</b> {info_arquivo['data_f']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Hora:</b> {info_arquivo['hora']}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))

    # Preparar dados para a tabela
    # Converter todas as colunas para string para evitar problemas de formatação no PDF
    data_for_table = [df.columns.tolist()] + df.astype(str).values.tolist()

    table = Table(data_for_table)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def criar_excel(df, info_arquivo):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados Históricos')
        workbook = writer.book
        worksheet = writer.sheets['Dados Históricos']

        # Ajustar largura das colunas
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Layout do Streamlit
# -------------------------------------------------

# st.sidebar.image("https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png", use_container_width=True) # <-- LINHA DA LOGO COMENTADA
st.sidebar.title("Filtros de Busca")

# Carrega todos os arquivos disponíveis
arquivos_disponiveis = buscar_arquivos()

# Extrai opções únicas para os filtros
modelos_unicos = sorted(list(set([a['modelo'] for a in arquivos_disponiveis if a['modelo'] != 'N/D'])))
operacoes_unicas = sorted(list(set([a['operacao'] for a in arquivos_disponiveis if a['operacao'] != 'N/D'])))
anos_unicos = sorted(list(set([a['ano'] for a in arquivos_disponiveis])), reverse=True)
meses_unicos = sorted(list(set([a['mes'] for a in arquivos_disponiveis])), reverse=True)

# Filtros na barra lateral
sel_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
sel_operacao = st.sidebar.selectbox("Operação (OP)", ["Todas"] + operacoes_unicas)
sel_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
sel_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos)

# Aplica os filtros
arquivos_filtrados = arquivos_disponiveis
if sel_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == sel_modelo]
if sel_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == sel_operacao]
if sel_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == sel_ano]
if sel_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == sel_mes]

# Título principal
st.markdown('<div class="main-header">Monitoramento de Máquinas Fromtherm</div>', unsafe_allow_html=True)

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Última Leitura Registrada")

    if arquivos_filtrados:
        ultimo_arquivo = arquivos_filtrados[0]
        df_ultimo = carregar_csv(ultimo_arquivo['caminho'])

        if not df_ultimo.empty:
            ultima_linha = df_ultimo.iloc[-1] # Pega a última linha para a última leitura

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mostra_valor("T-Ambiente", f"{ultima_linha.get('ambiente', 'N/D'):.2f}" if pd.notna(ultima_linha.get('ambiente')) else "N/D", "°C", '<i class="bi bi-thermometer-half"></i>')
            with col2:
                mostra_valor("T-Entrada", f"{ultima_linha.get('entrada', 'N/D'):.2f}" if pd.notna(ultima_linha.get('entrada')) else "N/D", "°C", '<i class="bi bi-arrow-down-circle"></i>')
            with col3:
                mostra_valor("T-Saída", f"{ultima_linha.get('saida', 'N/D'):.2f}" if pd.notna(ultima_linha.get('saida')) else "N/D", "°C", '<i class="bi bi-arrow-up-circle"></i>')
            with col4:
                mostra_valor("ΔT", f"{ultima_linha.get('dif', 'N/D'):.2f}" if pd.notna(ultima_linha.get('dif')) else "N/D", "°C", '<i class="bi bi-arrows-expand"></i>')

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                mostra_valor("Tensão", f"{ultima_linha.get('tensao', 'N/D'):.1f}" if pd.notna(ultima_linha.get('tensao')) else "N/D", "V", '<i class="bi bi-lightning-charge"></i>')
            with col6:
                mostra_valor("Corrente", f"{ultima_linha.get('corrente', 'N/D'):.1f}" if pd.notna(ultima_linha.get('corrente')) else "N/D", "A", '<i class="bi bi-lightning"></i>')
            with col7:
                mostra_valor("Vazão", f"{ultima_linha.get('vazao', 'N/D'):.0f}" if pd.notna(ultima_linha.get('vazao')) else "N/D", "L/min", '<i class="bi bi-water"></i>')
            with col8:
                mostra_valor("COP", f"{ultima_linha.get('cop', 'N/D'):.1f}" if pd.notna(ultima_linha.get('cop')) else "N/D", "", '<i class="bi bi-graph-up-arrow"></i>')

        else:
            st.warning(f"Erro ao carregar ou processar o CSV '{ultimo_arquivo['nome']}'. Verifique o formato do arquivo.")
            st.info("Os cards de última leitura não podem ser exibidos devido a um problema no arquivo CSV.")
            col1, col2, col3, col4 = st.columns(4)
            with col1: mostra_valor("T-Ambiente", "N/D", "°C", '<i class="bi bi-thermometer-half"></i>')
            with col2: mostra_valor("T-Entrada", "N/D", "°C", '<i class="bi bi-arrow-down-circle"></i>')
            with col3: mostra_valor("T-Saída", "N/D", "°C", '<i class="bi bi-arrow-up-circle"></i>')
            with col4: mostra_valor("ΔT", "N/D", "°C", '<i class="bi bi-arrows-expand"></i>')
            col5, col6, col7, col8 = st.columns(4)
            with col5: mostra_valor("Tensão", "N/D", "V", '<i class="bi bi-lightning-charge"></i>')
            with col6: mostra_valor("Corrente", "N/D", "A", '<i class="bi bi-lightning"></i>')
            with col7: mostra_valor("Vazão", "N/D", "L/min", '<i class="bi bi-water"></i>')
            with col8: mostra_valor("COP", "N/D", "", '<i class="bi bi-graph-up-arrow"></i>')
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")
        col1, col2, col3, col4 = st.columns(4)
        with col1: mostra_valor("T-Ambiente", "N/D", "°C", '<i class="bi bi-thermometer-half"></i>')
        with col2: mostra_valor("T-Entrada", "N/D", "°C", '<i class="bi bi-arrow-down-circle"></i>')
        with col3: mostra_valor("T-Saída", "N/D", "°C", '<i class="bi bi-arrow-up-circle"></i>')
        with col4: mostra_valor("ΔT", "N/D", "°C", '<i class="bi bi-arrows-expand"></i>')
        col5, col6, col7, col8 = st.columns(4)
        with col5: mostra_valor("Tensão", "N/D", "V", '<i class="bi bi-lightning-charge"></i>')
        with col6: mostra_valor("Corrente", "N/D", "A", '<i class="bi bi-lightning"></i>')
        with col7: mostra_valor("Vazão", "N/D", "L/min", '<i class="bi bi-water"></i>')
        with col8: mostra_valor("COP", "N/D", "", '<i class="bi bi-graph-up-arrow"></i>')

    st.subheader("Históricos Disponíveis")

    if arquivos_filtrados:
        for arquivo in arquivos_filtrados:
            with st.expander(f"**{arquivo['modelo']}** - **{arquivo['operacao']}** - {arquivo['data_f']} {arquivo['hora']} ({arquivo['nome']})"):
                df_exibir = carregar_csv(arquivo['caminho'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        pdf_buffer = criar_pdf(df_exibir, arquivo)
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer,
                            file_name=f"Historico_{arquivo['modelo']}_{arquivo['operacao']}_{arquivo['data_f'].replace('/', '-')}_{arquivo['hora'].replace(':', '')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with col_dl2:
                        excel_buffer = criar_excel(df_exibir, arquivo)
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_buffer,
                            file_name=f"Historico_{arquivo['modelo']}_{arquivo['operacao']}_{arquivo['data_f'].replace('/', '-')}_{arquivo['hora'].replace(':', '')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível exibir o conteúdo de '{arquivo['nome']}'. Verifique o arquivo.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico Personalizado")

    if arquivos_disponiveis:
        # Filtros para o gráfico
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