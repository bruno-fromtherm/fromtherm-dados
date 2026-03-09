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
    # Ou: historico_L1_YYYYMMDD_HHMM_MODELO.csv (se OP/OPE for opcional)
    # Ou: historico_L1_YYYYMMDD_HHMM_OPX.csv (se MODELO for opcional)
    # Vamos focar no padrão mais comum e ser flexíveis.
    # Adicionado (?:OP|OPE)? para tornar OP/OPE opcional e capturar ambos.
    # Adicionado (?:_([A-Z0-9_]+))? para tornar o modelo opcional e capturar qualquer coisa.
    # O grupo para a operação agora é mais flexível, capturando 'OP' ou 'OPE' seguido de dígitos.
    # O grupo para o modelo agora é mais flexível, capturando qualquer sequência de letras, números e underscores.
    # O regex foi ajustado para ser mais permissivo com a parte da operação e do modelo.
    # Ele tenta capturar o máximo possível, mas sem ser excessivamente ganancioso.
    # O objetivo é que ele capture 'OP999' ou 'OPE779' e 'FTI378L_BR' ou 'FTA987BR'
    # Padrão: historico_L1_YYYYMMDD_HHMM_OP[0-9]+_MODELO.csv
    # Ou: historico_L1_YYYYMMDD_HHMM_OPE[0-9]+_MODELO.csv
    # Ou: historico_L1_YYYYMMDD_HHMM_MODELO.csv (se não tiver OP/OPE)
    # Ou: historico_L1_YYYYMMDD_HHMM_OP[0-9]+.csv (se não tiver MODELO)

    # Novo regex mais flexível:
    # Captura YYYYMMDD, HHMM, e tenta capturar OP/OPE + dígitos, e depois o modelo.
    # O grupo para OP/OPE e o grupo para o modelo são opcionais.
    # A ordem é importante: data, hora, (operação opcional), (modelo opcional)
    # Ex: historico_L1_20260306_0718_OP999_FTI378L_BR.csv
    # Ex: historico_L1_20260307_1704_OPE779_FT55DBR.csv
    # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Ex: historico_L1_20260307_TESTE_NOVO.csv (este não será capturado completamente, mas não deve quebrar)

    # Regex final ajustado para ser o mais flexível possível com as partes variáveis
    # Ele tenta capturar o que puder e deixa o resto como N/D
    # (?:OP|OPE)?(\d+)?: tenta capturar "OP" ou "OPE" seguido de dígitos, tornando tudo opcional.
    # ([A-Z0-9_.-]+)?: tenta capturar o modelo, que pode ter letras, números, underscores, pontos e hífens.
    # Este regex é mais permissivo e tenta extrair o máximo possível.
    regex_padrao = re.compile(r"historico_L1_(\d{8})_(\d{4})(?:_(OP|OPE)(\d+))?(?:_([A-Z0-9_.-]+))?\.csv", re.IGNORECASE)


    for f_path in arquivos_encontrados:
        f_name = os.path.basename(f_path)
        match = regex_padrao.match(f_name)

        if match:
            data_str, hora_str = match.group(1), match.group(2)
            op_prefix = match.group(3) if match.group(3) else ""
            op_num = match.group(4) if match.group(4) else ""
            operacao = f"{op_prefix}{op_num}" if op_prefix and op_num else "N/D"
            modelo = match.group(5) if match.group(5) else "N/D"

            try:
                data_hora_obj = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")
                todos_arquivos.append({
                    'path': f_path,
                    'nome_arquivo': f_name,
                    'data_hora_obj': data_hora_obj,
                    'data_f': data_hora_obj.strftime("%d/%m/%Y"),
                    'hora_f': data_hora_obj.strftime("%H:%M"),
                    'ano': data_hora_obj.year,
                    'mes': data_hora_obj.month,
                    'modelo': modelo,
                    'operacao': operacao
                })
            except ValueError:
                st.warning(f"Nome de arquivo CSV inválido (formato de data/hora): {f_name}. Ignorando.")
        else:
            st.warning(f"Nome de arquivo CSV inválido: {f_name}. Não segue o padrão esperado. Ignorando.")
            # Para arquivos que não seguem o padrão, ainda podemos adicioná-los com N/D para que apareçam na lista
            # Mas não terão metadados para filtros.
            # No entanto, para evitar quebrar os filtros, é melhor ignorá-los completamente se não tiverem metadados.
            # O warning já informa o usuário.
            pass # Manter pass para ignorar arquivos que não batem com o regex

    # Ordenar do mais recente para o mais antigo
    todos_arquivos.sort(key=lambda x: x['data_hora_obj'], reverse=True)
    return todos_arquivos

@st.cache_data(ttl=3600) # Cache por 1 hora
def carregar_csv(caminho_arquivo):
    """
    Carrega um arquivo CSV, lida com o cabeçalho misto (vírgula/pipe),
    limpa nomes de colunas e converte tipos numéricos.
    """
    try:
        # Tenta ler o arquivo como texto para inspecionar o cabeçalho
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        # Encontra a linha do cabeçalho (geralmente a primeira que não é vazia e não é a linha de separação)
        header_line = None
        data_start_line = 0
        for i, line in enumerate(linhas):
            if line.strip() and not line.startswith('|---'):
                header_line = line.strip()
                data_start_line = i + 1 # Dados começam após o cabeçalho
                # Se a próxima linha for a de separação, pular mais uma
                if i + 1 < len(linhas) and linhas[i+1].startswith('|---'):
                    data_start_line = i + 2
                break

        if not header_line:
            st.error(f"Não foi possível encontrar o cabeçalho no arquivo: {caminho_arquivo}")
            return pd.DataFrame()

        # Limpa o cabeçalho: remove aspas, espaços extras e separa por vírgula ou pipe
        # Prioriza vírgula se houver, senão pipe
        if ',' in header_line:
            col_names = [col.strip().strip('"') for col in header_line.split(',')]
        elif '|' in header_line:
            col_names = [col.strip().strip('"') for col in header_line.split('|') if col.strip()]
        else:
            st.error(f"Separador de cabeçalho desconhecido no arquivo: {caminho_arquivo}")
            return pd.DataFrame()

        # Remove colunas vazias que podem surgir de separadores extras no início/fim
        col_names = [name for name in col_names if name]

        # Lê o restante do arquivo, pulando as linhas até os dados
        df = pd.read_csv(
            caminho_arquivo,
            sep='|', # O separador dos dados é pipe
            skipinitialspace=True,
            skiprows=data_start_line, # Pula as linhas até onde os dados realmente começam
            header=None, # Não há cabeçalho no pd.read_csv, pois já o extraímos
            names=col_names, # Usa os nomes de colunas que extraímos
            engine='python' # 'python' engine é mais flexível para skiprows e sep
        )

        # Remove a primeira e última coluna se estiverem vazias (comum com sep='|')
        if not df.empty:
            if df.iloc[:, 0].isnull().all():
                df = df.iloc[:, 1:]
            if not df.empty and df.iloc[:, -1].isnull().all():
                df = df.iloc[:, :-1]

        # Limpa os nomes das colunas novamente para garantir consistência
        df.columns = [col.strip().lower().replace(' ', '_').replace('-', '_').replace('.', '') for col in df.columns]

        # Converte colunas numéricas, tratando erros
        for col in df.columns:
            # Tenta converter para numérico, se falhar, mantém como string
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Remove colunas que são completamente NaN após a conversão (se não eram numéricas)
        df = df.dropna(axis=1, how='all')

        # Cria a coluna 'datetime' combinando 'date' e 'time'
        if 'date' in df.columns and 'time' in df.columns:
            # Garante que 'date' e 'time' são strings antes de combinar
            df['date'] = df['date'].astype(str)
            df['time'] = df['time'].astype(str)
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], errors='coerce', format='%Y-%m-%d %H:%M:%S')
            # Remove linhas onde a conversão de datetime falhou
            df = df.dropna(subset=['datetime'])
        else:
            st.warning(f"Colunas 'date' ou 'time' não encontradas no arquivo {caminho_arquivo}. Gráficos podem não funcionar corretamente.")
            # Se não tiver datetime, cria uma coluna de índice para o gráfico
            df['datetime'] = range(len(df))

        return df

    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo CSV '{caminho_arquivo}': {e}")
        return pd.DataFrame()

# -------------------------------------------------
# 4. LAYOUT DO DASHBOARD
# -------------------------------------------------

# Carregar todos os arquivos disponíveis
todos_arquivos = buscar_arquivos()

# 4.1. BARRA LATERAL
with st.sidebar:
    st.image("https://i.imgur.com/your_fromtherm_logo.png", use_column_width=True) # Substitua pela URL da sua logo
    st.markdown("<h1 class='main-header' style='font-size: 22px; margin-top: 20px;'>Filtros de Busca</h1>", unsafe_allow_html=True)

    # Coletar opções únicas para os filtros
    modelos_unicos = sorted(list(set([a['modelo'] for a in todos_arquivos if a['modelo'] != 'N/D'])))
    anos_unicos = sorted(list(set([a['ano'] for a in todos_arquivos if a['ano'] != 'N/D'])), reverse=True)
    meses_unicos = sorted(list(set([a['mes'] for a in todos_arquivos if a['mes'] != 'N/D'])))
    datas_unicas = sorted(list(set([a['data_f'] for a in todos_arquivos if a['data_f'] != 'N/D'])), reverse=True)
    operacoes_unicas = sorted(list(set([a['operacao'] for a in todos_arquivos if a['operacao'] != 'N/D'])))

    # Adicionar "Todos" como opção padrão
    selected_modelo = st.selectbox("Modelo", ["Todos"] + modelos_unicos)
    selected_ano = st.selectbox("Ano", ["Todos"] + anos_unicos)
    selected_mes = st.selectbox("Mês", ["Todos"] + meses_unicos, format_func=lambda x: f"{datetime(1, x, 1).strftime('%B').capitalize()}" if x != "Todos" else x)
    selected_data = st.selectbox("Data", ["Todos"] + datas_unicas)
    selected_operacao = st.selectbox("Operação", ["Todos"] + operacoes_unicas)

    # Filtrar arquivos com base nas seleções
    arquivos_filtrados = todos_arquivos
    if selected_modelo != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['modelo'] == selected_modelo]
    if selected_ano != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['ano'] == selected_ano]
    if selected_mes != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['mes'] == selected_mes]
    if selected_data != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['data_f'] == selected_data]
    if selected_operacao != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a['operacao'] == selected_operacao]

# 4.2. ÁREA PRINCIPAL
st.markdown("<h1 class='main-header'>Monitoramento de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

# Cards de Última Leitura Registrada
st.markdown("### Última Leitura Registrada")
if arquivos_filtrados:
    ultima_leitura_arquivo = arquivos_filtrados[0]
    df_ultima_leitura = carregar_csv(ultima_leitura_arquivo['path'])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1]

        # Informações do Teste para o operador
        st.info(f"""
            **Informações do Teste:**
            - **Modelo:** {ultima_leitura_arquivo['modelo']}
            - **Operação:** {ultima_leitura_arquivo['operacao']}
            - **Data:** {ultima_leitura_arquivo['data_f']}
            - **Hora:** {ultima_leitura_arquivo['hora_f']}
        """)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if 'ambiente' in ultima_linha and pd.notna(ultima_linha['ambiente']):
                mostra_valor("T-Ambiente", f"{ultima_linha['ambiente']:.2f}", "°C", "bi-thermometer-half")
            else:
                mostra_valor("T-Ambiente", "N/D", "°C", "bi-thermometer-half")
        with col2:
            if 'entrada' in ultima_linha and pd.notna(ultima_linha['entrada']):
                mostra_valor("T-Entrada", f"{ultima_linha['entrada']:.2f}", "°C", "bi-thermometer-high")
            else:
                mostra_valor("T-Entrada", "N/D", "°C", "bi-thermometer-high")
        with col3:
            if 'saida' in ultima_linha and pd.notna(ultima_linha['saida']):
                mostra_valor("T-Saída", f"{ultima_linha['saida']:.2f}", "°C", "bi-thermometer-low")
            else:
                mostra_valor("T-Saída", "N/D", "°C", "bi-thermometer-low")
        with col4:
            if 'vazao' in ultima_linha and pd.notna(ultima_linha['vazao']):
                mostra_valor("Vazão", f"{ultima_linha['vazao']:.2f}", "L/min", "bi-droplet-half")
            else:
                mostra_valor("Vazão", "N/D", "L/min", "bi-droplet-half")
    else:
        st.warning("Não foi possível carregar os dados da última leitura do arquivo selecionado.")
else:
    st.info("Nenhum histórico disponível com os filtros aplicados.")

st.markdown("---")

# Abas para Históricos e Gráficos
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Históricos Disponíveis")
    if arquivos_filtrados:
        for i, arquivo_info in enumerate(arquivos_filtrados):
            expander_title = f"**{arquivo_info['modelo']}** - Operação: **{arquivo_info['operacao']}** - Data: {arquivo_info['data_f']} {arquivo_info['hora_f']}"
            with st.expander(expander_title):
                st.write(f"Caminho do arquivo: `{arquivo_info['path']}`")
                df_historico = carregar_csv(arquivo_info['path'])
                if not df_historico.empty:
                    st.dataframe(df_historico, use_container_width=True)

                    # Botões de download
                    col_dl1, col_dl2 = st.columns(2)
                    nome_base_download = f"Maquina_{arquivo_info['modelo']}_OP{arquivo_info['operacao']}_{arquivo_info['data_f'].replace('/', '-')}_{arquivo_info['hora_f'].replace(':', 'hs')}"

                    with col_dl1:
                        # Download PDF
                        pdf_buffer = BytesIO()
                        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                        styles = getSampleStyleSheets()

                        # Estilo para o título
                        title_style = ParagraphStyle(
                            'TitleStyle',
                            parent=styles['h1'],
                            fontSize=16,
                            leading=20,
                            alignment=1, # Center
                            spaceAfter=12,
                            textColor=colors.HexColor("#003366")
                        )

                        # Estilo para o cabeçalho da tabela
                        table_header_style = ParagraphStyle(
                            'TableHeaderStyle',
                            parent=styles['Normal'],
                            fontSize=8,
                            leading=10,
                            alignment=1, # Center
                            textColor=colors.white,
                            fontName='Helvetica-Bold'
                        )

                        # Estilo para o conteúdo da tabela
                        table_cell_style = ParagraphStyle(
                            'TableCellStyle',
                            parent=styles['Normal'],
                            fontSize=7,
                            leading=9,
                            alignment=1, # Center
                            textColor=colors.black
                        )

                        elements = []
                        elements.append(Paragraph(f"Relatório de Teste - {arquivo_info['modelo']}", title_style))
                        elements.append(Paragraph(f"Operação: {arquivo_info['operacao']} | Data: {arquivo_info['data_f']} | Hora: {arquivo_info['hora_f']}", styles['h3']))
                        elements.append(Spacer(1, 0.2 * inch))

                        # Preparar dados para a tabela PDF
                        data_pdf = [
                            [Paragraph(col, table_header_style) for col in df_historico.columns]
                        ] + [
                            [Paragraph(str(cell), table_cell_style) for cell in row]
                            for row in df_historico.values
                        ]

                        table = Table(data_pdf)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                        ]))
                        elements.append(table)
                        doc.build(pdf_buffer)
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"{nome_base_download}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{i}"
                        )

                    with col_dl2:
                        # Download Excel
                        excel_buffer = BytesIO()
                        df_historico.to_excel(excel_buffer, index=False, engine='xlsxwriter')
                        st.download_button(
                            label="Baixar como Excel",
                            data=excel_buffer.getvalue(),
                            file_name=f"{nome_base_download}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_excel_{i}"
                        )
                else:
                    st.warning("Não foi possível carregar os dados deste histórico.")
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