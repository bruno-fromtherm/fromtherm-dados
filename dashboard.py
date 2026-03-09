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
# O Streamlit Cloud monta o repositório na raiz /mount/src/<repo_name>
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=3600) # Cache para evitar recarregar arquivos a cada interação
def buscar_arquivos():
    # Use glob para encontrar todos os arquivos CSV no DATA_PATH e subdiretórios
    # O asterisco duplo ** permite buscar em subdiretórios
    # recursive=True é necessário para que ** funcione
    csv_files = glob.glob(os.path.join(DATA_PATH, "**", "*.csv"), recursive=True)

    todos_arquivos = []
    # Regex para extrair informações do nome do arquivo
    # Ex: historico_L1_20260306_0718_OP999_FTI378L_BR.csv
    # Regex mais flexível para a operação (OP ou OPE) e modelo (qualquer coisa até .csv)
    # pattern = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)(\w+)_([a-zA-Z0-9_.-]+)\.csv")
    # Novo regex ainda mais flexível para o modelo, permitindo mais caracteres e garantindo que seja o final antes do .csv
    # Tentativa 1: Captura tudo depois de OP/OPE como modelo
    # pattern = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)(\w+)_([a-zA-Z0-9_.-]+)\.csv")

    # Regex mais robusto para capturar a operação e o modelo
    # Grupo 1: Ano (YYYY)
    # Grupo 2: Mês (MM)
    # Grupo 3: Dia (DD)
    # Grupo 4: Hora (HHMM)
    # Grupo 5: Operação (OP ou OPE seguido de dígitos/letras)
    # Grupo 6: Modelo (qualquer combinação de letras, números, _ ou -)
    pattern = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)([a-zA-Z0-9]+)_([a-zA-Z0-9_-]+)\.csv")

    for filepath in csv_files:
        filename = os.path.basename(filepath)
        match = pattern.match(filename)
        if match:
            ano, mes, dia, hora, op_prefix, op_sufix, modelo = match.groups()
            operacao = f"{op_prefix}{op_sufix}" # Recombina OP/OPE com o sufixo

            data_obj = datetime.strptime(f"{ano}-{mes}-{dia}", "%Y-%m-%d").date()
            data_formatada = data_obj.strftime("%d/%m/%Y")
            hora_formatada = f"{hora[:2]}:{hora[2:]}"

            todos_arquivos.append({
                "filepath": filepath,
                "filename": filename,
                "modelo": modelo,
                "ano": ano,
                "mes": mes,
                "data": data_obj,
                "data_f": data_formatada, # Data formatada para exibição
                "hora": hora_formatada,
                "operacao": operacao
            })
        else:
            st.warning(f"Nome de arquivo CSV inválido: {filename}. Não segue o padrão esperado. Ignorando.")

    # Ordena os arquivos pelo modelo, depois pela data e hora
    todos_arquivos.sort(key=lambda x: (x['modelo'], x['data'], x['hora']))
    return todos_arquivos

@st.cache_data(ttl=3600) # Cache para evitar recarregar o mesmo CSV várias vezes
def carregar_csv(filepath):
    try:
        # Tenta ler com o separador '|' e sem aspas duplas (quotechar=None)
        # skiprows=[1] para pular a linha de separação '---'
        df = pd.read_csv(filepath, sep='|', skiprows=[1], quotechar=None, encoding='utf-8', engine='python')

        # Remove a primeira e a última coluna que podem ser vazias devido ao separador '|'
        df = df.iloc[:, 1:-1]

        # --- NOVO: Limpeza e padronização dos nomes das colunas ---
        df.columns = [col.strip().lower().replace(' ', '_').replace('/', '_') for col in df.columns]

        # Mapeamento de nomes de colunas para garantir consistência
        # Isso é útil se houver pequenas variações nos nomes das colunas entre os arquivos
        column_mapping = {
            'date': 'date', 'time': 'time', 'ambiente': 'ambiente', 'entrada': 'entrada',
            'saida': 'saida', 'dif': 'dif', 'tensao': 'tensao', 'corrente': 'corrente',
            'kacl_h': 'kacl/h', 'vazao': 'vazao', 'kw_aquecimento': 'kw aquecimento',
            'kw_consumo': 'kw consumo', 'cop': 'cop'
        }
        df = df.rename(columns=column_mapping)

        # Converte colunas numéricas, tratando vírgulas e valores inválidos
        numeric_cols = ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 
                        'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # Preenche erros com 0
            else:
                st.warning(f"Coluna '{col}' não encontrada no arquivo {os.path.basename(filepath)}. Verifique o CSV.")

        # Combina 'Date' e 'Time' em uma única coluna datetime
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y/%m/%d %H:%M:%S', errors='coerce')
            df = df.dropna(subset=['datetime']) # Remove linhas com datetime inválido
        else:
            st.error(f"Colunas 'Date' ou 'Time' não encontradas no arquivo {os.path.basename(filepath)}. Verifique o CSV.")
            return pd.DataFrame() # Retorna DataFrame vazio se colunas essenciais estiverem faltando

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(filepath)}': {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# -------------------------------------------------
# 4. LAYOUT DO DASHBOARD
# -------------------------------------------------

# Carrega todos os arquivos CSV e seus metadados
todos_arquivos = buscar_arquivos()

# 4.1. BARRA LATERAL
with st.sidebar:
    st.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
    st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Filtros de Busca")

    # Garante que as listas de opções não estejam vazias
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D']))) if todos_arquivos else []
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos if a['ano'] != 'N/D']))) if todos_arquivos else []
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos if a['mes'] != 'N/D']))) if todos_arquivos else []
    datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos if a['data_f'] != 'N/D']))) if todos_arquivos else []
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D']))) if todos_arquivos else []

    # Adiciona "Todos" como opção para os filtros
    modelo_selecionado = st.selectbox("Modelo", ["Todos"] + modelos_unicos)
    ano_selecionado = st.selectbox("Ano", ["Todos"] + anos_unicos)
    mes_selecionado = st.selectbox("Mês", ["Todos"] + meses_unicos)
    data_selecionada = st.selectbox("Data", ["Todos"] + datas_unicas)
    operacao_selecionada = st.selectbox("Operação", ["Todos"] + operacoes_unicas)

    st.markdown("---")
    st.markdown("Desenvolvido por **Inner AI**")

# 4.2. FILTRAGEM DOS ARQUIVOS
arquivos_filtrados = todos_arquivos
if modelo_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == modelo_selecionado]
if ano_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == ano_selecionado]
if mes_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == mes_selecionado]
if data_selecionada != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == data_selecionada]
if operacao_selecionada != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == operacao_selecionada]

# 4.3. CONTEÚDO PRINCIPAL
st.markdown("<h2 style='color: #003366; text-align: center;'>Última Leitura Registrada</h2>", unsafe_allow_html=True)

if arquivos_filtrados:
    # Pega o último arquivo filtrado (assumindo que já está ordenado)
    ultimo_arquivo_info = arquivos_filtrados[-1]
    df_ultima_leitura = carregar_csv(ultimo_arquivo_info['filepath'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1]

        # Informações do Teste
        st.markdown(f"""
            <div style="background-color: #e6f2ff; padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: #003366;">
                <strong>Modelo:</strong> {ultimo_arquivo_info['modelo']} |
                <strong>Operação:</strong> {ultimo_arquivo_info['operacao']} |
                <strong>Data:</strong> {ultimo_arquivo_info['data_f']} |
                <strong>Hora:</strong> {ultimo_arquivo_info['hora']}
            </div>
        """, unsafe_allow_html=True)

        # Exibição dos cards
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        with col1: mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
        with col2: mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-thermometer-up")
        with col3: mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-thermometer-down")
        with col4: mostra_valor("T-Diferença", f"{ultima_linha['dif']:.2f}", "°C", "bi-arrow-down-up")
        with col5: mostra_valor("Tensão", f"{ultima_linha['tensao']:.1f}", "V", "bi-lightning-charge")
        with col6: mostra_valor("Corrente", f"{ultima_linha['corrente']:.1f}", "A", "bi-lightning")
        with col7: mostra_valor("Vazão", f"{ultima_linha['vazao']:.0f}", "L/h", "bi-droplet")

        col8, col9, col10 = st.columns(3) # Novas colunas para os 3 cards restantes
        with col8: mostra_valor("kCal/h", f"{ultima_linha['kacl/h']:.1f}", "", "bi-fire")
        with col9: mostra_valor("kW Aquecimento", f"{ultima_linha['kw aquecimento']:.1f}", "", "bi-sun")
        with col10: mostra_valor("kW Consumo", f"{ultima_linha['kw consumo']:.1f}", "", "bi-power")
        # COP não está na lista de cards solicitados, mas se precisar, adicione aqui
        # with col11: mostra_valor("COP", f"{ultima_linha['cop']:.1f}", "", "bi-speedometer")

    else:
        st.warning("Não foi possível carregar os dados do último histórico filtrado.")
else:
    st.info("Nenhum histórico disponível com os filtros aplicados.")

st.markdown("---")

# 4.4. ABAS DE NAVEGAÇÃO
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("<h3 style='color: #003366;'>Históricos Disponíveis</h3>", unsafe_allow_html=True)
    if arquivos_filtrados:
        for i, arquivo_info in enumerate(arquivos_filtrados):
            expander_label = f"Modelo: {arquivo_info['modelo']} | Operação: {arquivo_info['operacao']} | Data: {arquivo_info['data_f']} | Hora: {arquivo_info['hora']}"
            with st.expander(expander_label):
                df_historico = carregar_csv(arquivo_info['filepath'])
                if not df_historico.empty:
                    st.dataframe(df_historico, use_container_width=True)

                    # Botões de Download
                    col_dl1, col_dl2 = st.columns(2)

                    # Nome do arquivo para download
                    nome_base = f"Maquina_{arquivo_info['modelo']}_OP{arquivo_info['operacao']}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora'].replace(':', 'hs')}"

                    # Download CSV
                    csv_buffer = BytesIO()
                    df_historico.to_csv(csv_buffer, index=False, sep=';', decimal=',') # Usar ; e , para compatibilidade Excel BR
                    csv_buffer.seek(0)
                    with col_dl1:
                        st.download_button(
                            label="Baixar CSV",
                            data=csv_buffer,
                            file_name=f"{nome_base}.csv",
                            mime="text/csv",
                            key=f"download_csv_{i}"
                        )

                    # Download PDF
                    pdf_buffer = BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                    styles = getSampleStyleSheet()

                    # Estilo para o título do PDF
                    title_style = ParagraphStyle(
                        'TitleStyle',
                        parent=styles['h2'],
                        fontSize=16,
                        leading=20,
                        alignment=1, # Center
                        spaceAfter=12,
                        textColor=colors.HexColor('#003366')
                    )

                    # Estilo para informações do teste
                    info_style = ParagraphStyle(
                        'InfoStyle',
                        parent=styles['Normal'],
                        fontSize=10,
                        leading=12,
                        alignment=1, # Center
                        spaceAfter=6,
                        textColor=colors.black
                    )

                    elements = []
                    elements.append(Paragraph(f"Relatório de Histórico - Máquina {arquivo_info['modelo']}", title_style))
                    elements.append(Paragraph(f"Operação: {arquivo_info['operacao']} | Data: {arquivo_info['data_f']} | Hora: {arquivo_info['hora']}", info_style))
                    elements.append(Spacer(1, 0.2 * inch)) # Adiciona um pequeno espaço

                    # Preparar dados para a tabela do PDF
                    data_pdf = [df_historico.columns.tolist()] + df_historico.values.tolist()
                    table = Table(data_pdf)

                    # Estilo da tabela
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    elements.append(table)
                    doc.build(elements)
                    pdf_buffer.seek(0)

                    with col_dl2:
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=f"{nome_base}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{i}"
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para {arquivo_info['filename']}.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.markdown("<h3 style='color: #003366;'>Crie Seu Gráfico</h3>", unsafe_allow_html=True)

    if arquivos_filtrados:
        # Filtros para o gráfico (seleciona um único arquivo para plotar)
        st.subheader("Selecione um Histórico para o Gráfico")

        # Cria uma lista de opções para o selectbox do gráfico
        opcoes_grafico = [
            f"Modelo: {a['modelo']} | Operação: {a['operacao']} | Data: {a['data_f']} | Hora: {a['hora']}"
            for a in arquivos_filtrados
        ]

        selecao_grafico = st.selectbox("Escolha o histórico:", opcoes_grafico)

        arquivo_para_grafico = None
        if selecao_grafico:
            # Encontra o arquivo_info correspondente à seleção
            for a in arquivos_filtrados:
                if f"Modelo: {a['modelo']} | Operação: {a['operacao']} | Data: {a['data_f']} | Hora: {a['hora']}" == selecao_grafico:
                    arquivo_para_grafico = a
                    break

        if arquivo_para_grafico:
            df_grafico = carregar_csv(arquivo_para_grafico['filepath'])
            if not df_grafico.empty:
                # Identifica colunas numéricas para o gráfico
                colunas_numericas = df_grafico.select_dtypes(include=['float64', 'int64']).columns.tolist()
                # Remove 'Date', 'Time' e 'datetime' se estiverem na lista de numéricas (improvável, mas para segurança)
                colunas_numericas = [col for col in colunas_numericas if col not in ['date', 'time', 'datetime']]

                if colunas_numericas:
                    st.subheader("Selecione as Variáveis para o Gráfico")
                    variaveis_selecionadas = st.multiselect(
                        "Variáveis:",
                        options=colunas_numericas,
                        default=[col for col in ['ambiente', 'entrada', 'saida'] if col in colunas_numericas][:3] # Seleciona as 3 primeiras por padrão
                    )

                    if variaveis_selecionadas:
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