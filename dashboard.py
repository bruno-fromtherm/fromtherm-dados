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
DATA_PATH = "dados_brutos/historico_L1" # Certifique-se que esta pasta existe no seu repositório

@st.cache_data(ttl=3600) # Cache para não recarregar os arquivos toda hora
def buscar_arquivos():
    arquivos_encontrados = []

    # Regex ultra-robusto:
    # ^historico_L1_ : Início padrão
    # (\d{8}) : Grupo 1 - Data (YYYYMMDD)
    # _(\d{4}) : Grupo 2 - Hora (HHMM)
    # _(OP\d{3,4})? : Grupo 3 - Operação (OP seguido de 3 ou 4 dígitos, opcional)
    # _([A-Za-z0-9_]+)? : Grupo 4 - Modelo (qualquer combinação de letras, números e _, opcional)
    # \.csv$ : Fim do arquivo .csv

    # Este regex tenta ser o mais flexível possível para capturar as partes,
    # mas se uma parte não existir, o grupo será None.
    # Isso evita que o programa quebre com nomes de arquivo que não seguem o padrão exato.
    # Exemplos:
    # historico_L1_20260308_0939_OP987_FTA987BR.csv
    # historico_L1_20260306_0718_OP999_FTI378L_BR.csv
    # historico_L1_20260305_2340_OP8888_FTI240L_BR.csv
    # historico_L1_20260307_TESTE_NOVO.csv (Data e Hora seriam capturadas, OP e Modelo seriam None)
    # historico_L1_20260306_0718_OP999_FTI378L_BR.csv (o erro que você reportou)

    # Novo regex mais flexível para o modelo e operação
    # O modelo pode ter letras, números e underscores, e a operação pode ter 3 ou 4 dígitos
    regex_padrao = re.compile(r"^historico_L1_(\d{8})_(\d{4})(?:_(OP\d{3,4}))?(?:_([A-Za-z0-9_]+))?\.csv$")

    if not os.path.exists(DATA_PATH):
        st.error(f"A pasta de dados '{DATA_PATH}' não foi encontrada. Por favor, verifique o caminho.")
        return []

    for filename in glob.glob(os.path.join(DATA_PATH, "*.csv")):
        basename = os.path.basename(filename)
        match = regex_padrao.match(basename)

        if match:
            data_str, hora_str = match.group(1), match.group(2)
            operacao_match = match.group(3)
            modelo_match = match.group(4)

            try:
                data_obj = datetime.strptime(data_str + hora_str, "%Y%m%d%H%M")

                # Usar "N/D" se a operação ou modelo não foram capturados
                operacao = operacao_match if operacao_match else "N/D"
                modelo = modelo_match if modelo_match else "N/D"

                arquivos_encontrados.append({
                    "caminho": filename,
                    "nome_arquivo": basename,
                    "data_obj": data_obj,
                    "data_f": data_obj.strftime("%d/%m/%Y"),
                    "hora_f": data_obj.strftime("%H:%M"),
                    "ano": data_obj.year,
                    "mes": data_obj.month,
                    "operacao": operacao,
                    "modelo": modelo
                })
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido: {basename}. Não foi possível extrair a data/hora. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: {basename}. Não segue o padrão esperado. Ignorando.")

    # Ordenar os arquivos do mais recente para o mais antigo
    arquivos_encontrados.sort(key=lambda x: x['data_obj'], reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=3600) # Cache para não recarregar o CSV toda hora
def carregar_csv(caminho_arquivo):
    try:
        # Tenta ler com o separador '|' e sem aspas duplas (quotechar=None)
        # Isso é crucial para evitar o erro 'expected after ""'
        df = pd.read_csv(caminho_arquivo, sep='|', skiprows=[1], quotechar=None, encoding='utf-8', engine='python')

        # Remove colunas vazias que podem surgir do separador '|' no início/fim
        df = df.dropna(axis=1, how='all')

        # Limpa nomes das colunas (remove espaços em branco e caracteres indesejados)
        df.columns = df.columns.str.strip().str.replace(' ', '_').str.lower()

        # Renomeia colunas para padronização se necessário
        df = df.rename(columns={'kacl/h': 'kacal_h', 'kw_aquecimento': 'kw_aquecimento', 'kw_consumo': 'kw_consumo'})

        # Converte colunas de data e hora
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y/%m/%d %H:%M:%S', errors='coerce')
            df = df.drop(columns=['date', 'time'])
        else:
            st.warning(f"Colunas 'Date' ou 'Time' não encontradas em {os.path.basename(caminho_arquivo)}. Gráficos podem ser afetados.")
            df['datetime'] = pd.to_datetime(df.index, errors='coerce') # Cria um datetime básico se não encontrar

        # Converte colunas numéricas, tratando vírgulas e zeros à esquerda
        colunas_numericas = ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacal_h', 'vazao', 'kw_aquecimento', 'kw_consumo', 'cop']
        for col in colunas_numericas:
            if col in df.columns:
                # Garante que a coluna é string antes de substituir, para evitar erros com tipos mistos
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                # Converte para numérico, forçando erros para NaN e depois preenchendo com 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                st.warning(f"Coluna numérica '{col}' não encontrada em {os.path.basename(caminho_arquivo)}.")

        return df

    except pd.errors.ParserError as e:
        st.error(f"Erro de parsing ao carregar o CSV '{os.path.basename(caminho_arquivo)}': {e}. Verifique o formato do arquivo.")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro
    except Exception as e:
        st.error(f"Erro inesperado ao carregar o CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

# -------------------------------------------------
# 4. LAYOUT DO DASHBOARD
# -------------------------------------------------

# Carrega todos os arquivos disponíveis
todos_arquivos = buscar_arquivos()

# 4.1. BARRA LATERAL (FILTROS)
with st.sidebar:
    st.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
    st.markdown("<h2 class='sidebar-title'>Filtros de Busca</h2>", unsafe_allow_html=True)

    # Garante que as listas de opções não estejam vazias
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D']))) if todos_arquivos else []
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D']))) if todos_arquivos else []
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos]))) if todos_arquivos else []
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos]))) if todos_arquivos else []
    datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos]))) if todos_arquivos else []

    # Adiciona "Todos" como opção padrão
    modelo_selecionado = st.selectbox("Modelo", ["Todos"] + modelos_unicos)
    operacao_selecionada = st.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
    ano_selecionado = st.selectbox("Ano", ["Todos"] + anos_unicos)
    mes_selecionado = st.selectbox("Mês", ["Todos"] + meses_unicos, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos")
    data_selecionada = st.selectbox("Data", ["Todos"] + datas_unicas)

# Aplica os filtros
arquivos_filtrados = todos_arquivos
if modelo_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == modelo_selecionado]
if operacao_selecionada != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == operacao_selecionada]
if ano_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == ano_selecionado]
if mes_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == mes_selecionado]
if data_selecionada != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == data_selecionada]

# 4.2. ÁREA PRINCIPAL
st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("### Última Leitura Registrada")

    if arquivos_filtrados:
        ultimo_arquivo_info = arquivos_filtrados[0]
        df_ultimo = carregar_csv(ultimo_arquivo_info['caminho'])

        if not df_ultimo.empty:
            ultima_linha = df_ultimo.iloc[-1] # Pega a última linha do DataFrame

            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            with col1:
                mostra_valor("T. AMBIENTE", f"{ultima_linha['ambiente']:.1f}", "°C", "bi-thermometer-half")
            with col2:
                mostra_valor("ENTRADA", f"{ultima_linha['entrada']:.1f}", "°C", "bi-arrow-down-circle")
            with col3:
                mostra_valor("SAÍDA", f"{ultima_linha['saida']:.1f}", "°C", "bi-arrow-up-circle")
            with col4:
                mostra_valor("ΔT", f"{ultima_linha['dif']:.1f}", "°C", "bi-thermometer-high")
            with col5:
                mostra_valor("TENSÃO", f"{ultima_linha['tensao']:.1f}", "V", "bi-lightning-charge")
            with col6:
                mostra_valor("CORRENTE", f"{ultima_linha['corrente']:.1f}", "A", "bi-lightning")
            with col7:
                mostra_valor("VAZÃO", f"{ultima_linha['vazao']:.1f}", "L/min", "bi-droplet-half")

            st.markdown("---")
            st.markdown("### Históricos Disponíveis")

            for arquivo_info in arquivos_filtrados:
                with st.expander(f"**{arquivo_info['modelo']} - OP {arquivo_info['operacao']} - {arquivo_info['data_f']} {arquivo_info['hora_f']}**"):
                    df_exibir = carregar_csv(arquivo_info['caminho'])
                    if not df_exibir.empty:
                        st.dataframe(df_exibir.drop(columns=['datetime'], errors='ignore'), use_container_width=True)

                        # Botões de Download
                        col_dl1, col_dl2 = st.columns(2)

                        # Formata o nome do arquivo para download
                        nome_base_download = f"Maquina_{arquivo_info['modelo']}_OP{arquivo_info['operacao']}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora_f'].replace(':', 'hs')}"

                        with col_dl1:
                            # Download CSV
                            csv_data = df_exibir.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')
                            st.download_button(
                                label="Baixar como CSV",
                                data=csv_data,
                                file_name=f"{nome_base_download}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with col_dl2:
                            # Download PDF
                            buffer_pdf = BytesIO()
                            doc = SimpleDocTemplate(buffer_pdf, pagesize=landscape(A4))
                            styles = getSampleStyleSheet()

                            # Estilo para o título do PDF
                            style_title = ParagraphStyle(
                                'TitleStyle',
                                parent=styles['h1'],
                                fontName='Helvetica-Bold',
                                fontSize=16,
                                alignment=1, # Centro
                                spaceAfter=12
                            )

                            # Estilo para o cabeçalho da tabela
                            style_header = ParagraphStyle(
                                'HeaderStyle',
                                parent=styles['Normal'],
                                fontName='Helvetica-Bold',
                                fontSize=8,
                                alignment=1, # Centro
                                textColor=colors.white
                            )

                            # Estilo para o corpo da tabela
                            style_body = ParagraphStyle(
                                'BodyStyle',
                                parent=styles['Normal'],
                                fontName='Helvetica',
                                fontSize=7,
                                alignment=1 # Centro
                            )

                            story = []
                            story.append(Paragraph(f"Relatório de Histórico - {arquivo_info['modelo']} - OP {arquivo_info['operacao']} - {arquivo_info['data_f']} {arquivo_info['hora_f']}", style_title))
                            story.append(Spacer(1, 0.2 * cm))

                            # Prepara os dados para a tabela do PDF
                            data_pdf = [
                                [Paragraph(col, style_header) for col in df_exibir.drop(columns=['datetime'], errors='ignore').columns]
                            ] + [
                                [Paragraph(str(cell), style_body) for cell in row]
                                for row in df_exibir.drop(columns=['datetime'], errors='ignore').values
                            ]

                            table = Table(data_pdf)
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f4f7f6')), # Linhas alternadas
                                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                ('LEFTPADDING', (0,0), (-1,-1), 2),
                                ('RIGHTPADDING', (0,0), (-1,-1), 2),
                            ]))
                            story.append(table)
                            doc.build(story)

                            st.download_button(
                                label="Baixar como PDF",
                                data=buffer_pdf.getvalue(),
                                file_name=f"{nome_base_download}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.warning("Não foi possível carregar os dados para este histórico.")

    else:
        st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura ou lista de históricos.")

with tab2:
    st.markdown("### Crie Seu Gráfico Personalizado")

    if arquivos_filtrados:
        # Filtros para o gráfico
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            modelo_grafico = st.selectbox("Modelo para Gráfico", sorted(list(set([a['modelo'] for a in arquivos_filtrados if a['modelo'] != 'N/D']))))
        with col_g2:
            operacao_grafico = st.selectbox("Operação para Gráfico", sorted(list(set([a['operacao'] for a in arquivos_filtrados if a['operacao'] != 'N/D']))))
        with col_g3:
            # Filtra as datas disponíveis com base no modelo e operação selecionados
            datas_disponiveis_grafico = sorted(list(set([
                a['data_f'] for a in arquivos_filtrados
                if a['modelo'] == modelo_grafico and a['operacao'] == operacao_grafico
            ])))
            data_grafico = st.selectbox("Data para Gráfico", datas_disponiveis_grafico)

        # Encontra o arquivo correspondente aos filtros do gráfico
        arquivo_para_grafico = next((
            a for a in arquivos_filtrados
            if a['modelo'] == modelo_grafico and a['operacao'] == operacao_grafico and a['data_f'] == data_grafico
        ), None)

        # AQUI É ONDE A INDENTAÇÃO FOI CORRIGIDA
        if arquivo_para_grafico: # A indentação deste 'if' foi ajustada para estar no nível correto
            df_grafico = carregar_csv(arquivo_para_grafico['caminho'])

            if not df_grafico.empty and 'datetime' in df_grafico.columns:
                # Identifica colunas numéricas para o gráfico
                colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()
                # Remove colunas que não fazem sentido para plotar diretamente como 'datetime'
                colunas_numericas = [col for col in colunas_numericas if col not in ['ano', 'mes']] # Exclui ano e mes se existirem como numéricos

                if colunas_numericas:
                    st.markdown("---")
                    st.markdown("#### Selecione as variáveis para o gráfico:")
                    variaveis_selecionadas = st.multiselect(
                        "Variáveis",
                        options=colunas_numericas,
                        default=colunas_numericas[:3] # Seleciona as 3 primeiras por padrão
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