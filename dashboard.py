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
# Configurações da página
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS global (remove o “0” e estiliza os cards)
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde qualquer elemento span que seja o primeiro filho de um div no topo da página */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > div:first-child > span {
        display: none !important;
    }
    /* Uma alternativa mais genérica, caso a de cima não funcione em todos os casos */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > span {
        display: none !important;
    }
    /* E uma última tentativa para qualquer span pequeno e solto no topo */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Outra tentativa para esconder o "0" que pode ser um elemento de "summary" */
    summary {
        display: none !important;
    }
    /* Esconder o botão de menu que pode conter o "0" */
    button[title="View options"] {
        display: none !important;
    }
    /* Esconder o ícone de menu do Streamlit que pode conter o "0" */
    .st-emotion-cache-1r6dm1x { /* Seletor específico para o ícone de menu */
        display: none !important;
    }
    /* Esconder o elemento pai do ícone de menu */
    .st-emotion-cache-10q71g7 { /* Seletor específico para o container do ícone de menu */
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
        transition: transform 0.2s ease-in-out; /* Animação suave */
    }
    .ft-card:hover {
        transform: translateY(-3px); /* Efeito de levantar ao passar o mouse */
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
        color: #444444;
        margin: 0;
        padding: 0;
    }
    .ft-card-value {
        font-size: 22px;
        font-weight: 700;
        color: #1a1a1a;
        margin: 0;
        padding: 0;
    }
    .ft-card-unit {
        font-size: 14px;
        color: #666666;
        margin-left: 5px;
    }
    /* Ajustes para o título principal */
    h1 {
        color: #0d6efd;
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }
    /* Ajustes para o subtítulo */
    h2 {
        color: #333333;
        text-align: center;
        font-size: 1.8em;
        margin-top: 0.5em;
        margin-bottom: 1em;
    }
    /* Estilo para o expander dos históricos */
    .streamlit-expanderHeader {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 5px;
        border: 1px solid #e0e0e0;
    }
    .streamlit-expanderContent {
        background-color: #f9f9f9;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-top: none;
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Funções Auxiliares
# -------------------------------------------------

# Caminho base para os dados (ajustado para o seu repositório)
# Assumindo que a estrutura é fromtherm-dados/dados_brutos/historico_L1/IP_registro192.168.2.150/datalog
DADOS_DIR = "./dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

def listar_arquivos_csv():
    """Lista arquivos CSV na pasta DADOS_DIR e extrai informações."""
    arquivos_info = []
    if not os.path.exists(DADOS_DIR):
        st.error(f"Diretório de dados não encontrado: {DADOS_DIR}")
        return []

    # Padrão regex para extrair informações do nome do arquivo
    # Ex: historico_L1_YYYYMMDD_HHMM_OPXXXX_FTYYY.csv
    # Grupo 1: Modelo (FTYYY)
    # Grupo 2: OP (OPXXXX)
    # Grupo 3: Data (YYYYMMDD)
    # Grupo 4: Hora (HHMM)
    # Grupo 5: Nome completo do arquivo
    regex_pattern = re.compile(r"historico_L1_(\d{8})_(\d{4})_(OP\d+)_(\w+)\.csv", re.IGNORECASE)

    for caminho_completo in glob.glob(os.path.join(DADOS_DIR, "*.csv")):
        nome_arquivo = os.path.basename(caminho_completo)
        match = regex_pattern.search(nome_arquivo)

        info = {
            "caminho": caminho_completo,
            "nome_arquivo": nome_arquivo,
            "modelo": "N/D",
            "operacao": "N/D",
            "data_arquivo": "N/D",
            "hora_arquivo": "N/D",
            "data_modificacao": datetime.fromtimestamp(os.path.getmtime(caminho_completo)),
            "timestamp_arquivo": datetime.min # Valor padrão para ordenação
        }

        if match:
            data_str, hora_str, operacao_str, modelo_str = match.groups()
            info["modelo"] = modelo_str
            info["operacao"] = operacao_str
            info["data_arquivo"] = datetime.strptime(data_str, "%Y%m%d").strftime("%d/%m/%Y")
            info["hora_arquivo"] = datetime.strptime(hora_str, "%H%M").strftime("%H:%M")
            try:
                # Usar a data e hora do nome do arquivo para o timestamp
                info["timestamp_arquivo"] = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")
            except ValueError:
                st.warning(f"Não foi possível parsear data/hora do nome do arquivo: {nome_arquivo}")
                info["timestamp_arquivo"] = datetime.min # Fallback

        arquivos_info.append(info)

    # Ordena os arquivos pelo timestamp extraído do nome (mais recente primeiro)
    arquivos_info.sort(key=lambda x: x["timestamp_arquivo"], reverse=True)
    return arquivos_info

@st.cache_data(ttl=600) # Cache por 10 minutos
def carregar_csv_caminho(caminho_arquivo):
    """Carrega um arquivo CSV e retorna o DataFrame."""
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', decimal=',')
        # Tenta converter 'DateTime' para datetime, se existir
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            df = df.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

def mostra_valor(df, coluna):
    """Retorna o último valor da coluna do DataFrame ou 'N/D'."""
    if not df.empty and coluna in df.columns:
        # Tenta converter para numérico, forçando erros para NaN
        valor = pd.to_numeric(df[coluna].iloc[-1], errors='coerce')
        if pd.isna(valor):
            return "N/D"
        return f"{valor:.2f}".replace('.', ',') # Formata para 2 casas decimais e usa vírgula
    return "N/D"

def exibir_card(titulo, valor, unidade, icone_classe, cor_icone="", cor_borda=""):
    """Exibe um card de métrica com ícone e animação."""
    card_style = f"border-left: 4px solid {cor_borda if cor_borda else '#0d6efd'};"
    icon_style = f"color: {cor_icone if cor_icone else '#0d6efd'};"

    st.markdown(
        f"""
        <div class="ft-card" style="{card_style}">
            <i class="{icone_classe} ft-card-icon" style="{icon_style}"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor}<span class="ft-card-unit">{unidade}</span></p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def criar_pdf(df, info_arquivo):
    """Cria um PDF a partir de um DataFrame."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    # Título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=18,
        alignment=1, # Centered
        spaceAfter=14
    )
    elements.append(Paragraph(f"Relatório de Dados - {info_arquivo['nome_arquivo']}", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Informações do arquivo
    info_text = f"<b>Modelo:</b> {info_arquivo['modelo']} | <b>OP:</b> {info_arquivo['operacao']} | <b>Data:</b> {info_arquivo['data_arquivo']} | <b>Hora:</b> {info_arquivo['hora_arquivo']}"
    elements.append(Paragraph(info_text, styles['Normal']))
    elements.append(Spacer(1, 0.2 * inch))

    # Tabela
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8), # Reduzir fonte para caber mais dados
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Barra Lateral (Sidebar)
# -------------------------------------------------
st.sidebar.image("https://raw.githubusercontent.com/bruno-fromtherm/fromtherm-dados/main/logo_fromtherm.png", use_column_width=True)
st.sidebar.title("FromTherm")
st.sidebar.markdown("---")
st.sidebar.header("Filtros de Pesquisa")

todos_arquivos_info = listar_arquivos_csv()

# Extrair opções únicas para os filtros
modelos_unicos = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info if arq["modelo"] != "N/D"])))
anos_unicos = sorted(list(set([datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").year for arq in todos_arquivos_info if arq["data_arquivo"] != "N/D"])), reverse=True)
meses_unicos = sorted(list(set([datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").month for arq in todos_arquivos_info if arq["data_arquivo"] != "N/D"])))
meses_nomes = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
operacoes_unicas = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info if arq["operacao"] != "N/D"])))

# Adicionar "Todos" como opção para os filtros
modelo_filtro = st.sidebar.selectbox("Filtrar por Modelo:", ["Todos"] + modelos_unicos)
ano_filtro = st.sidebar.selectbox("Filtrar por Ano:", ["Todos"] + anos_unicos)
mes_filtro_num = st.sidebar.selectbox("Filtrar por Mês:", ["Todos"] + [m for m in meses_unicos], format_func=lambda x: meses_nomes.get(x, "Todos"))
data_filtro_str = st.sidebar.text_input("Filtrar por Data (DD/MM/AAAA):", "")
operacao_filtro = st.sidebar.selectbox("Filtrar por Operação:", ["Todos"] + operacoes_unicas)

# Aplicar filtros
arquivos_filtrados = todos_arquivos_info
if modelo_filtro != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["modelo"] == modelo_filtro]
if ano_filtro != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["data_arquivo"] != "N/D" and datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").year == ano_filtro]
if mes_filtro_num != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["data_arquivo"] != "N/D" and datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").month == mes_filtro_num]
if data_filtro_str:
    arquivos_filtrados = [arq for arq in arquivos_filtrados if data_filtro_str in arq["data_arquivo"]]
if operacao_filtro != "Todos":
    arquivos_filtrados = [arq for arq in arquivos_filtrados if arq["operacao"] == operacao_filtro]

# -------------------------------------------------
# Conteúdo Principal
# -------------------------------------------------
st.title("Máquina de Teste Fromtherm")

tab1, tab2 = st.tabs(["Dashboard", "Crie Seu Gráfico"])

with tab1:
    st.header("Última Leitura Atualizada")

    info_ultimo_arquivo = arquivos_filtrados[0] if arquivos_filtrados else None
    df_ultimo = pd.DataFrame()

    if info_ultimo_arquivo:
        df_ultimo = carregar_csv_caminho(info_ultimo_arquivo["caminho"])
        if not df_ultimo.empty:
            st.markdown(
                f"**Modelo:** {info_ultimo_arquivo['modelo'] or 'N/D'} | "
                f"**OP:** {info_ultimo_arquivo['operacao'] or 'N/D'} | "
                f"**Data:** {info_ultimo_arquivo['data_arquivo'] or 'N/D'} | "
                f"**Hora:** {info_ultimo_arquivo['hora_arquivo'] or 'N/D'}"
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                exibir_card("T-Ambiente", mostra_valor(df_ultimo, "Ambiente"), "°C", "bi bi-thermometer-half")
            with col2:
                exibir_card("T-Entrada", mostra_valor(df_ultimo, "Entrada"), "°C", "bi bi-arrow-down-circle")
            with col3:
                exibir_card("T-Saída", mostra_valor(df_ultimo, "Saída"), "°C", "bi bi-arrow-up-circle", "red", "red")
            with col4:
                exibir_card("DIF", mostra_valor(df_ultimo, "DeltaT"), "°C", "bi bi-arrow-down-up")

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                exibir_card("Tensão", mostra_valor(df_ultimo, "Tensao"), "V", "bi bi-lightning-charge")
            with col6:
                exibir_card("Corrente", mostra_valor(df_ultimo, "Corrente"), "A", "bi bi-lightning")
            with col7:
                exibir_card("kcal/h", mostra_valor(df_ultimo, "Kcal_h"), "", "bi bi-fire")
            with col8:
                exibir_card("Vazão", mostra_valor(df_ultimo, "Vazao"), "L/min", "bi bi-water")

            col9, col10 = st.columns(2)
            with col9:
                exibir_card("kW Aquecimento", mostra_valor(df_ultimo, "KWAquecimento"), "kW", "bi bi-sun")
            with col10:
                exibir_card("kW Consumo", mostra_valor(df_ultimo, "KWConsumo"), "kW", "bi bi-power")

            st.markdown("---")
            st.subheader("Performance")
            col_cop, _, _, _ = st.columns(4)
            with col_cop:
                exibir_card("COP", mostra_valor(df_ultimo, "COP"), "", "bi bi-graph-up")
        else:
            st.info("Não foi possível carregar dados da última leitura. O arquivo pode estar vazio ou com formato incorreto.")
    else:
        st.info("Nenhum histórico encontrado para a última leitura com os filtros aplicados.")

    st.markdown("---")
    st.header("Históricos Disponíveis")

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arq in arquivos_filtrados:
            expander_label = f"{arq['nome_arquivo']} (Modelo: {arq['modelo']}, OP: {arq['operacao']}, Data: {arq['data_arquivo']} {arq['hora_arquivo']})"
            with st.expander(expander_label, expanded=False):
                st.write(f"Caminho: {arq['caminho']}")
                st.write(f"Data modificação: {arq['data_modificacao'].strftime('%d/%m/%Y %H:%M:%S')}")

                df_exibir = carregar_csv_caminho(arq["caminho"])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    # Nome do arquivo para download
                    nome_base = f"Maquina_{arq['modelo']}_{arq['operacao']}_{arq['data_arquivo'].replace('/', '-')}_{arq['hora_arquivo'].replace(':', 'h')}s"

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        pdf_buffer = criar_pdf(df_exibir, arq)
                        st.download_button(
                            label="Baixar como PDF",
                            data=pdf_buffer,
                            file_name=f"{nome_base}.pdf",
                            mime="application/pdf",
                            help="Baixa a tabela completa como um arquivo PDF."
                        )
                    with col_dl2:
                        csv_buffer = BytesIO()
                        df_exibir.to_excel(csv_buffer, index=False, sheet_name="Dados", engine='xlsxwriter')
                        csv_buffer.seek(0)
                        st.download_button(
                            label="Baixar como Excel",
                            data=csv_buffer,
                            file_name=f"{nome_base}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Baixa a tabela completa como um arquivo Excel."
                        )
                else:
                    st.info("Não foi possível carregar os dados deste arquivo ou ele está vazio.")

with tab2:
    st.header("Crie Seu Gráfico Personalizado")

    if not todos_arquivos_info:
        st.info("Nenhum dado disponível para gerar gráficos. Carregue arquivos CSV primeiro.")
    else:
        # Filtros para o gráfico (usando os mesmos dados base)
        modelos_graf_unicos = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info if arq["modelo"] != "N/D"])))
        ops_graf_unicas = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info if arq["operacao"] != "N/D"])))
        anos_graf_unicos = sorted(list(set([datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").year for arq in todos_arquivos_info if arq["data_arquivo"] != "N/D"])), reverse=True)
        meses_graf_unicos = sorted(list(set([datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").month for arq in todos_arquivos_info if arq["data_arquivo"] != "N/D"])))

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            modelo_graf = st.selectbox("Selecione o Modelo para o Gráfico:", modelos_graf_unicos)
        with col_g2:
            op_graf = st.selectbox("Selecione a Operação para o Gráfico:", ops_graf_unicas)

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            ano_graf = st.selectbox("Selecione o Ano para o Gráfico:", ["Todos"] + anos_graf_unicos)
        with col_g4:
            mes_graf = st.selectbox("Selecione o Mês para o Gráfico:", ["Todos"] + meses_graf_unicos, format_func=lambda x: meses_nomes.get(x, "Todos"))

        # Encontrar o arquivo correspondente aos filtros do gráfico
        arquivo_graf_info = None
        for arq in todos_arquivos_info:
            match_modelo = arq["modelo"] == modelo_graf
            match_op = arq["operacao"] == op_graf
            match_ano = (ano_graf == "Todos") or (arq["data_arquivo"] != "N/D" and datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").year == ano_graf)
            match_mes = (mes_graf == "Todos") or (arq["data_arquivo"] != "N/D" and datetime.strptime(arq["data_arquivo"], "%d/%m/%Y").month == mes_graf)

            if match_modelo and match_op and match_ano and match_mes:
                arquivo_graf_info = arq
                break

        if not arquivo_graf_info:
            st.info("Nenhum arquivo encontrado para os filtros de gráfico selecionados.")
        else:
            st.markdown(f"**Arquivo selecionado:** {arquivo_graf_info['nome_arquivo']}")
            df_graf = carregar_csv_caminho(arquivo_graf_info["caminho"])

            if df_graf.empty or 'DateTime' not in df_graf.columns:
                st.warning("O arquivo selecionado não contém dados válidos ou a coluna 'DateTime' está ausente para gerar o gráfico.")
            else:
                st.markdown("---")
                st.subheader("Selecione as Variáveis para o Gráfico")

                # Opções de variáveis para o gráfico
                opcoes_variaveis = [
                    "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                    "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
                ]
                # Filtrar colunas que realmente existem no DataFrame
                opcoes_variaveis_existentes = [col for col in opcoes_variaveis if col in df_graf.columns]

                vars_selecionadas = st.multiselect(
                    "Escolha as variáveis para plotar:",
                    opcoes_variaveis_existentes,
                    default=["Ambiente", "Entrada", "Saída"] if "Ambiente" in opcoes_variaveis_existentes else []
                )

                if not vars_selecionadas:
                    st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                else:
                    # Melt o DataFrame para o formato longo, ideal para Plotly Express
                    df_melted = df_graf[["DateTime"] + vars_selecionadas].melt(
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
                        title=f"Gráfico - Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{datetime(1, mes_graf, 1).strftime('%B') if mes_graf != 'Todos' else 'Todos os Meses'}",
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