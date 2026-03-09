import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheets, ParagraphStyle
from reportlab.lib import colors

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
    .ft-value { font-size: 20px; font-weight: 800; color: #003366; margin-top: 5px; }

    /* Cores dos Ícones (se necessário, mas o código usa bi- para Bootstrap Icons) */
    .azul { color: #007bff; }
    .vermelho { color: #dc3545; }
    .ouro { color: #ffc107; }
    .verde { color: #28a745; }

    /* Ajuste para Celulares */
    @media (max-width: 768px) {
        .ft-value { font-size: 16px; }
        .main-header { font-size: 20px; }
        .ft-icon { font-size: 30px; }
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. FUNÇÕES AUXILIARES
# -------------------------------------------------

# Função para exibir cards
def mostra_valor(label, value, unit, icon_class): # icon_class é agora apenas a classe do ícone
    st.markdown(f"""
        <div class="ft-card">
            <span class="ft-icon"><i class="{icon_class}"></i></span>
            <div class="ft-content">
                <div class="ft-label">{label}</div>
                <div class="ft-value">{value} {unit}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 3.1. CONFIGURAÇÃO DE DADOS E LEITURA DE ARQUIVOS
# Caminho para a pasta de dados (ajustado para o ambiente do Streamlit Cloud)
# O Streamlit Cloud monta o repositório na raiz, então o caminho é relativo a ela.
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=3600) # Cache por 1 hora
def buscar_arquivos():
    """
    Busca arquivos CSV na DATA_PATH e extrai metadados de seus nomes.
    Retorna uma lista de dicionários com os metadados.
    """
    if not os.path.exists(DATA_PATH):
        st.error(f"O caminho de dados configurado não existe: '{DATA_PATH}'")
        return []

    arquivos_encontrados = glob.glob(os.path.join(DATA_PATH, "*.csv"))
    todos_arquivos = []

    # Regex ultra-robusto para capturar data, hora, operação e modelo
    # Ele tenta ser o mais flexível possível para a operação e o modelo
    # Ex: historico_L1_YYYYMMDD_HHMM_OPX_MODELO.csv
    # Ou: historico_L1_YYYYMMDD_HHMM_OPEY_MODELO.csv
    # Ou: historico_L1_YYYYMMDD_HHMM_MODELO.csv (se OP/OPE for opcional)
    # Ou: historico_L1_YYYYMMDD_HHMM_OPX.csv (se MODELO for opcional)
    # Vamos focar no padrão mais comum e ser flexíveis.
    # Padrão: historico_L1_YYYYMMDD_HHMM_OP/OPE[0-9A-Z]+_MODELO[0-9A-Z_]+.csv
    # Ou: historico_L1_YYYYMMDD_HHMM_OP/OPE[0-9A-Z]+.csv
    # Ou: historico_L1_YYYYMMDD_HHMM_MODELO[0-9A-Z_]+.csv
    # O mais seguro é capturar o que está entre HHMM e .csv como uma "identificação" e depois tentar parsear.
    # Vamos simplificar e capturar o que está entre HHMM e .csv como um grupo, e depois tentar dividir.

    # Novo regex mais flexível:
    # Captura YYYYMMDD, HHMM, e o resto antes do .csv como 'identificador'
    # O identificador pode conter OP/OPE, números, letras, underscores.
    regex_padrao = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})_([a-zA-Z0-9_.-]+)\.csv")

    for arquivo_path in arquivos_encontrados:
        nome_arquivo = os.path.basename(arquivo_path)
        match = regex_padrao.match(nome_arquivo)

        if match:
            ano, mes, dia, hora, minuto, identificador = match.groups()
            data_str = f"{dia}/{mes}/{ano}"
            hora_str = f"{hora}:{minuto}"
            data_hora_obj = datetime.strptime(f"{ano}-{mes}-{dia} {hora}:{minuto}", "%Y-%m-%d %H:%M")

            operacao = "N/D"
            modelo = "N/D"

            # Tenta extrair Operação e Modelo do identificador
            op_match = re.search(r"(OP|OPE)([0-9A-Z]+)", identificador, re.IGNORECASE)
            if op_match:
                operacao = op_match.group(0).upper() # Ex: OP987, OPE779
                # Remove a operação do identificador para tentar encontrar o modelo
                identificador_sem_op = identificador.replace(op_match.group(0), "").strip('_')

            # O modelo é o que sobra, ou o identificador completo se não achou OP/OPE
            if identificador_sem_op:
                modelo = identificador_sem_op.upper()
            elif not op_match: # Se não achou OP/OPE, o identificador inteiro pode ser o modelo
                modelo = identificador.upper()

            # Limpeza final do modelo (remover possíveis sufixos indesejados)
            modelo = re.sub(r'(_BR|_L|_H|\.CSV)$', '', modelo, flags=re.IGNORECASE).strip('_-')
            if not modelo: # Se ficou vazio após a limpeza, volta para N/D
                modelo = "N/D"

            todos_arquivos.append({
                "path": arquivo_path,
                "nome_arquivo": nome_arquivo,
                "data_obj": data_hora_obj.date(),
                "hora_obj": data_hora_obj.time(),
                "datetime_obj": data_hora_obj,
                "data_f": data_str,
                "hora_f": hora_str,
                "ano": int(ano),
                "mes": int(mes),
                "operacao": operacao,
                "modelo": modelo
            })
        else:
            st.sidebar.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.")
            # st.warning(f"Nome de arquivo CSV inválido: {nome_arquivo}. Não segue o padrão esperado. Ignorando.") # Para debug na tela principal

    # Ordena os arquivos do mais recente para o mais antigo
    todos_arquivos.sort(key=lambda x: x['datetime_obj'], reverse=True)
    return todos_arquivos

@st.cache_data(ttl=3600) # Cache por 1 hora
def carregar_csv(caminho_arquivo):
    """
    Carrega um arquivo CSV, limpa os nomes das colunas e converte tipos.
    Lida com cabeçalhos problemáticos e separador '|'.
    """
    try:
        # Tenta ler o cabeçalho separadamente para identificar os nomes das colunas
        # e pular a linha de separação '---'
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            st.error(f"Arquivo CSV vazio: {caminho_arquivo}")
            return pd.DataFrame()

        # Encontra a linha do cabeçalho (primeira linha que não é '---')
        header_line_index = -1
        data_start_index = -1
        for i, line in enumerate(lines):
            if not line.strip().startswith('| ---'): # Ignora a linha de separação
                header_line_index = i
                break

        if header_line_index == -1:
            st.error(f"Não foi possível encontrar o cabeçalho no arquivo: {caminho_arquivo}")
            return pd.DataFrame()

        # Extrai os nomes das colunas da linha do cabeçalho
        # Remove os pipes iniciais/finais e divide por pipe
        header_raw = lines[header_line_index].strip().strip('|')
        column_names_raw = [col.strip().strip('"') for col in header_raw.split('|')]

        # Limpa e padroniza os nomes das colunas
        column_names = []
        for name in column_names_raw:
            cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '', name.lower().replace(' ', '_'))
            if cleaned_name: # Garante que não adiciona nomes vazios
                column_names.append(cleaned_name)
            else: # Se o nome ficou vazio, tenta um nome genérico ou ignora
                column_names.append(f"col_{len(column_names)}") # Fallback

        # Encontra a linha onde os dados começam (após o cabeçalho e a linha '---')
        data_start_index = header_line_index + 1
        while data_start_index < len(lines) and lines[data_start_index].strip().startswith('| ---'):
            data_start_index += 1

        if data_start_index >= len(lines):
            st.warning(f"Nenhum dado encontrado após o cabeçalho no arquivo: {caminho_arquivo}")
            return pd.DataFrame(columns=column_names) # Retorna DF vazio com colunas

        # Lê o restante do arquivo, pulando as linhas já processadas
        df = pd.read_csv(
            caminho_arquivo,
            sep='|',
            skiprows=data_start_index, # Pula o cabeçalho e a linha '---'
            header=None, # Não espera cabeçalho, pois já o processamos
            encoding='utf-8',
            engine='python' # 'python' engine é mais flexível para separadores
        )

        # Remove a primeira e última coluna se estiverem vazias (resíduo do separador '|')
        df = df.iloc[:, 1:-1] if df.shape[1] > 2 else df # Garante que não remove se só tiver 1 ou 2 colunas

        # Atribui os nomes das colunas limpos
        if len(column_names) == df.shape[1]:
            df.columns = column_names
        else:
            st.warning(f"Número de colunas no cabeçalho ({len(column_names)}) não corresponde ao número de colunas lidas ({df.shape[1]}) em {caminho_arquivo}. Usando nomes genéricos.")
            df.columns = [f"col_{i}" for i in range(df.shape[1])]


        # Converte 'Date' e 'Time' para datetime
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce', format='%Y/%m/%d %H:%M:%S')
            df = df.dropna(subset=['datetime']) # Remove linhas com datetime inválido
        else:
            st.warning(f"Colunas 'date' ou 'time' não encontradas em {caminho_arquivo}. Gráficos podem não funcionar corretamente.")
            df['datetime'] = pd.to_datetime(df.index, unit='s') # Fallback para índice

        # Converte colunas numéricas, tratando vírgulas e valores inválidos
        for col in df.columns:
            if col not in ['date', 'time', 'datetime']: # Ignora colunas de data/hora
                # Converte para string, substitui vírgula por ponto, remove espaços e tenta para numérico
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False).str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce') # 'coerce' transforma erros em NaN

        # Remove linhas onde todas as colunas numéricas são NaN (se houver)
        numeric_cols = df.select_dtypes(include=['number']).columns
        if not numeric_cols.empty:
            df = df.dropna(subset=numeric_cols, how='all')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame()

# -------------------------------------------------
# 4. LÓGICA PRINCIPAL DO DASHBOARD
# -------------------------------------------------

# Carrega todos os arquivos e metadados
todos_arquivos = buscar_arquivos()

# 4.1. SIDEBAR - FILTROS
with st.sidebar:
    st.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
    st.markdown("<h2 class='main-header-sidebar'>Filtros de Busca</h2>", unsafe_allow_html=True)

    # Garante que as listas de opções não estejam vazias
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D'])))
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D'])))
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos])), reverse=True)
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos])))
    datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos])), reverse=True)

    # Adiciona "Todos" como opção padrão
    selected_modelo = st.selectbox("Modelo", ["Todos"] + modelos_unicos)
    selected_operacao = st.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
    selected_ano = st.selectbox("Ano", ["Todos"] + anos_unicos)
    selected_mes = st.selectbox("Mês", ["Todos"] + meses_unicos, format_func=lambda x: datetime(1, x, 1).strftime('%B') if x != "Todos" else x)
    selected_data = st.selectbox("Data", ["Todos"] + datas_unicas)

# Filtra os arquivos com base nas seleções
arquivos_filtrados = todos_arquivos
if selected_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == selected_modelo]
if selected_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == selected_operacao]
if selected_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == selected_ano]
if selected_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == selected_mes]
if selected_data != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == selected_data]

# 4.2. ÁREA PRINCIPAL
st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Última Leitura Registrada")

    ultima_leitura_df = pd.DataFrame()
    if arquivos_filtrados:
        # Pega o arquivo mais recente entre os filtrados
        arquivo_mais_recente = arquivos_filtrados[0]
        df_recente = carregar_csv(arquivo_mais_recente['path'])
        if not df_recente.empty:
            ultima_leitura_df = df_recente.iloc[-1] # Pega a última linha do DF

    if not ultima_leitura_df.empty:
        # Exibe informações do teste
        st.markdown(f"""
            <div style="background-color: #e0f2f7; padding: 10px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #003366;">
                <p style="font-size: 16px; font-weight: bold; color: #003366;">Informações do Teste:</p>
                <ul style="list-style-type: none; padding: 0; margin: 0;">
                    <li><strong>Modelo:</strong> {arquivo_mais_recente.get('modelo', 'N/D')}</li>
                    <li><strong>Operação:</strong> {arquivo_mais_recente.get('operacao', 'N/D')}</li>
                    <li><strong>Data:</strong> {arquivo_mais_recente.get('data_f', 'N/D')}</li>
                    <li><strong>Hora:</strong> {arquivo_mais_recente.get('hora_f', 'N/D')}</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        with col1:
            mostra_valor("T-Ambiente", f"{ultima_leitura_df.get('ambiente', 'N/D'):.2f}" if pd.notna(ultima_leitura_df.get('ambiente')) else "N/D", "°C", "bi-thermometer-half")
        with col2:
            mostra_valor("T-Entrada", f"{ultima_leitura_df.get('entrada', 'N/D'):.2f}" if pd.notna(ultima_leitura_df.get('entrada')) else "N/D", "°C", "bi-arrow-down-circle")
        with col3:
            mostra_valor("T-Saída", f"{ultima_leitura_df.get('saida', 'N/D'):.2f}" if pd.notna(ultima_leitura_df.get('saida')) else "N/D", "°C", "bi-arrow-up-circle")
        with col4:
            mostra_valor("T-Dif", f"{ultima_leitura_df.get('dif', 'N/D'):.2f}" if pd.notna(ultima_leitura_df.get('dif')) else "N/D", "°C", "bi-arrow-left-right")
        with col5:
            mostra_valor("Tensão", f"{ultima_leitura_df.get('tensao', 'N/D'):.1f}" if pd.notna(ultima_leitura_df.get('tensao')) else "N/D", "V", "bi-lightning-charge")
        with col6:
            mostra_valor("Corrente", f"{ultima_leitura_df.get('corrente', 'N/D'):.1f}" if pd.notna(ultima_leitura_df.get('corrente')) else "N/D", "A", "bi-lightning")
        with col7:
            mostra_valor("Vazão", f"{ultima_leitura_df.get('vazao', 'N/D'):.0f}" if pd.notna(ultima_leitura_df.get('vazao')) else "N/D", "L/min", "bi-droplet-half")

        # Linha adicional para kacl/h, kw aquecimento, kw consumo, cop
        col8, col9, col10, col11 = st.columns(4)
        with col8:
            mostra_valor("Kcal/h", f"{ultima_leitura_df.get('kacl_h', 'N/D'):.1f}" if pd.notna(ultima_leitura_df.get('kacl_h')) else "N/D", "", "bi-fire")
        with col9:
            mostra_valor("KW Aquecimento", f"{ultima_leitura_df.get('kw_aquecimento', 'N/D'):.1f}" if pd.notna(ultima_leitura_df.get('kw_aquecimento')) else "N/D", "kW", "bi-thermometer-sun")
        with col10:
            mostra_valor("KW Consumo", f"{ultima_leitura_df.get('kw_consumo', 'N/D'):.1f}" if pd.notna(ultima_leitura_df.get('kw_consumo')) else "N/D", "kW", "bi-power")
        with col11:
            mostra_valor("COP", f"{ultima_leitura_df.get('cop', 'N/D'):.1f}" if pd.notna(ultima_leitura_df.get('cop')) else "N/D", "", "bi-clipboard-data")

    else:
        st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")

    st.subheader("Históricos Disponíveis")

    if arquivos_filtrados:
        for arquivo_info in arquivos_filtrados:
            expander_label = f"**{arquivo_info['modelo']}** - Operação: **{arquivo_info['operacao']}** - Data: {arquivo_info['data_f']} {arquivo_info['hora_f']}"
            with st.expander(expander_label):
                df_historico = carregar_csv(arquivo_info['path'])
                if not df_historico.empty:
                    st.dataframe(df_historico, use_container_width=True)

                    # Botões de download
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Gerar PDF
                        pdf_buffer = BytesIO()
                        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                        styles = getSampleStyleSheets()

                        # Estilo para o título
                        title_style = ParagraphStyle(
                            'TitleStyle',
                            parent=styles['h1'],
                            fontSize=16,
                            alignment=1, # Center
                            spaceAfter=12,
                            textColor=colors.HexColor('#003366')
                        )
                        # Estilo para informações do teste
                        info_style = ParagraphStyle(
                            'InfoStyle',
                            parent=styles['Normal'],
                            fontSize=10,
                            spaceAfter=6,
                            textColor=colors.black
                        )
                        # Estilo para o cabeçalho da tabela
                        table_header_style = ParagraphStyle(
                            'TableHeaderStyle',
                            parent=styles['Normal'],
                            fontSize=8,
                            alignment=1, # Center
                            textColor=colors.white,
                            fontName='Helvetica-Bold'
                        )
                        # Estilo para o conteúdo da tabela
                        table_content_style = ParagraphStyle(
                            'TableContentStyle',
                            parent=styles['Normal'],
                            fontSize=7,
                            alignment=1, # Center
                            textColor=colors.black
                        )

                        elements = []
                        elements.append(Paragraph("Relatório de Teste de Máquina Fromtherm", title_style))
                        elements.append(Spacer(1, 0.2 * cm))
                        elements.append(Paragraph(f"<b>Modelo:</b> {arquivo_info.get('modelo', 'N/D')}", info_style))
                        elements.append(Paragraph(f"<b>Operação:</b> {arquivo_info.get('operacao', 'N/D')}", info_style))
                        elements.append(Paragraph(f"<b>Data:</b> {arquivo_info.get('data_f', 'N/D')}", info_style))
                        elements.append(Paragraph(f"<b>Hora:</b> {arquivo_info.get('hora_f', 'N/D')}", info_style))
                        elements.append(Spacer(1, 0.5 * cm))

                        # Preparar dados para a tabela
                        data = [
                            [Paragraph(col.replace('_', ' ').title(), table_header_style) for col in df_historico.columns]
                        ]
                        for _, row in df_historico.iterrows():
                            data.append([Paragraph(str(row[col]), table_content_style) for col in df_historico.columns])

                        table = Table(data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('FONTSIZE', (0, 1), (-1, -1), 7),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        elements.append(table)
                        doc.build(pdf_buffer)
                        pdf_buffer.seek(0)

                        pdf_filename = f"Maquina_{arquivo_info.get('modelo', 'N_D')}_OP{arquivo_info.get('operacao', 'N_D')}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora_f'].replace(':', '')}hs.pdf"
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with col_dl2:
                        # Gerar Excel
                        excel_buffer = BytesIO()
                        df_historico.to_excel(excel_buffer, index=False, sheet_name='Dados')
                        excel_buffer.seek(0)
                        excel_filename = f"Maquina_{arquivo_info.get('modelo', 'N_D')}_OP{arquivo_info.get('operacao', 'N_D')}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora_f'].replace(':', '')}hs.xlsx"
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_buffer,
                            file_name=excel_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para {arquivo_info['nome_arquivo']}.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico Personalizado")

    if arquivos_filtrados:
        # Filtros para o gráfico (pode ser diferente dos filtros da sidebar)
        # Usar apenas os arquivos filtrados para popular as opções
        modelos_grafico = sorted(list(set([a['modelo'] for a in arquivos_filtrados if a['modelo'] != 'N/D'])))
        operacoes_grafico = sorted(list(set([a['operacao'] for a in arquivos_filtrados if a['operacao'] != 'N/D'])))
        datas_grafico = sorted(list(set([a['data_f'] for a in arquivos_filtrados])), reverse=True)

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            selected_modelo_grafico = st.selectbox("Modelo do Gráfico", ["Selecione"] + modelos_grafico, key="model_graph")
        with col_g2:
            selected_operacao_grafico = st.selectbox("Operação do Gráfico", ["Selecione"] + operacoes_grafico, key="op_graph")
        with col_g3:
            selected_data_grafico = st.selectbox("Data do Gráfico", ["Selecione"] + datas_grafico, key="date_graph")

        arquivo_para_grafico = None
        if selected_modelo_grafico != "Selecione" and selected_operacao_grafico != "Selecione" and selected_data_grafico != "Selecione":
            for arquivo in arquivos_filtrados:
                if (arquivo['modelo'] == selected_modelo_grafico and
                    arquivo['operacao'] == selected_operacao_grafico and
                    arquivo['data_f'] == selected_data_grafico):
                    arquivo_para_grafico = arquivo
                    break

        if arquivo_para_grafico:
            df_grafico = carregar_csv(arquivo_para_grafico['path'])
            if not df_grafico.empty:
                # Identifica colunas numéricas para o gráfico
                colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()
                # Remove 'date' e 'time' se ainda estiverem lá e não forem numéricas
                colunas_numericas = [col for col in colunas_numericas if col not in ['date', 'time']]

                if colunas_numericas:
                    variaveis_selecionadas = st.multiselect(
                        "Selecione as variáveis para o gráfico",
                        options=colunas_numericas,
                        default=colunas_numericas[:3] # Seleciona as 3 primeiras por padrão
                    )

                    if variaveis_selecionadas:
                        # Criar o gráfico de linha interativo com Plotly
                        fig = px.line(
                            df_grafico,
                            x="datetime", # Usar 'datetime' que criamos
                            y=variaveis_selecionadas,
                            title=f"Gráfico de Variáveis para {arquivo_para_grafico['modelo']} - {arquivo_para_grafico['operacao']} em {arquivo_para_grafico['data_f']}",
                            labels={"datetime": "Data e Hora", "value": "Valor"},
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