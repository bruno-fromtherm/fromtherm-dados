import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re # Importar módulo de expressões regulares
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm  # Importar cm para unidades de medida
from io import BytesIO
import plotly.express as px

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm") # Título da aba do navegador

# =========================
#  CSS GLOBAL (correção do "0", cards com animação suave)
# =========================
st.markdown(
    """
    <style>
    /* REMOÇÃO FINAL DO "0" TEIMOSO (mais abrangente e direto) */
    /* Esconde o botão de menu do Streamlit e o ícone de menu */
    button[data-testid="stSidebarNavToggle"],
    .st-emotion-cache-1r6dm1x, /* Seletor específico para o ícone de menu */
    .st-emotion-cache-10q71g7, /* Seletor específico para o container do ícone de menu */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > div:first-child > span,
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > span,
    span[data-testid="stDecoration"],
    summary {
        display: none !important;
    }

    /* Estilo dos cards de métricas */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd; /* Cor padrão da borda */
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd; /* Cor padrão do ícone */
        animation: ft-pulse 1.5s ease-in-out infinite; /* Animação de pulso suave para todos */
    }
    .ft-card-icon.red {
        color: #dc3545; /* Cor vermelha para T-Saída */
    }
    .ft-card-content {
        display: flex;
        flex-direction: column;
    }
    .ft-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #6c757d;
        margin-bottom: 2px;
    }
    .ft-card-value {
        font-size: 20px;
        font-weight: 700;
        color: #343a40;
    }
    .ft-card-value.red {
        color: #dc3545; /* Cor vermelha para T-Saída */
    }

    /* Animação de pulso para os ícones */
    @keyframes ft-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    /* Ajustes para o título principal */
    .st-emotion-cache-10trblm { /* Seletor para o título h1 */
        text-align: center;
        color: #0d6efd;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }

    /* Ajustes para o logo */
    .st-emotion-cache-1v0mbdj { /* Seletor para o container do logo */
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }

    /* Ajustes para o multiselect */
    .stMultiSelect {
        margin-bottom: 15px;
    }
    </style>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    """,
    unsafe_allow_html=True,
)

# =========================
#  FUNÇÕES AUXILIARES
# =========================

# Função para listar arquivos CSV e extrair informações
@st.cache_data(ttl=3600) # Cache para evitar reprocessar a cada execução
def listar_arquivos_csv(pasta_dados="dados"):
    arquivos_info = []
    # Padrão regex para extrair informações do nome do arquivo
    # Ex: historico_L1_FTA987BR_20260308_0939_OP987.csv
    # Grupo 1: Modelo (FTA987BR)
    # Grupo 2: Ano (2026)
    # Grupo 3: Mês (03)
    # Grupo 4: Dia (08)
    # Grupo 5: Hora (0939)
    # Grupo 6: Operação (OP987)
    padrao_nome_arquivo = re.compile(
        r"historico_L\d+_([A-Z0-9]+)_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)\.csv",
        re.IGNORECASE
    )

    for root, _, files in os.walk(pasta_dados):
        for nome_arquivo in files:
            if nome_arquivo.endswith(".csv"):
                match = padrao_nome_arquivo.match(nome_arquivo)
                if match:
                    modelo, ano_str, mes_str, dia_str, hora_str, operacao = match.groups()
                    data_str = f"{ano_str}{mes_str}{dia_str}"

                    try:
                        data_obj = datetime.strptime(data_str, "%Y%m%d").date()
                    except ValueError:
                        data_obj = None # Se a data for inválida, define como None

                    arquivos_info.append({
                        "nome_arquivo": nome_arquivo,
                        "caminho": os.path.join(root, nome_arquivo),
                        "modelo": modelo,
                        "ano": int(ano_str),
                        "mes": int(mes_str),
                        "dia": int(dia_str),
                        "data": data_obj, # Armazena como objeto date
                        "hora": f"{hora_str[:2]}:{hora_str[2:]}",
                        "operacao": operacao,
                        "timestamp": os.path.getmtime(os.path.join(root, nome_arquivo)) # Para ordenar por mais recente
                    })

    # Ordena os arquivos do mais recente para o mais antigo
    arquivos_info.sort(key=lambda x: x["timestamp"], reverse=True)
    return arquivos_info

# Função para carregar e padronizar o CSV
@st.cache_data(ttl=3600)
def carregar_csv_caminho(caminho_arquivo):
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', decimal=',')

        # Nomes de colunas esperados
        colunas_esperadas = [
            "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT",
            "Tensao", "Corrente", "Kcal_h", "Vazao", "KWAquecimento",
            "KWConsumo", "COP"
        ]

        # Renomear colunas se os nomes originais forem diferentes
        # Ex: 'T-Ambiente' para 'Ambiente'
        mapeamento_colunas = {
            'T-Ambiente': 'Ambiente',
            'T-Entrada': 'Entrada',
            'T-Saída': 'Saída',
            'DIF': 'DeltaT', # Mapeia DIF para DeltaT
            'Tensão': 'Tensao',
            'Corrente': 'Corrente',
            'kcal/h': 'Kcal_h',
            'Vazão': 'Vazao',
            'kW Aquecimento': 'KWAquecimento',
            'kW Consumo': 'KWConsumo',
            'COP': 'COP'
        }

        df = df.rename(columns=mapeamento_colunas)

        # Garante que todas as colunas esperadas existam, preenchendo com NaN se não
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = pd.NA # Adiciona a coluna com valores nulos

        # Seleciona e reordena as colunas para o padrão
        df = df[colunas_esperadas]

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# Função para formatar números para exibição
def formatar_valor(valor, casas_decimais=2):
    if pd.isna(valor):
        return "N/D"
    return f"{valor:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".") # Formato brasileiro

# Função para gerar PDF
def gerar_pdf(df, info_teste):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para o título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=20,
        alignment=1, # Centro
        spaceAfter=14,
        textColor=colors.HexColor('#0d6efd')
    )

    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['h2'],
        fontSize=14,
        alignment=0, # Esquerda
        spaceAfter=8,
        textColor=colors.HexColor('#343a40')
    )

    # Estilo para texto normal
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.spaceAfter = 4

    elements = []

    elements.append(Paragraph("Relatório de Teste de Máquinas Fromtherm", title_style))
    elements.append(Spacer(1, 0.5*cm))

    # Informações do teste
    elements.append(Paragraph("Informações do Teste:", subtitle_style))
    elements.append(Paragraph(f"<b>Modelo:</b> {info_teste.get('modelo', 'N/D')}", normal_style))
    elements.append(Paragraph(f"<b>Operação:</b> {info_teste.get('operacao', 'N/D')}", normal_style))
    elements.append(Paragraph(f"<b>Data:</b> {info_teste.get('data_formatada', 'N/D')}", normal_style))
    elements.append(Paragraph(f"<b>Hora:</b> {info_teste.get('hora', 'N/D')}", normal_style))
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph("Dados Completos do Teste:", subtitle_style))
    elements.append(Spacer(1, 0.2*cm))

    # Preparar dados para a tabela
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)

    # Estilo da tabela
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# =========================
#  INÍCIO DO APP STREAMLIT
# =========================

# Logo da Fromtherm (substitua pelo caminho real da sua imagem)
# st.image("caminho/para/seu/logo_fromtherm.png", width=150) # Descomente e ajuste se tiver um logo

st.title("Máquina de Teste Fromtherm")

# Carrega todos os arquivos CSV disponíveis
todos_arquivos_info = listar_arquivos_csv()

# --- Seção de Última Leitura (Cards) ---
st.markdown("## Última Leitura")

ultima_linha = pd.Series() # Inicializa como série vazia
info_ultimo_arquivo = {}

if todos_arquivos_info:
    # Pega o arquivo mais recente (já ordenado por timestamp)
    arquivo_mais_recente = todos_arquivos_info[0]
    info_ultimo_arquivo = arquivo_mais_recente

    df_ultimo = carregar_csv_caminho(arquivo_mais_recente["caminho"])
    if not df_ultimo.empty:
        ultima_linha = df_ultimo.iloc[-1] # Pega a última linha do DataFrame

# Exibe as informações do teste da última leitura
if info_ultimo_arquivo:
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px; font-size: 1.1em; color: #343a40;">
            <b>Modelo:</b> {info_ultimo_arquivo.get('modelo', 'N/D')} |
            <b>OP:</b> {info_ultimo_arquivo.get('operacao', 'N/D')} |
            <b>Data:</b> {info_ultimo_arquivo.get('data', datetime.now().date()).strftime('%d/%m/%Y')} |
            <b>Hora:</b> {info_ultimo_arquivo.get('hora', 'N/D')}
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("Nenhum arquivo CSV encontrado para exibir a última leitura.")

# Cria os cards de métricas
col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)
col7, col8, col9 = st.columns(3)
col10, col11, col12 = st.columns(3)

# Dicionário para mapear colunas para ícones e títulos
metricas = {
    "Ambiente": {"titulo": "T-Ambiente", "icone": "bi-thermometer-half"},
    "Entrada": {"titulo": "T-Entrada", "icone": "bi-thermometer-half"},
    "Saída": {"titulo": "T-Saída", "icone": "bi-thermometer-half", "cor": "red"},
    "DeltaT": {"titulo": "DIF (ΔT)", "icone": "bi-arrow-down-up"},
    "Tensao": {"titulo": "Tensão", "icone": "bi-lightning-charge"},
    "Corrente": {"titulo": "Corrente", "icone": "bi-lightning"},
    "Kcal_h": {"titulo": "kcal/h", "icone": "bi-fire"},
    "Vazao": {"titulo": "Vazão", "icone": "bi-droplet"},
    "KWAquecimento": {"titulo": "kW Aquecimento", "icone": "bi-sun"},
    "KWConsumo": {"titulo": "kW Consumo", "icone": "bi-plug"},
    "COP": {"titulo": "COP", "icone": "bi-bar-chart-line"},
}

cols = [col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12]
for i, (coluna, info) in enumerate(metricas.items()):
    with cols[i]:
        valor = ultima_linha.get(coluna, pd.NA)
        st.markdown(f"""
            <div class="ft-card" style="border-left-color: {'#dc3545' if info.get('cor') == 'red' else '#0d6efd'};">
                <i class="ft-card-icon {info.get('cor', '')} {info['icone']}"></i>
                <div class="ft-card-content">
                    <div class="ft-card-title">{info['titulo']}</div>
                    <div class="ft-card-value {'red' if info.get('cor') == 'red' else ''}">{formatar_valor(valor)}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---") # Separador visual

# --- Abas para Históricos e Gráficos ---
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("### Históricos Disponíveis")

    # --- Filtros na Barra Lateral ---
    st.sidebar.markdown("## Filtros de Históricos")
    st.sidebar.markdown("---")

    # Coleta todos os valores únicos para os filtros
    modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))
    anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"] != 0)), reverse=True)
    meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"] != 0)))
    ops_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"] != "N/D")))

    # Adiciona "Todos" como opção padrão
    modelos_filtro = ["Todos"] + modelos_disponiveis
    anos_filtro = ["Todos"] + [str(a) for a in anos_disponiveis]
    meses_filtro = ["Todos"] + [f"{m:02d} - {datetime(1, m, 1).strftime('%B')}" for m in meses_disponiveis]
    ops_filtro = ["Todas"] + ops_disponiveis

    # Filtros na sidebar
    modelo_selecionado = st.sidebar.selectbox("Modelo:", modelos_filtro, key="filtro_modelo")
    ano_selecionado = st.sidebar.selectbox("Ano:", anos_filtro, key="filtro_ano")
    mes_selecionado_label = st.sidebar.selectbox("Mês:", meses_filtro, key="filtro_mes")
    data_especifica_str = st.sidebar.text_input("Data específica (opcional - YYYYMMDD):", key="filtro_data")
    op_selecionada = st.sidebar.selectbox("Operação (OP):", ops_filtro, key="filtro_op")

    # Converte o mês selecionado de volta para número
    mes_selecionado = None
    if mes_selecionado_label != "Todos":
        mes_selecionado = int(mes_selecionado_label.split(' ')[0])

    # Aplica os filtros
    arquivos_filtrados = todos_arquivos_info
    if modelo_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == modelo_selecionado]
    if ano_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["ano"] == int(ano_selecionado)]
    if mes_selecionado is not None:
        arquivos_filtrados = [a for a in arquivos_filtrados if a["mes"] == mes_selecionado]
    if data_especifica_str:
        try:
            data_especifica_obj = datetime.strptime(data_especifica_str, "%Y%m%d").date()
            arquivos_filtrados = [a for a in arquivos_filtrados if a["data"] == data_especifica_obj]
        except ValueError:
            st.sidebar.error("Formato de data inválido. Use YYYYMMDD.")
    if op_selecionada != "Todas":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == op_selecionada]

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arquivo in arquivos_filtrados:
            expander_title = (
                f"{arquivo['modelo']} - Linha: L1 - Data: {arquivo['data'].strftime('%d/%m/%Y')} - "
                f"Hora: {arquivo['hora']} - Operação: {arquivo['operacao']}"
            )
            with st.expander(expander_title):
                st.write(f"Caminho do arquivo: `{arquivo['caminho']}`")

                df_exibir = carregar_csv_caminho(arquivo["caminho"])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    # Botão para baixar PDF
                    info_para_pdf = {
                        "modelo": arquivo['modelo'],
                        "operacao": arquivo['operacao'],
                        "data_formatada": arquivo['data'].strftime('%d/%m/%Y'),
                        "hora": arquivo['hora']
                    }
                    pdf_buffer = gerar_pdf(df_exibir, info_para_pdf)
                    nome_pdf = f"Relatorio_{arquivo['modelo']}_OP{arquivo['operacao']}_{arquivo['data'].strftime('%Y%m%d')}_{arquivo['hora'].replace(':', '')}.pdf"
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_buffer,
                        file_name=nome_pdf,
                        mime="application/pdf",
                        key=f"download_pdf_{arquivo['nome_arquivo']}"
                    )

                    # Botão para baixar Excel
                    excel_buffer = BytesIO()
                    df_exibir.to_excel(excel_buffer, index=False, engine='xlsxwriter')
                    excel_buffer.seek(0)
                    nome_excel = f"Dados_{arquivo['modelo']}_OP{arquivo['operacao']}_{arquivo['data'].strftime('%Y%m%d')}_{arquivo['hora'].replace(':', '')}.xlsx"
                    st.download_button(
                        label="Baixar Excel",
                        data=excel_buffer,
                        file_name=nome_excel,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_excel_{arquivo['nome_arquivo']}"
                    )
                else:
                    st.warning("Não foi possível carregar os dados deste arquivo CSV.")

with tab2:
    st.markdown("### Crie Seu Gráfico")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo CSV encontrado para gerar gráficos.")
    else:
        # Filtros para o gráfico (na área principal, mas usando dados filtrados)
        st.markdown("#### Selecione o Arquivo para o Gráfico")

        modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))
        anos_disponiveis_graf = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"] != 0)), reverse=True)
        meses_disponiveis_graf = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"] != 0)))

        modelo_graf = st.selectbox("Modelo:", modelos_disponiveis_graf, key="graf_modelo")
        ano_graf = st.selectbox("Ano:", anos_disponiveis_graf, key="graf_ano")

        meses_graf_labels = ["Todos"] + [f"{m:02d} - {datetime(1, m, 1).strftime('%B')}" for m in meses_disponiveis_graf]
        mes_graf_label = st.selectbox("Mês:", meses_graf_labels, key="graf_mes")

        mes_graf = None
        if mes_graf_label != "Todos":
            mes_graf = int(mes_graf_label.split(' ')[0])

        # Filtra as OPs com base nos modelos, anos e meses já selecionados
        arquivos_por_modelo_ano = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf and a["ano"] == ano_graf]
        arquivos_por_modelo_ano_mes = [a for a in arquivos_por_modelo_ano if a["mes"] == mes_graf or mes_graf is None]
        ops_disponiveis_graf = sorted(list(set(a["operacao"] for a in arquivos_por_modelo_ano_mes if a["operacao"] != "N/D")))

        default_op_index = 0
        if len(ops_disponiveis_graf) == 1:
            default_op_index = 0

        op_graf = st.selectbox(
            "Operação (OP):",
            ops_disponiveis_graf if ops_disponiveis_graf else ["Nenhuma OP disponível"],
            index=default_op_index if ops_disponiveis_graf else 0,
            key="graf_op",
        )

        arquivo_escolhido = None
        for a in todos_arquivos_info:
            if (
                a["modelo"] == modelo_graf
                and a["ano"] == ano_graf
                and (a["mes"] == mes_graf or mes_graf is None)
                and a["operacao"] == op_graf
            ):
                arquivo_escolhido = a
                break

        if not modelos_disponiveis_graf:
            st.info("Ainda não há dados suficientes para criar gráficos.")
        elif arquivo_escolhido is None:
            st.warning("Não foi encontrado um arquivo que combine este Modelo, Ano, Mês e Operação.")
        else:
            st.markdown(f"Arquivo selecionado: **{arquivo_escolhido['nome_arquivo']}**")

            try:
                df_graf = carregar_csv_caminho(arquivo_escolhido["caminho"]).copy()

                # As colunas já foram renomeadas dentro de carregar_csv_caminho
                # df_graf.columns = [ ... ] # Esta linha não é mais necessária aqui

                try:
                    df_graf["DateTime"] = pd.to_datetime(
                        df_graf["Date"].astype(str) + " " + df_graf["Time"].astype(str),
                        errors="coerce",
                    )
                except Exception:
                    df_graf["DateTime"] = df_graf["Time"]

                st.markdown("### Variáveis para o gráfico")

                variaveis_opcoes = [
                    "Ambiente",
                    "Entrada",
                    "Saída",
                    "DeltaT",
                    "Tensao",
                    "Corrente",
                    "Kcal_h",
                    "Vazao",
                    "KWAquecimento",
                    "KWConsumo",
                    "COP",
                ]

                # Filtra as variáveis que realmente existem no DataFrame carregado
                variaveis_disponiveis_no_df = [v for v in variaveis_opcoes if v in df_graf.columns]

                vars_selecionadas = st.multiselect(
                    "Selecione uma ou mais variáveis:",
                    variaveis_disponiveis_no_df,
                    default=[v for v in ["Ambiente", "Entrada", "Saída"] if v in variaveis_disponiveis_no_df], # Define um default mais seguro
                )

                if not vars_selecionadas:
                    st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                else:
                    # Garante que apenas as colunas selecionadas e 'DateTime' sejam usadas
                    df_plot = df_graf[["DateTime"] + vars_selecionadas].copy()

                    # Melt o DataFrame para o formato longo, ideal para Plotly Express
                    df_melted = df_plot.melt(
                        id_vars="DateTime",
                        value_vars=vars_selecionadas,
                        var_name="Variável",
                        value_name="Valor",
                    )

                    fig = px.line(
                        df_melted,
                        x="DateTime",
                        y="Valor",
                        color="Variável",
                        title=f"Gráfico - Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{mes_graf_label.split(' ')[0] if mes_graf_label != 'Todos' else 'Todos os Meses'}",
                        markers=True,
                    )

                    fig.update_yaxes(rangemode="tozero")

                    fig.update_layout(
                        xaxis_title="Tempo",
                        yaxis_title="Valor",
                        hovermode="x unified",
                        legend_title="Variáveis",
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown(
                        "- Use o botão de **fullscreen** no gráfico para expandir.\n"
                        "- Use o ícone de **câmera** no gráfico para baixar como imagem (PNG).\n"
                        "- A imagem baixada pode ser compartilhada via WhatsApp, e-mail, etc., em qualquer dispositivo."
                    )

            except Exception as e:
                st.error(f"Erro ao carregar dados para o gráfico: {e}")
                st.info("Verifique se o arquivo CSV está no formato correto e se as colunas esperadas existem.")