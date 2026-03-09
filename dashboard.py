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
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    """, unsafe_allow_html=True)

# -------------------------------------------------
# 3. FUNÇÕES DE PROCESSAMENTO DE DADOS
# -------------------------------------------------

# Caminho base para os arquivos CSV
BASE_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data
def buscar_arquivos():
    """
    Busca arquivos CSV no diretório especificado e extrai metadados.
    Retorna uma lista de dicionários com path, nome, data, hora, operacao e modelo.
    """
    if not os.path.exists(BASE_PATH):
        st.error(f"O diretório base '{BASE_PATH}' não foi encontrado. Verifique a estrutura de pastas.")
        return []

    arquivos_encontrados = glob.glob(os.path.join(BASE_PATH, "*.csv"))
    lista_arquivos_meta = []

    # Regex ultra-robusto para capturar data, hora, operação e modelo
    # Suporta OP ou OPE, e modelos com letras/numeros/hifens
    # Ex: historico_L1_20260306_0718_OP999_FTI378L_BR.csv
    # Ex: historico_L1_20260307_1704_OPE779_FT55DBR.csv
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (fallback para N/D)
    # Ajustado para ser mais flexível com a parte final do nome do arquivo
    regex_padrao = re.compile(r'historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)?(\w+)_?([a-zA-Z0-9-]+)?_?BR\.csv')
    # Novo regex mais flexível para capturar o que for possível
    regex_flexivel = re.compile(r'historico_L1_(\d{8})_(\d{4})_?([a-zA-Z0-9]+)?_?([a-zA-Z0-9-]+)?_?BR\.csv')


    for file_path in arquivos_encontrados:
        file_name = os.path.basename(file_path)
        match = regex_padrao.match(file_name) # Tenta o padrão mais específico primeiro

        if match:
            ano, mes, dia, hora_str, op_prefix, operacao_part, modelo_part = match.groups()

            # Ajuste para operacao e modelo que podem ser None se o regex for muito flexível
            operacao = f"{op_prefix or ''}{operacao_part or ''}" if op_prefix or operacao_part else 'N/D'
            modelo = modelo_part if modelo_part else 'N/D'

            data_str = f"{dia}/{mes}/{ano}"
            hora_formatada = f"{hora_str[:2]}:{hora_str[2:]}:00" # HHMM -> HH:MM:SS

            try:
                data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
            except ValueError:
                data_obj = None # Caso a data não seja válida

            lista_arquivos_meta.append({
                'path': file_path,
                'nome': file_name,
                'data': data_obj,
                'data_str': data_str,
                'hora': hora_formatada,
                'ano': ano,
                'mes': mes,
                'dia': dia,
                'operacao': operacao,
                'modelo': modelo
            })
        else:
            # Fallback para arquivos que não seguem o padrão exato, usando o regex flexível
            match_flex = regex_flexivel.match(file_name)
            if match_flex:
                data_completa_str, hora_str, operacao_flex, modelo_flex = match_flex.groups()
                ano, mes, dia = data_completa_str[:4], data_completa_str[4:6], data_completa_str[6:8]
                data_str = f"{dia}/{mes}/{ano}"
                hora_formatada = f"{hora_str[:2]}:{hora_str[2:]}:00"

                try:
                    data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
                except ValueError:
                    data_obj = None

                lista_arquivos_meta.append({
                    'path': file_path,
                    'nome': file_name,
                    'data': data_obj,
                    'data_str': data_str,
                    'hora': hora_formatada,
                    'ano': ano,
                    'mes': mes,
                    'dia': dia,
                    'operacao': operacao_flex if operacao_flex else 'N/D',
                    'modelo': modelo_flex if modelo_flex else 'N/D'
                })
            else:
                st.warning(f"Nome de arquivo CSV inválido: {file_name}. Não segue o padrão esperado. Ignorando.")
                # Adiciona com N/D para que apareça na lista, mas com dados incompletos
                lista_arquivos_meta.append({
                    'path': file_path,
                    'nome': file_name,
                    'data': None,
                    'data_str': "N/D",
                    'hora': "N/D",
                    'ano': "N/D",
                    'mes': "N/D",
                    'dia': "N/D",
                    'operacao': 'N/D',
                    'modelo': 'N/D'
                })
    return sorted(lista_arquivos_meta, key=lambda x: (x['data'] if x['data'] else datetime.min.date(), x['hora']), reverse=True)


@st.cache_data
def carregar_csv(file_path):
    """
    Carrega um arquivo CSV, detecta o separador, limpa o cabeçalho e as colunas.
    """
    try:
        # Ler as primeiras linhas para detectar o separador e o cabeçalho
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Encontrar a linha do cabeçalho real (que não seja a linha de traços)
        header_line_index = -1
        for i, line in enumerate(lines):
            if not line.strip().startswith('|---'): # Ignora linhas de separação
                header_line_index = i
                break

        if header_line_index == -1:
            raise ValueError("Não foi possível encontrar uma linha de cabeçalho válida no CSV.")

        # Tentar inferir o separador (priorizando pipe)
        # Se a linha do cabeçalho contém vírgulas e aspas, mas o resto do arquivo usa pipe,
        # precisamos ler o cabeçalho de forma diferente.

        # Primeiro, tentar ler com pipe, pulando a linha de traços
        try:
            df = pd.read_csv(file_path, sep='|', skiprows=lambda x: lines[x].strip().startswith('|---'), encoding='utf-8', engine='python')
        except Exception:
            # Se falhar com pipe, tentar com vírgula (menos provável para o corpo do arquivo)
            df = pd.read_csv(file_path, sep=',', skiprows=lambda x: lines[x].strip().startswith('|---'), encoding='utf-8', engine='python')

        # Limpar nomes das colunas: remover espaços, aspas, etc.
        df.columns = [col.strip().replace('"', '').lower() for col in df.columns]

        # Remover colunas totalmente vazias que podem surgir do separador
        df = df.dropna(axis=1, how='all')

        # Remover a primeira e/ou última coluna se estiverem vazias (resíduo do separador |)
        if not df.empty:
            # Verifica se a primeira coluna é totalmente NaN ou vazia
            if df.iloc[:, 0].isnull().all() or (df.iloc[:, 0].astype(str) == '').all():
                df = df.iloc[:, 1:]
            # Verifica se a última coluna é totalmente NaN ou vazia
            if not df.empty and (df.iloc[:, -1].isnull().all() or (df.iloc[:, -1].astype(str) == '').all()):
                df = df.iloc[:, :-1]

            # Limpa espaços em branco das colunas de string
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()

            # Converte colunas numéricas, tratando erros
            # Usando pd.to_numeric em um loop para evitar o erro 'errors' se a versão do pandas for antiga
            for col in ['ambiente', 'entrada', 'saida', 'setpoint', 'histerese', 'ciclos', 'tempo_ciclo']:
                if col in df.columns:
                    # Tenta converter, se der erro, o valor vira NaN
                    df[col] = df[col].apply(lambda x: pd.to_numeric(x, errors='coerce'))
                    df[col] = df[col].fillna(0) # Preenche NaNs com 0

            # Cria coluna datetime combinando 'date' e 'time'
            if 'date' in df.columns and 'time' in df.columns:
                # Converte para string antes de combinar para evitar problemas de tipo
                df['datetime_str'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
                # Tenta converter para datetime, se der erro, o valor vira NaT
                df['datetime'] = pd.to_datetime(df['datetime_str'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
                df = df.dropna(subset=['datetime']) # Remove linhas com datetime inválido
                df = df.drop(columns=['datetime_str']) # Remove a coluna auxiliar
            else:
                st.warning(f"Colunas 'date' ou 'time' não encontradas no arquivo {os.path.basename(file_path)}. Gráficos de tempo podem ser afetados.")
                df['datetime'] = pd.to_datetime(df.index, unit='s') # Fallback para índice como datetime

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo {os.path.basename(file_path)}: {e}")
        return pd.DataFrame()

# Função para gerar PDF usando FPDF2
def gerar_pdf(df, filename="relatorio.pdf"):
    pdf = FPDF(orientation='L', unit='mm', format='A4') # Orientação paisagem
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(0, 10, "Relatório de Histórico de Dados Fromtherm", 0, 1, 'C')
    pdf.ln(5)

    # Informações do arquivo (se disponível)
    # pdf.cell(0, 10, f"Arquivo: {filename}", 0, 1, 'L')
    # pdf.ln(5)

    # Cabeçalho da tabela
    pdf.set_font("Arial", 'B', 10)
    col_widths = [25, 25, 25, 25, 25, 25, 25, 25, 25, 25] # Ajuste conforme o número de colunas e tamanho da página

    # Seleciona as colunas mais relevantes para o PDF
    cols_para_pdf = ['datetime', 'ambiente', 'entrada', 'saida', 'setpoint', 'histerese', 'ciclos', 'tempo_ciclo']
    cols_para_pdf = [col for col in cols_para_pdf if col in df.columns]

    # Ajusta o cabeçalho para o PDF
    header_pdf = [col.replace('_', ' ').title() for col in cols_para_pdf]

    # Calcula as larguras das colunas dinamicamente para caber na página
    page_width = pdf.w - 2*pdf.l_margin
    num_cols = len(cols_para_pdf)
    col_width = page_width / num_cols if num_cols > 0 else page_width # Largura igual para todas

    for col in header_pdf:
        pdf.cell(col_width, 10, col, 1, 0, 'C')
    pdf.ln()

    # Dados da tabela
    pdf.set_font("Arial", size=8)
    for index, row in df.iterrows():
        for col in cols_para_pdf:
            value = row[col]
            if pd.isna(value):
                display_value = "N/D"
            elif isinstance(value, datetime):
                display_value = value.strftime("%d/%m/%Y %H:%M:%S")
            elif isinstance(value, (int, float)):
                display_value = f"{value:.2f}" if col in ['ambiente', 'entrada', 'saida', 'setpoint', 'histerese'] else str(int(value))
            else:
                display_value = str(value)

            pdf.cell(col_width, 8, display_value, 1, 0, 'C')
        pdf.ln()

    # Salvar o PDF em um buffer de bytes
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    return pdf_output.getvalue()


# Função para exibir cards
def mostra_valor(label, value, unit, icon_class): # icon_class é agora apenas a classe do ícone
    st.markdown(f"""
        <div class="ft-card">
            <i class="bi {icon_class} ft-icon"></i>
            <span class="ft-label">{label}</span>
            <span class="ft-value">{value} {unit}</span>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# 4. LAYOUT DO STREAMLIT
# -------------------------------------------------

st.markdown('<div class="main-header">Dashboard de Testes Fromtherm</div>', unsafe_allow_html=True)

# Buscar todos os arquivos disponíveis
todos_arquivos_meta = buscar_arquivos()

# 4.1. BARRA LATERAL (FILTROS)
# -------------------------------------------------
# Substitua pela URL real da sua logo. Se não tiver, pode comentar esta linha ou usar uma imagem placeholder.
st.sidebar.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) 
st.sidebar.title("Filtros de Busca")

if todos_arquivos_meta:
    # Extrair opções únicas para os filtros
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos_meta if a['modelo'] != 'N/D'])))
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos_meta if a['operacao'] != 'N/D'])))
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos_meta if a['ano'] != 'N/D'])), reverse=True)
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos_meta if a['mes'] != 'N/D'])))
    datas_unicas = sorted(list(set([a['data'] for a in todos_arquivos_meta if a['data'] is not None])), reverse=True)

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
        arquivos_filtrados = [a for a in arquivos_filtrados if a['data_str'] == data_selecionada]

    # Ordenar os arquivos filtrados pela data e hora mais recente
    arquivos_filtrados = sorted(arquivos_filtrados, key=lambda x: (x['data'] if x['data'] else datetime.min.date(), x['hora']), reverse=True)

    # 4.2. ÚLTIMA LEITURA REGISTRADA (Cards)
    # -------------------------------------------------
    st.subheader("Última Leitura Registrada")

    ultima_linha = None
    if arquivos_filtrados:
        # Pega o arquivo mais recente da lista filtrada
        arquivo_mais_recente = arquivos_filtrados[0]
        df_mais_recente = carregar_csv(arquivo_mais_recente['path'])
        if not df_mais_recente.empty:
            ultima_linha = df_mais_recente.iloc[-1] # Pega a última linha do DataFrame

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if ultima_linha is not None and 'ambiente' in ultima_linha:
            mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
        else:
            mostra_valor("T-Ambiente", "N/D", "°C", "bi-thermometer-half")
    with col2:
        if ultima_linha is not None and 'entrada' in ultima_linha:
            mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-arrow-down-circle")
        else:
            mostra_valor("T-Entrada", "N/D", "°C", "bi-arrow-down-circle")
    with col3:
        if ultima_linha is not None and 'saida' in ultima_linha:
            mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-arrow-up-circle")
        else:
            mostra_valor("T-Saída", "N/D", "°C", "bi-arrow-up-circle")
    with col4:
        if ultima_linha is not None and 'setpoint' in ultima_linha:
            mostra_valor("Setpoint", f"{ultima_linha['setpoint']:.2f}", "°C", "bi-gear")
        else:
            mostra_valor("Setpoint", "N/D", "°C", "bi-gear")

    st.markdown("---")

    # 4.3. ABAS DE NAVEGAÇÃO
    # -------------------------------------------------
    tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

    with tab1:
        st.subheader("Históricos Disponíveis")
        if arquivos_filtrados:
            for arquivo_meta in arquivos_filtrados:
                with st.expander(f"**{arquivo_meta['nome']}** (Modelo: {arquivo_meta['modelo']}, Operação: {arquivo_meta['operacao']}, Data: {arquivo_meta['data_str']} {arquivo_meta['hora']})"):
                    df_arquivo = carregar_csv(arquivo_meta['path'])
                    if not df_arquivo.empty:
                        st.dataframe(df_arquivo, use_container_width=True)

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            # Botão de Download Excel
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                df_arquivo.to_excel(writer, index=False, sheet_name='Dados')
                            excel_buffer.seek(0)
                            st.download_button(
                                label="Baixar como Excel",
                                data=excel_buffer.getvalue(),
                                file_name=f"{arquivo_meta['nome'].replace('.csv', '')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        with col_dl2:
                            # Botão de Download PDF
                            pdf_bytes = gerar_pdf(df_arquivo, filename=f"{arquivo_meta['nome'].replace('.csv', '')}.pdf")
                            st.download_button(
                                label="Baixar como PDF",
                                data=pdf_bytes,
                                file_name=f"{arquivo_meta['nome'].replace('.csv', '')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.warning("Não foi possível carregar os dados deste arquivo.")
        else:
            st.info("Nenhum histórico disponível com os filtros aplicados.")

    with tab2:
        st.subheader("Crie Seu Gráfico")
        if arquivos_filtrados:
            # Carregar todos os dados dos arquivos filtrados para o gráfico
            df_todos_dados = pd.DataFrame()
            for arquivo_meta in arquivos_filtrados:
                df_temp = carregar_csv(arquivo_meta['path'])
                if not df_temp.empty:
                    df_todos_dados = pd.concat([df_todos_dados, df_temp], ignore_index=True)

            if not df_todos_dados.empty and 'datetime' in df_todos_dados.columns:
                # Opções de variáveis para o eixo Y
                variaveis_numericas = df_todos_dados.select_dtypes(include=['number']).columns.tolist()
                variaveis_para_grafico = [v for v in variaveis_numericas if v not in ['ciclos', 'tempo_ciclo']] # Exclui algumas que podem não fazer sentido no gráfico principal

                if 'datetime' in variaveis_para_grafico:
                    variaveis_para_grafico.remove('datetime') # datetime é o eixo X

                if variaveis_para_grafico:
                    y_vars_selecionadas = st.multiselect(
                        "Selecione as variáveis para o eixo Y",
                        options=variaveis_para_grafico,
                        default=[v for v in ['ambiente', 'entrada', 'saida', 'setpoint'] if v in variaveis_para_grafico]
                    )

                    if y_vars_selecionadas:
                        fig = px.line(
                            df_todos_dados,
                            x='datetime',
                            y=y_vars_selecionadas,
                            title='Variação das Temperaturas ao Longo do Tempo',
                            labels={'datetime': 'Data e Hora', 'value': 'Valor'},
                            hover_data={'datetime': '|%d/%m/%Y %H:%M:%S'}
                        )
                        fig.update_xaxes(
                            dtick="d1", # Tick a cada dia
                            tickformat="%d/%m/%Y\n%H:%M", # Formato de data e hora
                            showgrid=True
                        )
                        fig.update_layout(hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                else:
                    st.warning("Não há variáveis numéricas adequadas para gerar gráficos neste conjunto de dados.")
            else:
                st.info("Não há dados suficientes ou coluna 'datetime' para gerar gráficos com os filtros aplicados.")
        else:
            st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados.")