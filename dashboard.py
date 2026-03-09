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
# Caminho para a pasta de dados (AJUSTADO PARA O CAMINHO COMPLETO NO REPOSITÓRIO)
# Certifique-se que esta pasta existe no seu repositório GitHub
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog" 

@st.cache_data(ttl=3600) # Cache para não recarregar os arquivos toda hora
def buscar_arquivos():
    arquivos_encontrados = []

    # Regex ULTRA-ROBUSTO para capturar as partes
    # - `historico_L1_`: prefixo fixo
    # - `(\d{4})(\d{2})(\d{2})`: Ano (YYYY), Mês (MM), Dia (DD)
    # - `_(\d{4})`: Hora (HHMM)
    # - `_(OP|OPE)?(\w+)`: Operação (OP/OPE opcional) e o valor da operação (ex: 987, 999, 779, 8888)
    # - `_(\w+)`: Modelo (ex: FTA987BR, FTI378L_BR, FT55DBR, TESTE_NOVO)
    # - `\.csv`: extensão
    # O `?` torna a parte `(OP|OPE)` opcional, e `(\w+)` captura qualquer sequência de letras/números para operação e modelo.
    # Isso deve cobrir a maioria das variações, incluindo `TESTE_NOVO` (onde OP/OPE e o número da operação podem ser None).
    regex_padrao = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(?:OP|OPE)?(\w+)_(\w+)\.csv")

    # Adicionando um regex para o caso de TESTE_NOVO, que não tem OP/OPE e modelo no mesmo formato
    regex_teste_novo = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_TESTE_NOVO\.csv")

    if not os.path.exists(DATA_PATH):
        st.error(f"Erro: A pasta de dados '{DATA_PATH}' não foi encontrada no repositório.")
        return []

    for root, _, files in os.walk(DATA_PATH):
        for filename in files:
            if filename.endswith(".csv"):
                match = regex_padrao.match(filename)
                if match:
                    try:
                        ano, mes, dia, hora, operacao_val, modelo = match.groups()
                        data_str = f"{ano}/{mes}/{dia}"
                        hora_str = f"{hora[:2]}:{hora[2:]}"

                        # Formata a operação e modelo
                        operacao = f"OP{operacao_val}" if operacao_val else "N/D"
                        modelo_formatado = modelo.replace('_BR', '').replace('_', ' ') # Ajusta o modelo para exibição

                        arquivos_encontrados.append({
                            'nome_arquivo': filename,
                            'caminho_completo': os.path.join(root, filename),
                            'data': datetime.strptime(data_str, "%Y/%m/%d").date(),
                            'data_f': data_str,
                            'hora': hora_str,
                            'ano': int(ano),
                            'mes': int(mes),
                            'operacao': operacao,
                            'modelo': modelo_formatado
                        })
                    except Exception as e:
                        st.warning(f"Nome de arquivo CSV inválido: {filename}. Não foi possível extrair metadados. Ignorando. Erro: {e}")
                else:
                    # Tenta o regex para TESTE_NOVO se o padrão principal falhar
                    match_teste = regex_teste_novo.match(filename)
                    if match_teste:
                        try:
                            ano, mes, dia, hora = match_teste.groups()
                            data_str = f"{ano}/{mes}/{dia}"
                            hora_str = f"{hora[:2]}:{hora[2:]}"

                            arquivos_encontrados.append({
                                'nome_arquivo': filename,
                                'caminho_completo': os.path.join(root, filename),
                                'data': datetime.strptime(data_str, "%Y/%m/%d").date(),
                                'data_f': data_str,
                                'hora': hora_str,
                                'ano': int(ano),
                                'mes': int(mes),
                                'operacao': "TESTE_NOVO", # Operação padrão para este tipo
                                'modelo': "TESTE_NOVO"    # Modelo padrão para este tipo
                            })
                        except Exception as e:
                            st.warning(f"Nome de arquivo CSV inválido: {filename}. Não foi possível extrair metadados. Ignorando. Erro: {e}")
                    else:
                        st.warning(f"Nome de arquivo CSV inválido: {filename}. Não segue o padrão esperado. Ignorando.")

    # Ordena os arquivos do mais recente para o mais antigo
    arquivos_encontrados.sort(key=lambda x: (x['data'], x['hora']), reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=3600) # Cache para não recarregar o CSV toda hora
def carregar_csv(caminho_completo):
    try:
        # Tenta ler com o separador '|' e o quotechar padrão (")
        df = pd.read_csv(caminho_completo, sep='|', skiprows=[1], skipinitialspace=True, encoding='utf-8')
    except pd.errors.ParserError:
        # Se falhar, tenta novamente sem esperar nenhum quotechar
        df = pd.read_csv(caminho_completo, sep='|', skiprows=[1], skipinitialspace=True, encoding='utf-8', quotechar='\0')

    # Remove colunas vazias que podem surgir do separador '|' no início/fim
    df = df.dropna(axis=1, how='all')

    # Limpa nomes das colunas (remove espaços em branco extras)
    df.columns = df.columns.str.strip()

    # Converte colunas numéricas, tratando vírgulas e zeros à esquerda
    colunas_numericas = ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']
    for col in colunas_numericas:
        if col in df.columns:
            # Substitui vírgula por ponto e tenta converter para numérico, preenchendo erros com 0
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Combina 'Date' e 'Time' em uma única coluna 'datetime'
    if 'Date' in df.columns and 'Time' in df.columns:
        df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y/%m/%d %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['datetime']) # Remove linhas com datetime inválido

    return df

# -------------------------------------------------
# 4. CARREGAMENTO E FILTRAGEM DE DADOS
# -------------------------------------------------
todos_arquivos = buscar_arquivos()

# Extrai opções únicas para os filtros, garantindo que não haja 'N/D' ou vazios
modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D'])))
operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D'])))
anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos if a['ano'] != 'N/D'])))
meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos if a['mes'] != 'N/D'])))
datas_unicas = sorted(list(set([a['data'] for a in todos_arquivos if a['data'] != 'N/D'])), reverse=True) # Datas como objetos date

# -------------------------------------------------
# 5. BARRA LATERAL (FILTROS)
# -------------------------------------------------
st.sidebar.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
st.sidebar.markdown("<h2 style='text-align: center; color: #003366;'>Filtros de Busca</h2>", unsafe_allow_html=True)

filtro_modelo = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
filtro_operacao = st.sidebar.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
filtro_ano = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
filtro_mes = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos, format_func=lambda x: datetime(1, x, 1).strftime("%B") if x != "Todos" else "Todos")
filtro_data = st.sidebar.selectbox("Data", ["Todos"] + datas_unicas, format_func=lambda x: x.strftime("%d/%m/%Y") if x != "Todos" else "Todos")

# Aplica os filtros
arquivos_filtrados = todos_arquivos
if filtro_modelo != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == filtro_modelo]
if filtro_operacao != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == filtro_operacao]
if filtro_ano != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == filtro_ano]
if filtro_mes != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == filtro_mes]
if filtro_data != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a['data'] == filtro_data]

# -------------------------------------------------
# 6. CONTEÚDO PRINCIPAL
# -------------------------------------------------
st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("### Última Leitura Registrada")

    if arquivos_filtrados:
        ultimo_arquivo_info = arquivos_filtrados[0]
        df_ultima_leitura = carregar_csv(ultimo_arquivo_info['caminho_completo'])

        if not df_ultima_leitura.empty:
            ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha

            st.markdown(f"""
                <div style="background-color: #e0e7eb; padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; color: #003366;">
                    Modelo: {ultimo_arquivo_info['modelo']} | Operação: {ultimo_arquivo_info['operacao']} | Data: {ultimo_arquivo_info['data_f']} | Hora: {ultimo_arquivo_info['hora']}
                </div>
            """, unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            col5, col6, col7, col8 = st.columns(4)
            col9, col10, col11 = st.columns(3) # Ajuste para 11 itens

            with col1: mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
            with col2: mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-arrow-down-circle")
            with col3: mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-arrow-up-circle")
            with col4: mostra_valor("DIF", f"{ultima_linha['dif']:.2f}", "°C", "bi-arrows-expand")
            with col5: mostra_valor("Tensão", f"{ultima_linha['tensao']:.2f}", "V", "bi-lightning-charge")
            with col6: mostra_valor("Corrente", f"{ultima_linha['corrente']:.2f}", "A", "bi-lightning")
            with col7: mostra_valor("kcal/h", f"{ultima_linha['kacl/h']:.2f}", "", "bi-fire")
            with col8: mostra_valor("Vazão", f"{ultima_linha['vazao']:.2f}", "L/min", "bi-droplet")
            with col9: mostra_valor("kW Aquecimento", f"{ultima_linha['kw aquecimento']:.2f}", "", "bi-sun")
            with col10: mostra_valor("kW Consumo", f"{ultima_linha['kw consumo']:.2f}", "", "bi-power")
            with col11: mostra_valor("COP", f"{ultima_linha['cop']:.2f}", "", "bi-graph-up")
        else:
            st.info("Nenhum dado válido encontrado no último histórico para mostrar a última leitura.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")

    st.markdown("### Históricos Disponíveis")
    if arquivos_filtrados:
        for i, arquivo_info in enumerate(arquivos_filtrados):
            expander = st.expander(f"**{arquivo_info['modelo']}** - Operação: **{arquivo_info['operacao']}** - Data: **{arquivo_info['data_f']}** - Hora: **{arquivo_info['hora']}**")
            with expander:
                df_exibir = carregar_csv(arquivo_info['caminho_completo'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir.drop(columns=['datetime'], errors='ignore'), use_container_width=True) # Remove datetime para exibição

                    # Botões de download
                    col_dl1, col_dl2 = st.columns(2)

                    # Download PDF
                    nome_pdf = f"Maquina_{arquivo_info['modelo'].replace(' ', '_')}_OP{arquivo_info['operacao'].replace('OP', '')}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora'].replace(':', 'hs')}.pdf"
                    pdf_buffer = BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                    styles = getSampleStyleSheet()

                    # Estilo para o título
                    title_style = ParagraphStyle(
                        'TitleStyle',
                        parent=styles['h1'],
                        fontSize=16,
                        leading=20,
                        alignment=1, # Center
                        spaceAfter=12,
                        textColor=colors.HexColor('#003366')
                    )

                    # Estilo para o cabeçalho da tabela
                    header_style = ParagraphStyle(
                        'HeaderStyle',
                        parent=styles['Normal'],
                        fontSize=8,
                        alignment=1, # Center
                        textColor=colors.white,
                        fontName='Helvetica-Bold'
                    )

                    # Estilo para o corpo da tabela
                    body_style = ParagraphStyle(
                        'BodyStyle',
                        parent=styles['Normal'],
                        fontSize=7,
                        alignment=1, # Center
                        textColor=colors.black
                    )

                    story = []
                    story.append(Paragraph(f"Relatório de Teste - Máquina {arquivo_info['modelo']}", title_style))
                    story.append(Paragraph(f"Operação: {arquivo_info['operacao']} | Data: {arquivo_info['data_f']} | Hora: {arquivo_info['hora']}", styles['h3']))
                    story.append(Spacer(1, 0.2 * inch))

                    # Preparar dados para a tabela PDF
                    data_for_pdf = [
                        [Paragraph(col, header_style) for col in df_exibir.drop(columns=['datetime'], errors='ignore').columns]
                    ] + [
                        [Paragraph(str(cell), body_style) for cell in row]
                        for row in df_exibir.drop(columns=['datetime'], errors='ignore').values
                    ]

                    table = Table(data_for_pdf)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ]))
                    story.append(table)
                    doc.build(story)

                    with col_dl1:
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=nome_pdf,
                            mime="application/pdf",
                            use_container_width=True
                        )

                    # Download Excel
                    nome_excel = f"Maquina_{arquivo_info['modelo'].replace(' ', '_')}_OP{arquivo_info['operacao'].replace('OP', '')}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora'].replace(':', 'hs')}.xlsx"
                    excel_buffer = BytesIO()
                    df_exibir.drop(columns=['datetime'], errors='ignore').to_excel(excel_buffer, index=False, engine='openpyxl')
                    with col_dl2:
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_buffer.getvalue(),
                            file_name=nome_excel,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados do arquivo {arquivo_info['nome_arquivo']}.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.markdown("### Crie Seu Gráfico Personalizado")

    if arquivos_filtrados:
        # Seleção do arquivo para o gráfico
        opcoes_grafico = [
            f"{a['modelo']} - Operação: {a['operacao']} - Data: {a['data_f']} - Hora: {a['hora']}"
            for a in arquivos_filtrados
        ]
        selecao_grafico = st.selectbox("Selecione um Histórico para o Gráfico", opcoes_grafico)

        arquivo_para_grafico = next((a for a in arquivos_filtrados if f"{a['modelo']} - Operação: {a['operacao']} - Data: {a['data_f']} - Hora: {a['hora']}" == selecao_grafico), None)

        if arquivo_para_grafico:
            df_grafico = carregar_csv(arquivo_para_grafico['caminho_completo'])

            if not df_grafico.empty and 'datetime' in df_grafico.columns:
                # Identifica colunas numéricas para o gráfico
                colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()

                # Remove colunas que não fazem sentido para o gráfico de linha (ex: IDs, se houver)
                colunas_numericas = [col for col in colunas_numericas if col not in ['ano', 'mes']] # Exemplo, ajuste conforme necessário

                if colunas_numericas:
                    variaveis_selecionadas = st.multiselect(
                        "Selecione as variáveis para o gráfico",
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