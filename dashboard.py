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
# O Streamlit Cloud monta o repositório na raiz, então o caminho é relativo a ela.
# DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog" # Caminho anterior
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog" # Confirmado o caminho correto

@st.cache_data(ttl=3600) # Cache para evitar reprocessar arquivos a cada interação
def buscar_arquivos():
    # Regex para extrair informações do nome do arquivo
    # Mais flexível para OP/OPE e para o modelo (pode ter letras, números, _ e BR no final)
    # Ex: historico_L1_20260306_0718_OP999_FTI378L_BR.csv
    # Ex: historico_L1_20260307_1704_OPE779_FT55DBR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (este será ignorado pelo regex, o que é esperado)

    # Regex mais robusto:
    # - Captura a data (YYYYMMDD)
    # - Captura a hora (HHMM)
    # - Captura a operação (OP/OPE seguido de 3 a 4 dígitos ou letras/dígitos)
    # - Captura o modelo (FT seguido de letras/dígitos/underline e opcionalmente BR)
    # pattern = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)([A-Z0-9]{3,4})_(FT[A-Z0-9_]+BR)\.csv")
    # Novo regex ainda mais flexível para a operação e modelo
    pattern = re.compile(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP|OPE)?([A-Z0-9_]+)_(FT[A-Z0-9_]+BR)\.csv")


    arquivos_encontrados = []
    caminho_completo = os.path.join(os.getcwd(), DATA_PATH) # Garante que o caminho é absoluto

    if not os.path.exists(caminho_completo):
        st.error(f"Erro: O caminho de dados '{caminho_completo}' não foi encontrado. Verifique a estrutura do repositório.")
        return []

    for root, _, files in os.walk(caminho_completo):
        for filename in files:
            if filename.endswith(".csv"):
                match = pattern.match(filename)
                if match:
                    try:
                        ano, mes, dia, hora_str, op_prefix, operacao_num, modelo = match.groups()

                        # Reconstruir operacao se op_prefix for None (para casos como OP987)
                        operacao = f"{op_prefix or ''}{operacao_num}" if op_prefix else operacao_num

                        data_str = f"{ano}/{mes}/{dia}"
                        data_obj = datetime.strptime(data_str, "%Y/%m/%d").date()

                        arquivos_encontrados.append({
                            'filename': filename,
                            'filepath': os.path.join(root, filename),
                            'data_obj': data_obj,
                            'data_f': data_obj.strftime("%d/%m/%Y"),
                            'hora': f"{hora_str[:2]}:{hora_str[2:]}",
                            'ano': int(ano),
                            'mes': int(mes),
                            'operacao': operacao,
                            'modelo': modelo
                        })
                    except Exception as e:
                        st.warning(f"Nome de arquivo CSV inválido: {filename}. Erro ao extrair metadados: {e}. Ignorando.")
                else:
                    st.warning(f"Nome de arquivo CSV inválido: {filename}. Não segue o padrão esperado. Ignorando.")

    # Ordenar do mais recente para o mais antigo
    arquivos_encontrados.sort(key=lambda x: (x['data_obj'], x['hora']), reverse=True)
    return arquivos_encontrados

@st.cache_data(ttl=3600) # Cache para o DataFrame
def carregar_csv(filepath):
    try:
        # Tenta ler com o separador '|' e sem quotechar (para evitar problemas com aspas)
        df = pd.read_csv(filepath, sep='|', skiprows=[1], engine='python', quotechar='\0') # quotechar='\0' desabilita o tratamento de aspas

        # Limpar nomes das colunas: remover espaços em branco, caracteres especiais e o pipe extra
        df.columns = df.columns.str.strip().str.replace(r'[^a-zA-Z0-9_]', '', regex=True).str.lower()

        # Remover colunas vazias que podem surgir do pipe inicial/final
        df = df.loc[:, df.columns.notna()] # Remove colunas com nome NaN
        df = df.loc[:, (df != '').any(axis=0)] # Remove colunas que são completamente vazias (strings vazias)

        # Renomear colunas para padronização, se necessário
        # Exemplo: 'date' para 'Date', 'time' para 'Time'
        # Certifique-se de que os nomes limpos correspondem aos esperados
        df = df.rename(columns={
            'date': 'Date',
            'time': 'Time',
            'ambiente': 'ambiente',
            'entrada': 'entrada',
            'saida': 'saida',
            'dif': 'dif',
            'tensao': 'tensao',
            'corrente': 'corrente',
            'kaclh': 'kacl/h', # Ajuste para kacl/h se o nome limpo for 'kaclh'
            'vazao': 'vazao',
            'kwaquecimento': 'kw aquecimento', # Ajuste para kw aquecimento
            'kwconsumo': 'kw consumo', # Ajuste para kw consumo
            'cop': 'cop'
        })

        # Converter colunas numéricas, tratando vírgulas e erros
        colunas_numericas = ['ambiente', 'entrada', 'saida', 'dif', 'tensao', 'corrente', 'kacl/h', 'vazao', 'kw aquecimento', 'kw consumo', 'cop']
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # Coerce errors to NaN, then fill NaN with 0
            else:
                st.warning(f"Coluna '{col}' não encontrada no arquivo {os.path.basename(filepath)}. Verifique o cabeçalho do CSV.")

        # Combinar 'Date' e 'Time' em uma única coluna 'datetime'
        if 'Date' in df.columns and 'Time' in df.columns:
            df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y/%m/%d %H:%M:%S')
            df = df.dropna(subset=['datetime']) # Remove linhas onde a conversão de data/hora falhou
        else:
            st.warning(f"Colunas 'Date' ou 'Time' não encontradas no arquivo {os.path.basename(filepath)}. Gráficos de tempo podem ser afetados.")

        return df
    except pd.errors.ParserError as e:
        st.error(f"Erro de parsing no CSV '{os.path.basename(filepath)}': {e}. Verifique o formato do arquivo.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(filepath)}': {e}")
        return pd.DataFrame()

# -------------------------------------------------
# 4. LAYOUT DO STREAMLIT
# -------------------------------------------------

# Sidebar
st.sidebar.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
st.sidebar.markdown("<h1 style='text-align: center; color: #003366;'>Filtros de Busca</h1>", unsafe_allow_html=True)

todos_arquivos = buscar_arquivos()

# Extrair opções únicas para os filtros, tratando casos de listas vazias
modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if 'modelo' in a and a['modelo'] != 'N/D']))) if todos_arquivos else []
operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if 'operacao' in a and a['operacao'] != 'N/D']))) if todos_arquivos else []
anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos if 'ano' in a and a['ano'] != 'N/D']))) if todos_arquivos else []
meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos if 'mes' in a and a['mes'] != 'N/D']))) if todos_arquivos else []
datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos if 'data_f' in a and a['data_f'] != 'N/D']))) if todos_arquivos else []


# Adicionar "Todos" como opção nos filtros
modelo_selecionado = st.sidebar.selectbox("Modelo", ["Todos"] + modelos_unicos)
operacao_selecionada = st.sidebar.selectbox("Operação (OP)", ["Todos"] + operacoes_unicas)
ano_selecionado = st.sidebar.selectbox("Ano", ["Todos"] + anos_unicos)
mes_selecionado = st.sidebar.selectbox("Mês", ["Todos"] + meses_unicos)
data_selecionada = st.sidebar.selectbox("Data", ["Todos"] + datas_unicas)

# Filtrar arquivos com base nas seleções
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

# Main content
st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("### Última Leitura Registrada")

    ultima_leitura_df = pd.DataFrame()
    if arquivos_filtrados:
        # Pega o arquivo mais recente da lista filtrada
        arquivo_mais_recente = arquivos_filtrados[0]
        ultima_leitura_df = carregar_csv(arquivo_mais_recente['filepath'])
        if not ultima_leitura_df.empty:
            ultima_linha = ultima_leitura_df.iloc[-1] # Pega a última linha do DF
        else:
            st.warning("O arquivo mais recente está vazio ou não pôde ser processado.")

    if not ultima_leitura_df.empty:
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
        with col2:
            mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-thermometer-high")
        with col3:
            mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-thermometer-low")
        with col4:
            mostra_valor("T-Dif", f"{ultima_linha['dif']:.2f}", "°C", "bi-arrows-expand")
        with col5:
            mostra_valor("Tensão", f"{ultima_linha['tensao']:.2f}", "V", "bi-lightning-charge")
        with col6:
            mostra_valor("Corrente", f"{ultima_linha['corrente']:.2f}", "A", "bi-lightning")

        col7, col8, col9, col10 = st.columns(4)
        with col7:
            mostra_valor("Kcal/h", f"{ultima_linha['kacl/h']:.2f}", "", "bi-fire")
        with col8:
            mostra_valor("Vazão", f"{ultima_linha['vazao']:.2f}", "L/min", "bi-water")
        with col9:
            mostra_valor("kW Aquecimento", f"{ultima_linha['kw aquecimento']:.2f}", "", "bi-graph-up")
        with col10:
            mostra_valor("kW Consumo", f"{ultima_linha['kw consumo']:.2f}", "", "bi-power")

        # Informações do Teste
        st.markdown("---")
        st.markdown("### Informações do Teste")
        st.markdown(f"""
            - **Modelo da Máquina:** `{arquivo_mais_recente['modelo']}`
            - **Número de Operação:** `{arquivo_mais_recente['operacao']}`
            - **Data do Teste:** `{arquivo_mais_recente['data_f']}`
            - **Ano:** `{arquivo_mais_recente['ano']}`
            - **Hora da Última Leitura:** `{ultima_linha['Time']}`
        """)

    else:
        st.info("Nenhum histórico disponível com os filtros aplicados para mostrar a última leitura.")

    st.markdown("---")
    st.markdown("### Históricos Disponíveis")

    if arquivos_filtrados:
        for arquivo in arquivos_filtrados:
            with st.expander(f"**{arquivo['modelo']} - Operação {arquivo['operacao']} - {arquivo['data_f']} {arquivo['hora']}**"):
                df_historico = carregar_csv(arquivo['filepath'])
                if not df_historico.empty:
                    st.dataframe(df_historico, use_container_width=True)

                    # Botões de Download
                    col_dl1, col_dl2 = st.columns(2)

                    # Nome do arquivo para download
                    nome_base = f"Maquina_{arquivo['modelo']}_OP{arquivo['operacao']}_{arquivo['data_f'].replace('/', '-')}_{arquivo['hora'].replace(':', '')}hs"

                    with col_dl1:
                        # Download PDF
                        buffer_pdf = BytesIO()
                        doc = SimpleDocTemplate(buffer_pdf, pagesize=landscape(A4))
                        styles = getSampleStyleSheet()

                        # Estilo para o título do PDF
                        style_title = ParagraphStyle(
                            'Title',
                            parent=styles['h1'],
                            fontSize=16,
                            leading=20,
                            alignment=1, # Center
                            spaceAfter=12,
                            textColor=colors.HexColor('#003366')
                        )

                        # Estilo para o cabeçalho da tabela
                        style_header = ParagraphStyle(
                            'TableHeader',
                            parent=styles['Normal'],
                            fontSize=8,
                            alignment=1, # Center
                            textColor=colors.white,
                            backColor=colors.HexColor('#003366')
                        )

                        # Estilo para o corpo da tabela
                        style_body = ParagraphStyle(
                            'TableBody',
                            parent=styles['Normal'],
                            fontSize=7,
                            alignment=1, # Center
                            textColor=colors.black
                        )

                        elements = []
                        elements.append(Paragraph(f"Relatório de Teste - {arquivo['modelo']} - Operação {arquivo['operacao']}", style_title))
                        elements.append(Paragraph(f"Data: {arquivo['data_f']} Hora: {arquivo['hora']}", styles['h3']))
                        elements.append(Spacer(1, 0.2 * inch))

                        # Preparar dados para a tabela
                        data = [df_historico.columns.tolist()] + df_historico.values.tolist()

                        # Aplicar estilos ao cabeçalho e corpo da tabela
                        table_data = []
                        table_data.append([Paragraph(col, style_header) for col in data[0]]) # Cabeçalho
                        for row in data[1:]:
                            table_data.append([Paragraph(str(item), style_body) for item in row]) # Corpo

                        table = Table(table_data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
                            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0,0), (-1,0), 12),
                            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                            ('GRID', (0,0), (-1,-1), 1, colors.black)
                        ]))
                        elements.append(table)
                        doc.build(elements)

                        st.download_button(
                            label="Baixar como PDF",
                            data=buffer_pdf.getvalue(),
                            file_name=f"{nome_base}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with col_dl2:
                        # Download Excel
                        buffer_excel = BytesIO()
                        df_historico.to_excel(buffer_excel, index=False, engine='openpyxl')
                        st.download_button(
                            label="Baixar como Excel",
                            data=buffer_excel.getvalue(),
                            file_name=f"{nome_base}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para o histórico {arquivo['filename']}.")
    else:
        st.info("Nenhum histórico disponível com os filtros aplicados.")

with tab2:
    st.markdown("### Crie Seu Gráfico Personalizado")

    if arquivos_filtrados:
        # Seleção do arquivo para o gráfico
        opcoes_grafico = [f"{a['modelo']} - OP {a['operacao']} - {a['data_f']} {a['hora']}" for a in arquivos_filtrados]
        selecao_grafico = st.selectbox("Selecione um histórico para o gráfico", opcoes_grafico)

        arquivo_para_grafico = None
        if selecao_grafico:
            # Encontrar o dicionário do arquivo correspondente
            for a in arquivos_filtrados:
                if f"{a['modelo']} - OP {a['operacao']} - {a['data_f']} {a['hora']}" == selecao_grafico:
                    arquivo_para_grafico = a
                    break

        if arquivo_para_grafico:
            df_grafico = carregar_csv(arquivo_para_grafico['filepath'])

            if not df_grafico.empty and 'datetime' in df_grafico.columns:
                # Identificar colunas numéricas para o gráfico (excluindo 'Date', 'Time', 'datetime')
                colunas_numericas = df_grafico.select_dtypes(include=['number']).columns.tolist()
                colunas_numericas = [col for col in colunas_numericas if col not in ['Date', 'Time']]

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