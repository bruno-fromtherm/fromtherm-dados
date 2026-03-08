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
    /* Tentativas para esconder o "0" / elementos soltos */
    div[data-testid="stAppViewContainer"] > div:first-child span {
        display: none !important;
    }
    span[data-testid="stDecoration"] {
        display: none !important;
    }
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
DADOS_DIR = os.path.join(
    ".", "dados_brutos", "historico_L1", "IP_registro192.168.2.150", "datalog"
)

def extrair_info_nome_arquivo(nome_arquivo: str) -> dict:
    """
    Extrai modelo, data, hora e operação do nome do arquivo.
    Exemplo esperado:
      historico_L1_20250308_0939_OP1234_FT987.csv
    """
    info = {
        "modelo": "N/D",
        "operacao": "N/D",
        "data": None,
        "hora": None,
        "data_arquivo": "N/D",
        "hora_arquivo": "N/D",
    }

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
        dt_data = datetime.strptime(data_str, "%Y%m%d").date()
        info["data"] = dt_data
        info["data_arquivo"] = dt_data.strftime("%d/%m/%Y")
    except Exception:
        info["data"] = None

    try:
        info["hora"] = hora_str
        info["hora_arquivo"] = f"{hora_str[:2]}:{hora_str[2:]}h"
    except Exception:
        info["hora"] = None

    info["operacao"] = op_str
    info["modelo"] = modelo_str

    return info


def listar_arquivos_csv():
    """Lista todos os CSVs na pasta, com info extraída do nome e data de modificação."""
    padrao = os.path.join(DADOS_DIR, "*.csv")
    caminhos = glob.glob(padrao)

    arquivos_info = []
    for caminho in caminhos:
        nome = os.path.basename(caminho)
        info = extrair_info_nome_arquivo(nome)

        try:
            ts = os.path.getmtime(caminho)
            dt_mod = datetime.fromtimestamp(ts)
        except Exception:
            dt_mod = datetime.min

        arquivos_info.append(
            {
                "caminho": caminho,
                "nome_arquivo": nome,
                "data_modificacao": dt_mod,
                "modelo": info["modelo"],
                "operacao": info["operacao"],
                "data": info["data"],
                "hora": info["hora"],
                "data_arquivo": info["data_arquivo"],
                "hora_arquivo": info["hora_arquivo"],
            }
        )

    # Ordena por data de modificação (mais recente primeiro)
    arquivos_info.sort(key=lambda x: x["data_modificacao"], reverse=True)
    return arquivos_info


def carregar_csv_caminho(caminho: str) -> pd.DataFrame | None:
    """Lê um CSV e normaliza algumas colunas."""
    try:
        df = pd.read_csv(caminho, sep=";", decimal=",", encoding="latin1")
    except Exception:
        return None

    # Normalizar possíveis nomes de colunas
    rename_map = {
        "Temp_Ambiente": "Ambiente",
        "Temp_Entrada": "Entrada",
        "Temp_Saida": "Saída",
        "Delta_T": "DeltaT",
        "Tensao": "Tensao",
        "Corrente": "Corrente",
        "Kcal_h": "Kcal_h",
        "Vazao": "Vazao",
        "KW_Aquec": "KWAquecimento",
        "KW_Cons": "KWConsumo",
    }
    df.rename(columns=rename_map, inplace=True)

    # Coluna de data/hora
    possiveis_datetime = ["DateTime", "DataHora", "Data_Hora", "Data_Horario"]
    col_dt = None
    for c in possiveis_datetime:
        if c in df.columns:
            col_dt = c
            break

    if col_dt:
        try:
            df["DateTime"] = pd.to_datetime(df[col_dt], errors="coerce")
        except Exception:
            df["DateTime"] = pd.NaT
    else:
        df["DateTime"] = pd.NaT

    return df


def mostra_valor(df: pd.DataFrame | None, coluna: str, casas_decimais: int = 1):
    """Devolve valor formatado da última linha ou 'N/D'."""
    if df is None or df.empty:
        return "N/D"
    if coluna not in df.columns:
        return "N/D"
    valor = df[coluna].iloc[-1]
    if pd.isna(valor):
        return "N/D"
    try:
        return f"{float(valor):.{casas_decimais}f}"
    except Exception:
        return "N/D"


def exibir_card(titulo, valor, unidade, icon_class, icon_color="default"):
    """Mostra um card estilizado com o valor."""
    icon_extra_class = "red" if icon_color == "red" else ""
    html = f"""
    <div class="ft-card">
        <div class="ft-card-icon {icon_extra_class}">
            <i class="{icon_class}"></i>
        </div>
        <div class="ft-card-content">
            <p class="ft-card-title">{titulo}</p>
            <p class="ft-card-value">{valor} {unidade}</p>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# -------------------------------------------------
# Funções para gerar PDF e Excel
# -------------------------------------------------
def gerar_pdf_df(df: pd.DataFrame, info_arquivo: dict) -> BytesIO:
    """Gera um PDF simples com tabela do DataFrame."""
    buffer = BytesIO()

    # Nome bonito para cabeçalho
    modelo = info_arquivo.get("modelo", "N/D")
    op = info_arquivo.get("operacao", "N/D")
    data_ = info_arquivo.get("data_arquivo", "N/D")
    hora_ = info_arquivo.get("hora_arquivo", "N/D")

    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20,
                            topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,  # centro
        spaceAfter=10,
    )

    elements = []

    titulo = f"Relatório - Modelo {modelo} | OP {op} | {data_} {hora_}"
    elements.append(Paragraph(titulo, style_title))
    elements.append(Spacer(1, 0.2 * inch))

    # Tabela
    data_table = [list(df.columns)] + df.astype(str).values.tolist()

    table = Table(data_table, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def gerar_excel_df(df: pd.DataFrame) -> BytesIO:
    """Gera um Excel a partir do DataFrame."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")
    buffer.seek(0)
    return buffer


def nome_arquivo_export(info_arquivo: dict, extensao: str) -> str:
    """
    Monta o nome do arquivo de exportação.
    Exemplo:
        Maquina_FTA987BR_OP987_08-03-2026_09-39h.pdf
    """
    modelo = info_arquivo.get("modelo", "MODEL")
    op = info_arquivo.get("operacao", "0000")
    data_ = info_arquivo.get("data_arquivo", "DATA")
    hora_ = info_arquivo.get("hora_arquivo", "HORA")

    data_clean = data_.replace("/", "-")
    hora_clean = hora_.replace(":", "-").replace("h", "")
    return f"Maquina_{modelo}_OP{op}_{data_clean}_{hora_clean}.{extensao}"


# -------------------------------------------------
# Carregar lista de arquivos
# -------------------------------------------------
todos_arquivos_info = listar_arquivos_csv()

# -------------------------------------------------
# Barra lateral: logo e filtros
# -------------------------------------------------
with st.sidebar:
    st.image(
        "LOGO-FROMTHERM.png",
        use_column_width=True,
    )
    st.markdown("### FromTherm")

    # Se não houver arquivos, finaliza mais amigável
    if not todos_arquivos_info:
        st.error("Nenhum arquivo CSV encontrado na pasta de dados.")
    else:
        modelos = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D"})
        anos = sorted({a["data"].year for a in todos_arquivos_info if a["data"] is not None})
        meses = list(range(1, 13))
        operacoes = sorted({a["operacao"] for a in todos_arquivos_info if a["operacao"] != "N/D"})

        st.markdown("### Filtros de Pesquisa")

        modelo_filtro = st.selectbox("Modelo", ["Todos"] + modelos, index=0)
        ano_filtro = st.selectbox("Ano", ["Todos"] + anos, index=0)
        mes_filtro = st.selectbox("Mês", ["Todos"] + meses, index=0)
        op_filtro = st.selectbox("Operação", ["Todos"] + operacoes, index=0)

# Filtra a lista de arquivos conforme filtros
def passa_filtro(info: dict) -> bool:
    if modelo_filtro != "Todos" and info["modelo"] != modelo_filtro:
        return False
    if ano_filtro != "Todos":
        if info["data"] is None or info["data"].year != ano_filtro:
            return False
    if mes_filtro != "Todos":
        if info["data"] is None or info["data"].month != mes_filtro:
            return False
    if op_filtro != "Todos" and info["operacao"] != op_filtro:
        return False
    return True


arquivos_filtrados = [a for a in todos_arquivos_info if passa_filtro(a)]

# -------------------------------------------------
# Layout principal com abas
# -------------------------------------------------
tab_dashboard, tab_graficos = st.tabs(["Dashboard", "Crie Seu Gráfico"])

# =================================================
# ABA 1 - DASHBOARD
# =================================================
with tab_dashboard:
    st.title("Máquina de Teste Fromtherm")

    if arquivos_filtrados:
        info_ultimo_arquivo = arquivos_filtrados[0]  # mais recente dentro do filtro
    elif todos_arquivos_info:
        info_ultimo_arquivo = todos_arquivos_info[0]  # geral
    else:
        info_ultimo_arquivo = None

    df_ultimo = None
    if info_ultimo_arquivo is not None:
        df_ultimo = carregar_csv_caminho(info_ultimo_arquivo["caminho"])

    # ----------------------
    # Cards de última leitura
    # ----------------------
    st.subheader("Última Leitura (Atualizada)")

    if df_ultimo is not None and not df_ultimo.empty:
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
            exibir_card("T-Entrada", mostra_valor(df_ultimo, "Entrada"), "°C", "bi bi-arrow-down-circle")
        with col3:
            exibir_card("T-Saída", mostra_valor(df_ultimo, "Saída"), "°C", "bi bi-arrow-up-circle", icon_color="red")
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
        st.info("Não foi possível carregar a última leitura. Verifique se há arquivos CSV válidos.")

    st.markdown("---")
    st.header("Históricos Disponíveis")

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arq in arquivos_filtrados:
            label_exp = (
                f"{arq['nome_arquivo']} "
                f"(Modelo: {arq['modelo']}, OP: {arq['operacao']}, "
                f"Data: {arq['data_arquivo']} {arq['hora_arquivo']})"
            )
            with st.expander(label_exp, expanded=False):
                st.write(f"**Caminho:** {arq['caminho']}")
                st.write(
                    f"**Data modificação:** "
                    f"{arq['data_modificacao'].strftime('%d/%m/%Y %H:%M:%S')}"
                )

                df_hist = carregar_csv_caminho(arq["caminho"])
                if df_hist is None or df_hist.empty:
                    st.warning("Não foi possível carregar ou o arquivo está vazio.")
                else:
                    st.dataframe(df_hist, use_container_width=True)

                    # Botões de download
                    col_pdf, col_xls = st.columns(2)
                    with col_pdf:
                        pdf_buffer = gerar_pdf_df(df_hist, arq)
                        nome_pdf = nome_arquivo_export(arq, "pdf")
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=nome_pdf,
                            mime="application/pdf",
                        )
                    with col_xls:
                        xls_buffer = gerar_excel_df(df_hist)
                        nome_xls = nome_arquivo_export(arq, "xlsx")
                        st.download_button(
                            label="Baixar Excel",
                            data=xls_buffer,
                            file_name=nome_xls,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

# =================================================
# ABA 2 - GRÁFICOS
# =================================================
with tab_graficos:
    st.header("Crie Seu Gráfico")

    if not todos_arquivos_info:
        st.info("Nenhum dado disponível para gerar gráficos.")
    else:
        modelos_graf = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D"})
        modelo_graf = st.selectbox("Modelo", modelos_graf)

        ops_modelo = sorted({a["operacao"] for a in todos_arquivos_info if a["modelo"] == modelo_graf})
        op_graf = st.selectbox("Operação", ops_modelo)

        arquivos_graf = [
            a for a in todos_arquivos_info
            if a["modelo"] == modelo_graf and a["operacao"] == op_graf and a["data"] is not None
        ]

        if not arquivos_graf:
            st.warning("Não há arquivos válidos para esse modelo/OP.")
        else:
            anos_graf = sorted({a["data"].year for a in arquivos_graf})
            ano_graf = st.selectbox("Ano", anos_graf)

            meses_graf = sorted({a["data"].month for a in arquivos_graf if a["data"].year == ano_graf})
            mes_graf = st.selectbox("Mês", meses_graf)

            arq_escolhido = None
            for a in arquivos_graf:
                if a["data"].year == ano_graf and a["data"].month == mes_graf:
                    arq_escolhido = a
                    break

            if arq_escolhido is None:
                st.warning("Nenhum arquivo encontrado para esse modelo/OP/ano/mês.")
            else:
                df_graf = carregar_csv_caminho(arq_escolhido["caminho"])
                if df_graf is None or df_graf.empty:
                    st.warning("Arquivo selecionado está vazio ou não pôde ser lido.")
                else:
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