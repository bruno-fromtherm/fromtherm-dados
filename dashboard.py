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
    regex_padrao = re.compile(r'historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)(\w+)_([a-zA-Z0-9-]+)\.csv')

    for file_path in arquivos_encontrados:
        file_name = os.path.basename(file_path)
        match = regex_padrao.match(file_name)

        if match:
            ano, mes, dia, hora_str, op_prefix, operacao, modelo = match.groups()
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
                'operacao': f"{op_prefix}{operacao}",
                'modelo': modelo
            })
        else:
            # Fallback para arquivos que não seguem o padrão exato
            st.warning(f"Nome de arquivo CSV inválido: {file_name}. Não segue o padrão esperado. Ignorando.")
            # Adiciona com N/D para que apareça na lista, mas com dados incompletos
            try:
                # Tenta extrair data e hora minimamente
                partes = file_name.split('_')
                if len(partes) >= 4:
                    ano_f = partes[2][:4]
                    mes_f = partes[2][4:6]
                    dia_f = partes[2][6:8]
                    data_str_f = f"{dia_f}/{mes_f}/{ano_f}"
                    hora_str_f = partes[3]
                    hora_formatada_f = f"{hora_str_f[:2]}:{hora_str_f[2:]}:00"
                    data_obj_f = datetime.strptime(data_str_f, "%d/%m/%Y").date()
                else:
                    data_str_f = "N/D"
                    hora_formatada_f = "N/D"
                    data_obj_f = None
                    ano_f = "N/D"
                    mes_f = "N/D"
                    dia_f = "N/D"
            except Exception:
                data_str_f = "N/D"
                hora_formatada_f = "N/D"
                data_obj_f = None
                ano_f = "N/D"
                mes_f = "N/D"
                dia_f = "N/D"

            lista_arquivos_meta.append({
                'path': file_path,
                'nome': file_name,
                'data': data_obj_f,
                'data_str': data_str_f,
                'hora': hora_formatada_f,
                'ano': ano_f,
                'mes': mes_f,
                'dia': dia_f,
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

        # Tentar inferir o separador (priorizando pipe, depois vírgula)
        # Analisa a linha do cabeçalho para ver qual separador tem mais ocorrências
        header_line = lines[header_line_index]
        if '|' in header_line and header_line.count('|') > header_line.count(','):
            sep = '|'
        else:
            sep = ','

        # Carregar o CSV com o separador detectado e pulando linhas antes do cabeçalho
        df = pd.read_csv(file_path, sep=sep, skiprows=header_line_index, encoding='utf-8', errors='ignore')

        # Limpeza do cabeçalho: remover espaços, aspas e caracteres indesejados
        df.columns = df.columns.str.strip().str.replace('"', '').str.replace("'", "").str.lower()

        # Remover colunas totalmente vazias (que podem surgir de separadores extras no final)
        df = df.dropna(axis=1, how='all')

        # Remover a última coluna se for totalmente vazia (comum em CSVs com separador extra no final)
        if not df.empty and df.iloc[:, -1].isnull().all().all():
                df = df.iloc[:, :-1]

        # Limpa espaços em branco das colunas de string
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()

        # Converte colunas numéricas, tratando erros
        for col in ['ambiente', 'entrada', 'saida', 'setpoint', 'histerese', 'ciclos', 'tempo_ciclo']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Preenche NaNs com 0 ou outro valor padrão se for o caso
                df[col] = df[col].fillna(0) # Ou df[col].fillna(df[col].mean())

        # Cria coluna datetime combinando 'date' e 'time'
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce', format='%d/%m/%Y %H:%M:%S')
            df = df.dropna(subset=['datetime']) # Remove linhas com datetime inválido
        else:
            st.warning(f"Colunas 'date' ou 'time' não encontradas no arquivo {os.path.basename(file_path)}. Gráficos de tempo podem ser afetados.")
            df['datetime'] = pd.to_datetime(df.index, unit='s') # Fallback para índice como datetime

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo {os.path.basename(file_path)}: {e}")
        return pd.DataFrame()

# Função para exibir cards de valor
def mostra_valor(label, value, icon, color="blue"):
    st.markdown(f"""
    <div class="ft-card">
        <i class="bi bi-{icon} ft-icon {color}"></i>
        <span class="ft-label">{label}</span>
        <span class="ft-value">{value}</span>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# FUNÇÃO DE GERAÇÃO DE PDF (AGORA COM FPDF2)
# -------------------------------------------------
def gerar_pdf(df, filename="relatorio.pdf"):
    pdf = FPDF(orientation='L', unit='mm', format='A4') # Orientação paisagem para tabelas largas
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(0, 10, "Relatório de Histórico de Dados Fromtherm", 0, 1, 'C')
    pdf.ln(10)

    # Informações básicas (se disponíveis)
    if not df.empty:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 7, f"Data do Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)

        # Tenta pegar a primeira e última data do DataFrame
        if 'datetime' in df.columns and not df['datetime'].empty:
            primeira_data = df['datetime'].min().strftime('%d/%m/%Y %H:%M:%S')
            ultima_data = df['datetime'].max().strftime('%d/%m/%Y %H:%M:%S')
            pdf.cell(0, 7, f"Período dos Dados: {primeira_data} a {ultima_data}", 0, 1)
        pdf.ln(5)

    # Cabeçalho da tabela
    pdf.set_font("Arial", 'B', 8) # Fonte menor e negrito para o cabeçalho da tabela
    col_widths = [20, 25, 25, 20, 20, 20, 20, 20, 20, 20, 20] # Ajuste as larguras conforme necessário
    headers = ['Data', 'Hora', 'Ambiente', 'Entrada', 'Saída', 'Temperatura', 'Setpoint', 'Histerese', 'Ciclos', 'Tempo Ciclo', 'Operação']

    # Desenha o cabeçalho
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, header, 1, 0, 'C')
    pdf.ln()

    # Dados da tabela
    pdf.set_font("Arial", size=7) # Fonte ainda menor para os dados
    for index, row in df.iterrows():
        # Formata os valores para exibição
        data_val = row['date'] if 'date' in row else 'N/D'
        hora_val = row['time'] if 'time' in row else 'N/D'
        ambiente_val = f"{row['ambiente']:.2f}" if 'ambiente' in row else 'N/D'
        entrada_val = f"{row['entrada']:.2f}" if 'entrada' in row else 'N/D'
        saida_val = f"{row['saida']:.2f}" if 'saida' in row else 'N/D'
        temperatura_val = f"{row['temperatura']:.2f}" if 'temperatura' in row else 'N/D'
        setpoint_val = f"{row['setpoint']:.2f}" if 'setpoint' in row else 'N/D'
        histerese_val = f"{row['histerese']:.2f}" if 'histerese' in row else 'N/D'
        ciclos_val = str(int(row['ciclos'])) if 'ciclos' in row else 'N/D'
        tempo_ciclo_val = f"{row['tempo_ciclo']:.2f}" if 'tempo_ciclo' in row else 'N/D'
        operacao_val = row['operacao'] if 'operacao' in row else 'N/D' # Adicionado 'operacao'

        values = [
            data_val, hora_val, ambiente_val, entrada_val, saida_val, temperatura_val,
            setpoint_val, histerese_val, ciclos_val, tempo_ciclo_val, operacao_val
        ]

        # Verifica se a página atual tem espaço suficiente para a próxima linha
        # Se não tiver, adiciona uma nova página
        if pdf.get_y() + 7 > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 8)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 7, header, 1, 0, 'C')
            pdf.ln()
            pdf.set_font("Arial", size=7)

        for i, value in enumerate(values):
            pdf.cell(col_widths[i], 7, str(value), 1, 0, 'C')
        pdf.ln()

    # Salvar o PDF em um buffer de bytes
    pdf_output = BytesIO()
    pdf.output(pdf_output, 'S') # 'S' para retornar como string (bytes)
    return pdf_output.getvalue()


# -------------------------------------------------
# 4. LAYOUT DO STREAMLIT
# -------------------------------------------------

st.markdown('<div class="main-header">Dashboard de Testes Fromtherm</div>', unsafe_allow_html=True)

# Buscar todos os arquivos disponíveis
todos_arquivos_meta = buscar_arquivos()

# 4.1. BARRA LATERAL (FILTROS)
# -------------------------------------------------
st.sidebar.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
st.sidebar.title("Filtros de Busca")

if todos_arquivos_meta:
    # Extrair opções únicas para os filtros
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos_meta if a['modelo'] != 'N/D'])))
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos_meta if a['operacao'] != 'N/D'])))
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos_meta])), reverse=True)
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos_meta])))
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

    # Ordenar arquivos filtrados por data e hora
    arquivos_filtrados = sorted(arquivos_filtrados, key=lambda x: (x['data'] if x['data'] else datetime.min.date(), x['hora']), reverse=True)

    # Carregar o último arquivo para os cards de "Última Leitura"
    df_ultima_leitura = pd.DataFrame()
    ultima_linha = {}
    if arquivos_filtrados:
        df_ultima_leitura = carregar_csv(arquivos_filtrados[0]['path'])
        if not df_ultima_leitura.empty:
            ultima_linha = df_ultima_leitura.iloc[-1].to_dict()

    # 4.2. CARDS DE ÚLTIMA LEITURA
    # -------------------------------------------------
    st.subheader("Última Leitura Registrada")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        mostra_valor("T-Ambiente", f"{ultima_linha.get('ambiente', 'N/D'):.2f}" if isinstance(ultima_linha.get('ambiente'), (int, float)) else "N/D", "thermometer-half", "azul")
    with col2:
        mostra_valor("T-Entrada", f"{ultima_linha.get('entrada', 'N/D'):.2f}" if isinstance(ultima_linha.get('entrada'), (int, float)) else "N/D", "arrow-down-circle", "verde")
    with col3:
        mostra_valor("T-Saída", f"{ultima_linha.get('saida', 'N/D'):.2f}" if isinstance(ultima_linha.get('saida'), (int, float)) else "N/D", "arrow-up-circle", "vermelho")
    with col4:
        mostra_valor("Setpoint", f"{ultima_linha.get('setpoint', 'N/D'):.2f}" if isinstance(ultima_linha.get('setpoint'), (int, float)) else "N/D", "gear", "ouro")

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
                        st.dataframe(df_arquivo)

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            # Botão de Download CSV (Excel)
                            csv_buffer = BytesIO()
                            df_arquivo.to_excel(csv_buffer, index=False, engine='xlsxwriter')
                            st.download_button(
                                label="Baixar como Excel",
                                data=csv_buffer.getvalue(),
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