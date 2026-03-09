
import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheets, ParagraphStyle # CORRIGIDO: getSampleStyleSheets (plural)
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
    # Ou: historico_L1_YYYYMMDD_HHMM_MODELO.csv (sem OP/OPE)
    # Ou: historico_L1_YYYYMMDD_HHMM_OPX.csv (sem MODELO)
    # Ou: historico_L1_YYYYMMDD_HHMM.csv (sem OP/OPE e MODELO)
    # O objetivo é ser o mais abrangente possível.
    # Adicionado (?:_OP|OPE)?([A-Za-z0-9]+)? para capturar OP/OPE e o valor, ou apenas o valor.
    # Adicionado (?:_)?([A-Za-z0-9]+)? para o modelo, que pode ou não ter um underscore antes.
    # O grupo para o modelo é o último.
    # A data e hora são obrigatórias.
    regex_padrao = re.compile(r"historico_L1_(\d{8})_(\d{4})(?:_(OP|OPE)?([A-Za-z0-9]+))?(?:_([A-Za-z0-9]+))?\.csv$", re.IGNORECASE)

    for file_path in arquivos_encontrados:
        file_name = os.path.basename(file_path)
        match = regex_padrao.match(file_name)

        if match:
            data_str, hora_str, op_prefix, operacao, modelo = match.groups()

            # Tratar casos onde operacao ou modelo podem ser None
            operacao = operacao if operacao else "N/D"
            modelo = modelo if modelo else "N/D"

            # Se op_prefix existe, mas operacao não, significa que o valor de operacao é o que deveria ser o modelo
            # Ex: historico_L1_20260307_1704_OPE779.csv (sem modelo)
            # Ex: historico_L1_20260307_1704_FT55DBR.csv (modelo sem OP/OPE)
            # Este regex é complexo, vamos simplificar a extração para garantir que pegue o que existe.

            # Nova tentativa de extração mais robusta para operação e modelo
            partes_nome = file_name.replace('.csv', '').split('_')

            # Exemplo: historico_L1_20260306_0718_OP999_FTI378L_BR
            # partes_nome = ['historico', 'L1', '20260306', '0718', 'OP999', 'FTI378L', 'BR']

            # Vamos tentar pegar a operação e o modelo de forma mais flexível
            operacao_final = "N/D"
            modelo_final = "N/D"

            # A partir do 5º elemento (índice 4) em diante, pode ser operação ou modelo
            if len(partes_nome) > 4:
                # Se o 5º elemento começa com OP ou OPE, é a operação
                if partes_nome[4].startswith(('OP', 'OPE')):
                    operacao_final = partes_nome[4]
                    if len(partes_nome) > 5: # O próximo pode ser o modelo
                        modelo_final = "_".join(partes_nome[5:]) # Junta o resto como modelo
                else: # Se não começa com OP/OPE, assumimos que é o modelo
                    modelo_final = "_".join(partes_nome[4:]) # Junta o resto como modelo

            try:
                data_obj = datetime.strptime(data_str, "%Y%m%d")
                hora_obj = datetime.strptime(hora_str, "%H%M").time()

                todos_arquivos.append({
                    "caminho": file_path,
                    "nome": file_name,
                    "data": data_obj,
                    "data_f": data_obj.strftime("%d/%m/%Y"),
                    "hora": hora_obj.strftime("%H:%M"),
                    "ano": data_obj.year,
                    "mes": data_obj.month,
                    "operacao": operacao_final,
                    "modelo": modelo_final
                })
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido: {file_name}. Não segue o padrão esperado. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: {file_name}. Não segue o padrão esperado. Ignorando.")
    return todos_arquivos

@st.cache_data(ttl=3600) # Cache por 1 hora
def carregar_csv(file_path):
    """
    Carrega um arquivo CSV, trata o cabeçalho misto e limpa os dados.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        header_line_index = -1
        data_start_index = -1

        # Encontra a linha do cabeçalho e a linha de início dos dados
        for i, line in enumerate(lines):
            if 'Date' in line and 'Time' in line and ('ambiente' in line or 'entrada' in line):
                header_line_index = i
            if '---|---|' in line: # Linha de separação dos dados
                data_start_index = i + 1 # Os dados começam após esta linha
            if header_line_index != -1 and data_start_index != -1:
                break

        if header_line_index == -1 or data_start_index == -1:
            st.error(f"Formato de cabeçalho ou separador de dados inválido no arquivo: {os.path.basename(file_path)}")
            return pd.DataFrame()

        # Extrai os nomes das colunas da linha do cabeçalho
        header_line = lines[header_line_index]
        # Remove aspas duplas, espaços extras e divide por vírgula ou pipe
        raw_columns = re.split(r'[|,]', header_line.strip().replace('"', ''))

        # Limpa e padroniza os nomes das colunas
        column_names = [col.strip().lower() for col in raw_columns if col.strip()]

        # Lê os dados, pulando as linhas até o início dos dados
        df = pd.read_csv(
            file_path,
            sep='|',
            skiprows=data_start_index,
            header=None, # Não usa o cabeçalho do CSV diretamente
            names=column_names, # Usa os nomes de colunas limpos
            engine='python', # Necessário para skiprows e sep complexos
            encoding='utf-8'
        )

        # Remove a primeira e última coluna se estiverem vazias (resíduo do separador |)
        if not df.empty:
            if df.iloc[:, 0].isnull().all():
                df = df.iloc[:, 1:]
            if df.iloc[:, -1].isnull().all():
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
        arquivos_filtrados = [a for a in arquivos_filtrados if a['data'].strftime("%d/%m/%Y") == data_selecionada]

    # Ordenar por data e hora (mais recente primeiro)
    arquivos_filtrados = sorted(arquivos_filtrados, key=lambda x: (x['data'], x['hora']), reverse=True)

    # 4.2. CARDS DE ÚLTIMA LEITURA
    # -------------------------------------------------
    st.subheader("Última Leitura Disponível")
    if arquivos_filtrados:
        ultimo_arquivo_meta = arquivos_filtrados[0]
        df_ultimo = carregar_csv(ultimo_arquivo_meta['caminho'])

        if not df_ultimo.empty:
            ultima_linha = df_ultimo.iloc[-1] # Pega a última linha do DataFrame

            st.markdown(f"""
                <div style="text-align: center; font-size: 16px; font-weight: bold; color: #003366; margin-bottom: 20px;">
                    Modelo: {ultimo_arquivo_meta['modelo']} | Operação: {ultimo_arquivo_meta['operacao']} | Data: {ultimo_arquivo_meta['data_f']} | Hora: {ultimo_arquivo_meta['hora']}
                </div>
            """, unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
            with col2:
                mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-arrow-down-circle")
            with col3:
                mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-arrow-up-circle")
            with col4:
                mostra_valor("Setpoint", f"{ultima_linha['setpoint']:.2f}", "°C", "bi-gear")

            col5, col6, col7 = st.columns(3)
            with col5:
                mostra_valor("Histerese", f"{ultima_linha['histerese']:.2f}", "°C", "bi-arrow-left-right")
            with col6:
                mostra_valor("Ciclos", f"{int(ultima_linha['ciclos'])}", "", "bi-arrow-repeat")
            with col7:
                mostra_valor("Tempo Ciclo", f"{ultima_linha['tempo_ciclo']:.2f}", "s", "bi-hourglass-split")

        else:
            st.info("Nenhum dado válido encontrado no último histórico para exibir.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

    st.markdown("---") # Separador

    # 4.3. ABAS DE NAVEGAÇÃO
    # -------------------------------------------------
    tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

    with tab1:
        st.subheader("Históricos Disponíveis")
        if arquivos_filtrados:
            for arquivo_meta in arquivos_filtrados:
                with st.expander(f"**{arquivo_meta['modelo']} - Operação: {arquivo_meta['operacao']} - Data: {arquivo_meta['data_f']} {arquivo_meta['hora']}**"):
                    df_historico = carregar_csv(arquivo_meta['caminho'])
                    if not df_historico.empty:
                        st.dataframe(df_historico, use_container_width=True)

                        # Botões de Download
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            # Download como PDF
                            pdf_buffer = gerar_pdf(df_historico, arquivo_meta)
                            st.download_button(
                                label="Baixar como PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"historico_{arquivo_meta['modelo']}_{arquivo_meta['operacao']}_{arquivo_meta['data_f'].replace('/', '')}_{arquivo_meta['hora'].replace(':', '')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        with col_dl2:
                            # Download como Excel
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                df_historico.to_excel(writer, index=False, sheet_name='Historico')
                            st.download_button(
                                label="Baixar como Excel",
                                data=excel_buffer.getvalue(),
                                file_name=f"historico_{arquivo_meta['modelo']}_{arquivo_meta['operacao']}_{arquivo_meta['data_f'].replace('/', '')}_{arquivo_meta['hora'].replace(':', '')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    else:
                        st.info(f"Não foi possível carregar os dados para {arquivo_meta['nome']}.")
        else:
            st.info("Nenhum histórico disponível com os filtros aplicados.")

    with tab2:
        st.subheader("Crie Seu Gráfico")
        if todos_arquivos_meta:
            # Filtros para o gráfico (podem ser diferentes dos filtros de histórico)
            modelos_grafico = sorted(list(set([a['modelo'] for a in todos_arquivos_meta if a['modelo'] != 'N/D'])))
            operacoes_grafico = sorted(list(set([a['operacao'] for a in todos_arquivos_meta if a['operacao'] != 'N/D'])))
            datas_grafico = sorted(list(set([a['data'] for a in todos_arquivos_meta])), reverse=True)

            modelo_selecionado_grafico = st.selectbox("Selecione o Modelo para o Gráfico", ["Selecione"] + modelos_grafico)
            operacao_selecionada_grafico = st.selectbox("Selecione a Operação para o Gráfico", ["Selecione"] + operacoes_grafico)
            data_selecionada_grafico = st.selectbox("Selecione a Data para o Gráfico", ["Selecione"] + [d.strftime("%d/%m/%Y") for d in datas_grafico])

            arquivo_para_grafico = None
            if modelo_selecionado_grafico != "Selecione" and operacao_selecionada_grafico != "Selecione" and data_selecionada_grafico != "Selecione":
                for arquivo in todos_arquivos_meta:
                    if (arquivo['modelo'] == modelo_selecionado_grafico and
                        arquivo['operacao'] == operacao_selecionada_grafico and
                        arquivo['data'].strftime("%d/%m/%Y") == data_selecionada_grafico):
                        arquivo_para_grafico = arquivo
                        break

            if arquivo_para_grafico:
                df_grafico = carregar_csv(arquivo_para_grafico['caminho'])
                if not df_grafico.empty and 'datetime' in df_grafico.columns:
                    # Selecionar apenas colunas numéricas para o gráfico
                    colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()
                    # Remover colunas que não fazem sentido em um gráfico de linha (ex: ID, se houver)
                    colunas_numericas = [col for col in colunas_numericas if col not in ['id', 'index']]

                    if colunas_numericas:
                        variaveis_selecionadas = st.multiselect(
                            "Selecione as variáveis para o gráfico",
                            colunas_numericas,
                            default=colunas_numericas[:2] if len(colunas_numericas) >= 2 else colunas_numericas
                        )

                        if variaveis_selecionadas:
                            # Garante que 'datetime' é o eixo X
                            df_plot = df_grafico[['datetime'] + variaveis_selecionadas].melt(
                                id_vars=['datetime'], var_name="Variável", value_name="Valor"
                            )

                            fig = px.line(
                                df_plot,
                                x="datetime",
                                y="Valor",
                                color="Variável",
                                title=f"Gráfico de Tendência - Modelo: {arquivo_para_grafico['modelo']}, Operação: {arquivo_para_grafico['operacao']} em {arquivo_para_grafico['data_f']}",
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