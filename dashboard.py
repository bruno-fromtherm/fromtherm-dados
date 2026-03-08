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
from reportlab.lib.units import inch   # <- ESSENCIAL para o Spacer

from io import BytesIO
import plotly.express as px

# -------------------------------------------------
# Configuração básica
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS simples (mantém layout, não mexe em nada estrutural)
# -------------------------------------------------
st.markdown(
    """
    <style>
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd;
    }
    .ft-card-icon.red {
        color: #dc3545;
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
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Funções auxiliares
# -------------------------------------------------

DADOS_DIR = os.path.join(
    ".", "dados_brutos", "historico_L1", "IP_registro192.168.2.150", "datalog"
)

def extrair_info_nome_arquivo(nome_arquivo: str) -> dict:
    """
    Extrai modelo, data, hora e operação do nome do arquivo.
    Exemplo: historico_L1_20250308_0939_OP0987_FTA987BR.csv
    """
    modelo = ""
    data_str = ""
    hora_str = ""
    op = ""

    padrao = r"historico_L1_(\d{8})_(\d{4})_OP([A-Za-z0-9]+)_([A-Za-z0-9]+)\.csv"
    m = re.match(padrao, nome_arquivo)
    if m:
        data_str = m.group(1)   # 20250308
        hora_str = m.group(2)   # 0939
        op = m.group(3)         # OP0987 (ou apenas 0987, depende de como foi salvo)
        modelo = m.group(4)     # FTA987BR

    data_arquivo = ""
    try:
        if data_str:
            data_dt = datetime.strptime(data_str, "%Y%m%d")
            data_arquivo = data_dt.strftime("%d/%m/%Y")
    except Exception:
        data_arquivo = ""

    hora_arquivo = ""
    try:
        if hora_str:
            hora_arquivo = f"{hora_str[:2]}:{hora_str[2:]}"
    except Exception:
        hora_arquivo = ""

    return {
        "modelo": modelo,
        "data_arquivo": data_arquivo,
        "hora_arquivo": hora_arquivo,
        "operacao": op,
    }

def listar_arquivos_csv():
    """
    Lista todos os arquivos CSV na pasta DADOS_DIR, com informações básicas.
    """
    if not os.path.isdir(DADOS_DIR):
        return []

    caminhos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))

    arquivos_info = []
    for c in caminhos:
        nome = os.path.basename(c)
        info = extrair_info_nome_arquivo(nome)
        try:
            mtime = os.path.getmtime(c)
            dt_mod = datetime.fromtimestamp(mtime)
        except Exception:
            dt_mod = None

        arquivos_info.append(
            {
                "caminho": c,
                "nome_arquivo": nome,
                "modelo": info["modelo"],
                "data_arquivo": info["data_arquivo"],
                "hora_arquivo": info["hora_arquivo"],
                "operacao": info["operacao"],
                "data_modificacao": dt_mod,
            }
        )

    arquivos_info = [a for a in arquivos_info if a["data_modificacao"] is not None]
    arquivos_info.sort(key=lambda x: x["data_modificacao"], reverse=True)
    return arquivos_info

def carregar_csv_caminho(caminho: str) -> pd.DataFrame | None:
    """
    Lê um CSV e garante colunas esperadas, quando possível.
    """
    try:
        df = pd.read_csv(caminho, sep=";", decimal=",")
    except Exception:
        try:
            df = pd.read_csv(caminho)
        except Exception:
            return None

    # Cria coluna DateTime se houver colunas de data/hora conhecidas
    if "Data" in df.columns and "Hora" in df.columns:
        try:
            df["DateTime"] = pd.to_datetime(df["Data"] + " " + df["Hora"])
        except Exception:
            pass

    return df

def mostra_valor(df: pd.DataFrame | None, coluna: str, casa_decimal: int = 1):
    """
    Tenta pegar o último valor de uma coluna numérica.
    """
    if df is None or df.empty:
        return "N/D"
    if coluna not in df.columns:
        return "N/D"
    serie = df[coluna].dropna()
    if serie.empty:
        return "N/D"
    try:
        v = float(serie.iloc[-1])
        return f"{v:.{casa_decimal}f}"
    except Exception:
        return "N/D"

def exibir_card(titulo: str, valor: str, unidade: str, icone: str, vermelho=False):
    col_class = "ft-card-icon red" if vermelho else "ft-card-icon"
    st.markdown(
        f"""
        <div class="ft-card">
            <div class="{col_class}">{icone}</div>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor} {unidade}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def criar_pdf(df: pd.DataFrame, info_arq: dict) -> BytesIO:
    """
    Gera um PDF em memória com base no DataFrame e nas infos do arquivo.
    Usa 'inch' corretamente.
    """
    buffer = BytesIO()

    nome_modelo = info_arq.get("modelo", "MODELO")
    op = info_arq.get("operacao", "OP")
    data_str = info_arq.get("data_arquivo", "DATA")
    hora_str = info_arq.get("hora_arquivo", "HORA")

    # Nome “bonito” no título interno, o nome do arquivo o Streamlit define na hora do download
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "Titulo",
        parent=styles["Heading1"],
        alignment=1,
        fontSize=16,
        spaceAfter=10,
    )
    style_normal = styles["Normal"]

    elements = []
    titulo = f"Máquina {nome_modelo} - OP {op} - Data {data_str} - Hora {hora_str}"
    elements.append(Paragraph(titulo, style_title))
    elements.append(Spacer(1, 0.2 * inch))

    # Tabela com os dados
    dados = [list(df.columns)] + df.astype(str).values.tolist()
    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(tabela)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# Carregamento inicial
# -------------------------------------------------
todos_arquivos_info = listar_arquivos_csv()
arquivo_mais_recente = todos_arquivos_info[0] if todos_arquivos_info else None
df_ultimo = carregar_csv_caminho(arquivo_mais_recente["caminho"]) if arquivo_mais_recente else None

# -------------------------------------------------
# SIDEBAR (logo + filtros)
# -------------------------------------------------
with st.sidebar:
    # Logo: se não achar, não quebra
    try:
        st.image("LOGO-FROMTHERM.png", use_column_width=True)
    except Exception:
        st.write("FromTherm")

    st.markdown("### Filtros de Pesquisa")
    modelos_disp = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"]})
    anos_disp = sorted({a["data_arquivo"][-4:] for a in todos_arquivos_info if a["data_arquivo"]})

    modelo_filtro = st.selectbox("Filtrar por Modelo:", ["Todos"] + modelos_disp)
    ano_filtro = st.selectbox("Filtrar por Ano:", ["Todos"] + anos_disp)
    mes_filtro = st.selectbox("Filtrar por Mês:", ["Todos"] + [f"{m:02d}" for m in range(1, 13)])
    data_filtro = st.text_input("Filtrar por Data (DD/MM/AAAA):", "")
    op_filtro = st.text_input("Filtrar por Operação:", "")

# -------------------------------------------------
# Título principal
# -------------------------------------------------
st.title("Máquina de Teste Fromtherm")

# -------------------------------------------------
# Abas
# -------------------------------------------------
tab_dash, tab_graf = st.tabs(["Dashboard", "Crie Seu Gráfico"])

with tab_dash:
    # ---- Última Leitura Atualizada (cards) ----
    st.subheader("Última Leitura Atualizada")

    if arquivo_mais_recente and df_ultimo is not None and not df_ultimo.empty:
        modelo_texto = arquivo_mais_recente["modelo"] or "N/D"
        op_texto = arquivo_mais_recente["operacao"] or "N/D"
        data_texto = arquivo_mais_recente["data_arquivo"] or "N/D"
        hora_texto = arquivo_mais_recente["hora_arquivo"] or "N/D"

        st.markdown(
            f"**Modelo:** {modelo_texto} | **OP:** {op_texto} | "
            f"**Data:** {data_texto} | **Hora:** {hora_texto}"
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            c11, c12 = st.columns(2)
            with c11:
                exibir_card("T-Ambiente", mostra_valor(df_ultimo, "Ambiente"), "°C", "🌡️")
                exibir_card("Tensão", mostra_valor(df_ultimo, "Tensao"), "V", "⚡")
                exibir_card("kW Aquecimento", mostra_valor(df_ultimo, "KWAquecimento"), "kW", "☀️")
            with c12:
                exibir_card("DIF (ΔT)", mostra_valor(df_ultimo, "DeltaT"), "°C", "↕️")
                exibir_card("kcal/h", mostra_valor(df_ultimo, "Kcal_h"), "", "💧")
                exibir_card("kW Consumo", mostra_valor(df_ultimo, "KWConsumo"), "kW", "🔌")
        with c2:
            c21, c22 = st.columns(2)
            with c21:
                exibir_card("T-Entrada", mostra_valor(df_ultimo, "Entrada"), "°C", "🔵")
                exibir_card("Corrente", mostra_valor(df_ultimo, "Corrente"), "A", "⚡")
            with c22:
                exibir_card("T-Saída", mostra_valor(df_ultimo, "Saída"), "°C", "🔴")
                exibir_card("Vazão", mostra_valor(df_ultimo, "Vazao"), "L/min", "≋")
        with c3:
            exibir_card("COP", mostra_valor(df_ultimo, "COP"), "", "📈", vermelho=False)
    else:
        st.info("Não foi possível carregar a última leitura. Verifique se há arquivos CSV válidos.")

    st.markdown("---")
    st.subheader("Históricos Disponíveis")

    # ---- Filtro sobre a lista de arquivos ----
    arquivos_filtrados = todos_arquivos_info
    if modelo_filtro != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == modelo_filtro]
    if ano_filtro != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"].endswith(ano_filtro)]
    if mes_filtro != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"][3:5] == mes_filtro]
    if data_filtro:
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data_arquivo"] == data_filtro]
    if op_filtro:
        arquivos_filtrados = [a for a in arquivos_filtrados if op_filtro.lower() in a["operacao"].lower()]

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arq in arquivos_filtrados:
            label = (
                f"{arq['modelo']} - Data: {arq['data_arquivo']} - "
                f"Hora: {arq['hora_arquivo']} - Operação: {arq['operacao']}"
            )
            with st.expander(label):
                st.write(f"Arquivo: `{arq['nome_arquivo']}`")
                st.write(f"Modificado em: {arq['data_modificacao']}")

                df_exibir = carregar_csv_caminho(arq["caminho"])
                if df_exibir is None or df_exibir.empty:
                    st.warning("Arquivo vazio ou não pôde ser lido.")
                else:
                    st.dataframe(df_exibir, use_container_width=True)

                    # --- Download Excel ---
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                        df_exibir.to_excel(writer, index=False, sheet_name="Dados")
                    excel_buffer.seek(0)

                    nome_modelo = arq.get("modelo", "MODELO")
                    op = arq.get("operacao", "OP")
                    data_str = arq.get("data_arquivo", "DATA")
                    hora_str = arq.get("hora_arquivo", "HORA").replace(":", "h")

                    nome_excel = f"Maquina_{nome_modelo}_OP{op}_{data_str}_{hora_str}.xlsx"

                    st.download_button(
                        label="Baixar Excel",
                        data=excel_buffer,
                        file_name=nome_excel,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                    # --- Download PDF ---
                    pdf_buffer = criar_pdf(df_exibir, arq)
                    nome_pdf = f"Maquina_{nome_modelo}_OP{op}_{data_str}_{hora_str}.pdf"
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_buffer,
                        file_name=nome_pdf,
                        mime="application/pdf",
                    )

with tab_graf:
    st.subheader("Crie Seu Gráfico")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo disponível para gerar gráficos.")
    else:
        modelos_graf = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"]})
        modelo_graf = st.selectbox("Modelo:", modelos_graf)

        ops_graf = sorted({a["operacao"] for a in todos_arquivos_info if a["modelo"] == modelo_graf})
        op_graf = st.selectbox("Operação (OP):", ops_graf)

        datas_disp = [
            a["data_arquivo"]
            for a in todos_arquivos_info
            if a["modelo"] == modelo_graf and a["operacao"] == op_graf
        ]
        data_graf = st.selectbox("Data:", sorted(set(datas_disp)))

        arq_escolhido = None
        for a in todos_arquivos_info:
            if (
                a["modelo"] == modelo_graf
                and a["operacao"] == op_graf
                and a["data_arquivo"] == data_graf
            ):
                arq_escolhido = a
                break

        if arq_escolhido is None:
            st.warning("Nenhum arquivo encontrado para esse modelo/OP/data.")
        else:
            df_graf = carregar_csv_caminho(arq_escolhido["caminho"])
            if df_graf is None or df_graf.empty:
                st.warning("Arquivo selecionado vazio ou ilegível.")
            else:
                opcoes_variaveis = [
                    "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                    "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
                ]
                opcoes_variaveis_existentes = [c for c in opcoes_variaveis if c in df_graf.columns]

                vars_sel = st.multiselect(
                    "Variáveis para plotar:",
                    opcoes_variaveis_existentes,
                    default=[v for v in ["Ambiente", "Entrada", "Saída"] if v in opcoes_variaveis_existentes],
                )
                if not vars_sel:
                    st.info("Selecione pelo menos uma variável.")
                else:
                    df_melted = df_graf[["DateTime"] + vars_sel].melt(
                        id_vars="DateTime",
                        value_vars=vars_sel,
                        var_name="Variável",
                        value_name="Valor",
                    )
                    fig = px.line(
                        df_melted,
                        x="DateTime",
                        y="Valor",
                        color="Variável",
                        title=f"Modelo {modelo_graf} | OP {op_graf} | {data_graf}",
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