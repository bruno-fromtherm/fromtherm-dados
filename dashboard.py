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
from reportlab.lib.units import inch  # IMPORTANTE: para usar Spacer(... * inch)
from io import BytesIO

import plotly.express as px

# -------------------------------------------------
# Configuração da página
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS global: remove “0” e estiliza cards
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde o botão de menu do Streamlit que pode conter o "0" */
    button[title="View options"] {
        display: none !important;
    }
    /* Esconde o elemento pai do ícone de menu, se o anterior não funcionar */
    .st-emotion-cache-1r6dm1x { /* Seletor específico para o ícone de menu */
        display: none !important;
    }
    /* Esconde qualquer span solto no topo que possa ser o "0" */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Esconde o elemento summary que pode ser o "0" */
    summary {
        display: none !important;
    }

    /* Estilo dos cards */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .ft-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd;
        animation: ft-pulse 1.5s ease-in-out infinite;
    }
    .ft-card-icon.red {
        color: #dc3545;
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
        font-size: 18px;
        font-weight: 700;
        color: #111111;
        margin: 0;
        padding: 0;
    }
    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 1; }
        50%  { transform: scale(1.05); opacity: 0.85; }
        100% { transform: scale(1);   opacity: 1; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Funções auxiliares
# -------------------------------------------------

# Caminho base dos CSVs no repositório
# Ajustado para o caminho completo que você indicou
DADOS_DIR = os.path.join(
    ".", "dados_brutos", "historico_L1", "IP_registro192.168.2.150", "datalog"
)

def extrair_info_nome_arquivo(nome_arquivo: str) -> dict:
    """
    Extrai modelo, data, hora e operação do nome do arquivo.
    Exemplo esperado: historico_L1_20250308_0939_OP1234_FT987.csv
    """
    info = {
        "modelo": "N/D",
        "operacao": "N/D",
        "data": datetime.min.date(), # Usar data mínima para ordenação
        "hora": datetime.min.time(), # Usar hora mínima para ordenação
        "data_arquivo": "N/D",
        "hora_arquivo": "N/D",
    }

    # Padrão regex mais robusto para capturar as partes
    # historico_L1_YYYYMMDD_HHMM_OPXXXX_FTYYY.csv
    padrao = (
        r"historico_L1_"
        r"(?P<data>\d{8})_"
        r"(?P<hora>\d{4})_"
        r"OP(?P<op>\d+)_"
        r"FT(?P<modelo>[A-Za-z0-9]+)"
    )

    m = re.search(padrao, nome_arquivo)
    if not m:
        return info

    data_str = m.group("data")
    hora_str = m.group("hora")
    op_str = m.group("op")
    modelo_str = m.group("modelo")

    try:
        info["data"] = datetime.strptime(data_str, "%Y%m%d").date()
        info["data_arquivo"] = info["data"].strftime("%d/%m/%Y")
    except ValueError:
        pass # Mantém datetime.min.date()

    try:
        info["hora"] = datetime.strptime(hora_str, "%H%M").time()
        info["hora_arquivo"] = info["hora"].strftime("%H:%M")
    except ValueError:
        pass # Mantém datetime.min.time()

    info["operacao"] = op_str
    info["modelo"] = modelo_str
    return info

def listar_arquivos_csv():
    """Lista arquivos CSV no DADOS_DIR e extrai informações."""
    todos_arquivos_info = []
    if not os.path.exists(DADOS_DIR):
        st.error(f"Diretório de dados não encontrado: {DADOS_DIR}")
        return []

    arquivos_csv = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    if not arquivos_csv:
        return []

    for caminho_completo in arquivos_csv:
        nome_arquivo = os.path.basename(caminho_completo)
        info = extrair_info_nome_arquivo(nome_arquivo)
        info["caminho"] = caminho_completo
        info["nome_arquivo"] = nome_arquivo
        info["data_modificacao"] = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
        todos_arquivos_info.append(info)

    # Ordena do mais recente para o mais antigo (data e hora)
    todos_arquivos_info.sort(key=lambda x: (x["data"], x["hora"]), reverse=True)
    return todos_arquivos_info

@st.cache_data(ttl=600) # Cache por 10 minutos
def carregar_csv_caminho(caminho_arquivo):
    """Carrega um CSV de um caminho específico, tratando erros."""
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', decimal=',')
        # Converte a coluna 'DateTime' para datetime, se existir
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            df = df.dropna(subset=['DateTime']) # Remove linhas com DateTime inválido
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
        return None

def mostra_valor(df, coluna, unidade="", cor_icone=""):
    """Retorna o último valor de uma coluna do DataFrame ou 'N/D'."""
    if df is not None and not df.empty and coluna in df.columns:
        valor = df[coluna].iloc[-1] # Pega o último valor
        if pd.isna(valor):
            return "N/D"
        return f"{valor:.2f} {unidade}".strip() # Formata para 2 casas decimais
    return "N/D"

def exibir_card(titulo, valor, unidade, icone_classe, cor_icone=""):
    """Exibe um card de métrica com ícone e valor."""
    st.markdown(
        f"""
        <div class="ft-card">
            <i class="{icone_classe} ft-card-icon {cor_icone}"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def criar_pdf(df: pd.DataFrame, info_arquivo: dict) -> BytesIO:
    """Cria um PDF a partir de um DataFrame."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    # Estilo para o título
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=18,
        spaceAfter=14,
        alignment=1, # Centro
    )
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['h2'],
        fontSize=12,
        spaceAfter=8,
        alignment=0, # Esquerda
    )
    # Estilo para texto normal
    normal_style = styles['Normal']

    # Título do documento
    elements.append(Paragraph("Relatório de Dados da Máquina Fromtherm", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Informações do arquivo
    elements.append(Paragraph(f"<b>Modelo:</b> {info_arquivo['modelo']}", subtitle_style))
    elements.append(Paragraph(f"<b>Operação (OP):</b> {info_arquivo['operacao']}", subtitle_style))
    elements.append(Paragraph(f"<b>Data do Arquivo:</b> {info_arquivo['data_arquivo']}", subtitle_style))
    elements.append(Paragraph(f"<b>Hora do Arquivo:</b> {info_arquivo['hora_arquivo']}", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Tabela de dados
    if not df.empty:
        data = [df.columns.tolist()] + df.values.tolist()
        table = Table(data)

        # Estilo da tabela
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8), # Tamanho da fonte da tabela
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("Nenhum dado disponível para este arquivo.", normal_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Barra Lateral
# -------------------------------------------------
with st.sidebar:
    # Tenta carregar a imagem, se não encontrar, mostra um placeholder
    try:
        st.image(
            "LOGO-FROMTHERM.png",
            use_column_width=True,
        )
    except Exception:
        st.warning("Logo FromTherm não encontrada. Verifique se 'LOGO-FROMTHERM.png' está na mesma pasta do dashboard.py.")

    st.title("FromTherm")
    st.header("Filtros de Pesquisa")

    todos_arquivos_info = listar_arquivos_csv()

    # Extrair opções únicas para os filtros
    modelos = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info if arq["modelo"] != "N/D"])))
    anos = sorted(list(set([arq["data"].year for arq in todos_arquivos_info if arq["data"] is not None])), reverse=True)
    meses_num = sorted(list(set([arq["data"].month for arq in todos_arquivos_info if arq["data"] is not None])))
    meses_map = {i: datetime(1, i, 1).strftime('%B') for i in meses_num} # Mapeia número para nome do mês
    operacoes = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info if arq["operacao"] != "N/D"])))

    # Adicionar "Todos" como opção padrão
    modelo_selecionado = st.selectbox("Filtrar por Modelo:", ["Todos"] + modelos)
    ano_selecionado = st.selectbox("Filtrar por Ano:", ["Todos"] + anos)
    mes_selecionado_label = st.selectbox("Filtrar por Mês:", ["Todos"] + [meses_map[m] for m in meses_num])
    mes_selecionado = next((m for m, label in meses_map.items() if label == mes_selecionado_label), "Todos")

    data_especifica = st.date_input("Data específica (opcional):", value=None, format="DD/MM/YYYY")
    operacao_selecionada = st.selectbox("Filtrar por Operação:", ["Todos"] + operacoes)

# -------------------------------------------------
# Conteúdo Principal
# -------------------------------------------------
st.title("Máquina de Teste Fromtherm")

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.header("Última Leitura Atualizada")

    # Filtrar arquivos para a última leitura
    arquivos_filtrados_ultima_leitura = todos_arquivos_info
    if modelo_selecionado != "Todos":
        arquivos_filtrados_ultima_leitura = [arq for arq in arquivos_filtrados_ultima_leitura if arq["modelo"] == modelo_selecionado]
    if ano_selecionado != "Todos":
        arquivos_filtrados_ultima_leitura = [arq for arq in arquivos_filtrados_ultima_leitura if arq["data"] and arq["data"].year == ano_selecionado]
    if mes_selecionado != "Todos":
        arquivos_filtrados_ultima_leitura = [arq for arq in arquivos_filtrados_ultima_leitura if arq["data"] and arq["data"].month == mes_selecionado]
    if data_especifica:
        arquivos_filtrados_ultima_leitura = [arq for arq in arquivos_filtrados_ultima_leitura if arq["data"] and arq["data"] == data_especifica]
    if operacao_selecionada != "Todos":
        arquivos_filtrados_ultima_leitura = [arq for arq in arquivos_filtrados_ultima_leitura if arq["operacao"] == operacao_selecionada]

    df_ultimo = None
    info_ultimo_arquivo = None
    if arquivos_filtrados_ultima_leitura:
        # Pega o arquivo mais recente entre os filtrados
        info_ultimo_arquivo = arquivos_filtrados_ultima_leitura[0]
        df_ultimo = carregar_csv_caminho(info_ultimo_arquivo["caminho"])

    if info_ultimo_arquivo and df_ultimo is not None and not df_ultimo.empty:
        st.markdown(
            f"**Modelo:** {info_ultimo_arquivo['modelo']} | "
            f"**OP:** {info_ultimo_arquivo['operacao']} | "
            f"**Data:** {info_ultimo_arquivo['data_arquivo']} | "
            f"**Hora:** {info_ultimo_arquivo['hora_arquivo']}"
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            exibir_card("T-Ambiente", mostra_valor(df_ultimo, "Ambiente"), "°C", "bi bi-thermometer-half")
        with col2:
            exibir_card("T-Entrada", mostra_valor(df_ultimo, "Entrada"), "°C", "bi bi-thermometer-half")
        with col3:
            exibir_card("T-Saída", mostra_valor(df_ultimo, "Saída"), "°C", "bi bi-thermometer-half red")
        with col4:
            exibir_card("DIF (ΔT)", mostra_valor(df_ultimo, "DeltaT"), "°C", "bi bi-arrow-down-up")

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
        st.info("Não foi possível carregar a última leitura com os filtros aplicados. Verifique se há arquivos CSV válidos.")

    st.markdown("---")
    st.header("Históricos Disponíveis")

    # Aplicar filtros à lista de históricos
    arquivos_exibir = todos_arquivos_info
    if modelo_selecionado != "Todos":
        arquivos_exibir = [arq for arq in arquivos_exibir if arq["modelo"] == modelo_selecionado]
    if ano_selecionado != "Todos":
        arquivos_exibir = [arq for arq in arquivos_exibir if arq["data"] and arq["data"].year == ano_selecionado]
    if mes_selecionado != "Todos":
        arquivos_exibir = [arq for arq in arquivos_exibir if arq["data"] and arq["data"].month == mes_selecionado]
    if data_especifica:
        arquivos_exibir = [arq for arq in arquivos_exibir if arq["data"] and arq["data"] == data_especifica]
    if operacao_selecionada != "Todos":
        arquivos_exibir = [arq for arq in arquivos_exibir if arq["operacao"] == operacao_selecionada]

    if not arquivos_exibir:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arq in arquivos_exibir:
            with st.expander(f"Modelo: {arq['modelo']} | OP: {arq['operacao']} | Data: {arq['data_arquivo']} {arq['hora_arquivo']}"):
                st.write(f"Nome do arquivo: {arq['nome_arquivo']}")
                st.write(f"Caminho: {arq['caminho']}")
                st.write(f"Data modificação: {arq['data_modificacao'].strftime('%d/%m/%Y %H:%M:%S')}")

                df_exibir = carregar_csv_caminho(arq["caminho"])

                if df_exibir is not None and not df_exibir.empty:
                    st.subheader("Dados da Planilha:")
                    st.dataframe(df_exibir, use_container_width=True)

                    # Nome do arquivo para download
                    nome_base_download = (
                        f"Maquina_FT{arq['modelo']}_OP{arq['operacao']}_"
                        f"{arq['data_arquivo'].replace('/', '')}_"
                        f"{arq['hora_arquivo'].replace(':', '')}"
                    )

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        # Botão de download PDF
                        pdf_buffer = criar_pdf(df_exibir, arq)
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=f"{nome_base_download}.pdf",
                            mime="application/pdf",
                            help="Baixa os dados da planilha em formato PDF.",
                        )
                    with col_dl2:
                        # Botão de download Excel
                        excel_buffer = BytesIO()
                        df_exibir.to_excel(excel_buffer, index=False, engine='openpyxl')
                        excel_buffer.seek(0)
                        st.download_button(
                            label="Baixar Excel",
                            data=excel_buffer,
                            file_name=f"{nome_base_download}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Baixa os dados da planilha em formato Excel.",
                        )
                else:
                    st.info("Este arquivo CSV está vazio ou não pôde ser lido.")

with tab2:
    st.header("Crie Seu Gráfico")

    st.markdown(
        "Selecione o modelo e a operação para visualizar os dados em um gráfico interativo."
    )

    # Filtros para a aba de gráficos
    modelos_graf = sorted(list(set([arq["modelo"] for arq in todos_arquivos_info if arq["modelo"] != "N/D"])))
    ops_graf = sorted(list(set([arq["operacao"] for arq in todos_arquivos_info if arq["operacao"] != "N/D"])))

    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        modelo_graf = st.selectbox("Modelo para o Gráfico:", modelos_graf, key="modelo_graf_sel")
    with col_graf2:
        op_graf = st.selectbox("Operação (OP) para o Gráfico:", ops_graf, key="op_graf_sel")

    if modelo_graf and op_graf:
        arquivos_graf = [
            arq for arq in todos_arquivos_info
            if arq["modelo"] == modelo_graf and arq["operacao"] == op_graf
        ]
        arquivos_graf.sort(key=lambda x: (x["data"], x["hora"])) # Ordena para pegar o mais antigo primeiro

        if not arquivos_graf:
            st.warning("Não há arquivos válidos para esse modelo/OP.")
        else:
            # Pegar todos os anos e meses disponíveis para o modelo/OP selecionado
            anos_disponiveis = sorted(list(set([a["data"].year for a in arquivos_graf if a["data"]])))
            ano_graf = st.selectbox("Ano:", ["Todos"] + anos_disponiveis, key="ano_graf_sel")

            meses_disponiveis = []
            if ano_graf != "Todos":
                meses_disponiveis = sorted(list(set([a["data"].month for a in arquivos_graf if a["data"] and a["data"].year == ano_graf])))

            mes_graf_label = st.selectbox("Mês:", ["Todos"] + [datetime(1, m, 1).strftime('%B') for m in meses_disponiveis], key="mes_graf_sel")
            mes_graf = next((m for m, label in {i: datetime(1, i, 1).strftime('%B') for i in meses_disponiveis}.items() if label == mes_graf_label), "Todos")

            # Filtrar o arquivo a ser carregado com base nos filtros de ano e mês
            arq_para_grafico = None
            if ano_graf == "Todos" and mes_graf == "Todos":
                # Se "Todos" em ano e mês, pega o mais recente de todos os arquivos filtrados por modelo/OP
                arq_para_grafico = arquivos_graf[-1] if arquivos_graf else None
            elif ano_graf != "Todos" and mes_graf == "Todos":
                # Se ano específico, mas todos os meses, pega o mais recente desse ano
                arquivos_do_ano = [a for a in arquivos_graf if a["data"] and a["data"].year == ano_graf]
                arq_para_grafico = arquivos_do_ano[-1] if arquivos_do_ano else None
            elif ano_graf != "Todos" and mes_graf != "Todos":
                # Se ano e mês específicos, pega o mais recente desse mês/ano
                arquivos_do_mes = [a for a in arquivos_graf if a["data"] and a["data"].year == ano_graf and a["data"].month == mes_graf]
                arq_para_grafico = arquivos_do_mes[-1] if arquivos_do_mes else None

            if arq_para_grafico is None:
                st.warning("Nenhum arquivo encontrado para os filtros selecionados.")
            else:
                df_graf = carregar_csv_caminho(arq_para_grafico["caminho"])
                if df_graf is None or df_graf.empty:
                    st.warning("Arquivo selecionado está vazio ou não pôde ser lido.")
                else:
                    # Opções de variáveis para o gráfico
                    opcoes_variaveis = [
                        "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                        "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
                    ]
                    opcoes_variaveis_existentes = [c for c in opcoes_variaveis if c in df_graf.columns]

                    vars_selecionadas = st.multiselect(
                        "Selecione as variáveis para plotar:",
                        opcoes_variaveis_existentes,
                        default=[v for v in ["Ambiente", "Entrada", "Saída"] if v in opcoes_variaveis_existentes]
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
                            title=f"Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{mes_graf:02d}",
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
                            "- Use o botão de **fullscreen** no gráfico (canto superior direito do gráfico) para tela cheia.\n"
                            "- Use o ícone de **câmera** para baixar como imagem (PNG).\n"
                            "- A imagem pode ser enviada por WhatsApp, e-mail, etc., em PC ou celular."
                        )