import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import plotly.express as px

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# =========================
#  CSS GLOBAL E ESTILIZAÇÃO
# =========================
st.markdown(
    """
    <style>
    .stApp { background-color: #f4f6f9; }
    .main > div {
        background-color: #ffffff;
        padding: 10px 25px 40px 25px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-top: 5px;
    }
    h1 { color: #003366 !important; font-weight: 800 !important; }
    div[data-testid="stAppViewContainer"] > div:first-child span {
        font-size: 0px !important; color: transparent !important;
    }
    /* Estilo dos Cards do Painel */
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
        animation: ft-pulse 1.5s ease-in-out infinite;
    }
    .ft-card-content { display: flex; flex-direction: column; }
    .ft-card-title { font-size: 13px; font-weight: 600; color: #444444; margin: 0; }
    .ft-card-value { font-size: 18px; font-weight: 700; color: #111111; margin: 0; }
    @keyframes ft-pulse {
        0%   { transform: scale(1); opacity: 0.9; }
        50%  { transform: scale(1.10); opacity: 1; }
        100% { transform: scale(1); opacity: 0.9; }
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")
st.title("Máquina de Teste Fromtherm")

# --- Configuração de Caminho ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# =========================
#  FUNÇÕES AUXILIARES
# =========================

def criar_pdf_paisagem(df, info):
    """Gera um PDF em formato paisagem com os dados do teste."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Cabeçalho do PDF
    titulo = f"Relatório de Teste - Modelo: {info['modelo']} (OP: {info['operacao']})"
    elements.append(Paragraph(titulo, styles['Title']))
    elements.append(Spacer(1, 12))

    # Tabela de Dados
    data = [df.columns.tolist()] + df.values.tolist()
    t = Table(data, hAlign='CENTER')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

@st.cache_data(ttl=10)
def listar_arquivos_csv():
    if not os.path.exists(DADOS_DIR): return []
    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []
    for caminho in arquivos:
        nome = os.path.basename(caminho)
        try:
            partes = nome.replace(".csv", "").split("_")
            if len(partes) >= 6:
                data = datetime.strptime(partes[2], "%Y%m%d").date()
                info_arquivos.append({
                    "nome_arquivo": nome, "caminho": caminho, "linha": partes[1],
                    "data": data, "ano": data.year, "mes": data.month,
                    "hora": f"{partes[3][:2]}:{partes[3][2:]}", "operacao": partes[4], "modelo": partes[5]
                })
        except: pass
    return info_arquivos

def carregar_csv_caminho(caminho):
    try:
        df = pd.read_csv(caminho, sep=";", engine="python")
    except:
        df = pd.read_csv(caminho, sep=",", engine="python")

    # Padronização de Colunas (Garante que o código não quebre se o CSV mudar)
    colunas_esperadas = ["Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]
    if len(df.columns) == len(colunas_esperadas):
        df.columns = colunas_esperadas
    return df

# --- Execução Principal ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo encontrado em '{DADOS_DIR}'.")
    st.stop()

# Painel de última leitura
arquivo_mais_recente = max(todos_arquivos_info, key=lambda x: (x["data"], x["hora"]))
df_recente = carregar_csv_caminho(arquivo_mais_recente["caminho"])
ultima_linha = df_recente.iloc[-1]

st.markdown(f"### Última Leitura: **{arquivo_mais_recente['modelo']}** (OP: {arquivo_mais_recente['operacao']})")
cols = st.columns(4)
metrics = [
    ("T-Ambiente", ultima_linha['Ambiente'], "bi-thermometer-half"),
    ("T-Entrada", ultima_linha['Entrada'], "bi-arrow-down-circle"),
    ("T-Saída", ultima_linha['Saída'], "bi-arrow-up-circle"),
    ("COP", ultima_linha['COP'], "bi-speedometer2")
]

for i, (label, val, icon) in enumerate(metrics):
    cols[i % 4].markdown(f"""
        <div class="ft-card">
            <i class="bi {icon} ft-card-icon"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{label}</p>
                <p class="ft-card-value">{val}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- TABS ---
tab_hist, tab_graf = st.tabs(["📄 Históricos", "📊 Gráficos"])

with tab_hist:
    # Filtros Simplificados na Sidebar
    st.sidebar.header("Filtros")
    f_modelo = st.sidebar.selectbox("Modelo:", ["Todos"] + sorted(list({a['modelo'] for a in todos_arquivos_info})))

    arquivos_filtrados = [a for a in todos_arquivos_info if f_modelo == "Todos" or a['modelo'] == f_modelo]
    arquivos_filtrados.sort(key=lambda x: (x['data'], x['hora']), reverse=True)

    for i, arq in enumerate(arquivos_filtrados):
        with st.expander(f"📂 {arq['data']} - {arq['hora']} | {arq['modelo']} | OP: {arq['operacao']}"):
            df_item = carregar_csv_caminho(arq['caminho'])
            st.dataframe(df_item, use_container_width=True)

            c1, c2 = st.columns(2)
            # Exportar Excel
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df_item.to_excel(writer, index=False)
            c1.download_button("📥 Excel", output_excel.getvalue(), f"{arq['nome_arquivo']}.xlsx", key=f"ex_{i}")

            # Exportar PDF
            pdf_buf = criar_pdf_paisagem(df_item, arq)
            c2.download_button("📥 PDF", pdf_buf, f"{arq['nome_arquivo']}.pdf", key=f"pdf_{i}")

with tab_graf:
    st.subheader("Análise Gráfica")
    arq_graf_nome = st.selectbox("Selecione o teste pelo arquivo:", [a['nome_arquivo'] for a in arquivos_filtrados])
    arq_graf_info = next(a for a in todos_arquivos_info if a['nome_arquivo'] == arq_graf_nome)

    df_plot_raw = carregar_csv_caminho(arq_graf_info['caminho'])
    df_plot_raw["DateTime"] = df_plot_raw["Time"] # Simplificado para o eixo X

    vars_plot = st.multiselect("Variáveis:", ["Ambiente", "Entrada", "Saída", "ΔT", "COP", "kW Consumo"], default=["Entrada", "Saída"])

    if vars_plot:
        fig = px.line(df_plot_raw, x="DateTime", y=vars_plot, title=f"Desempenho - {arq_graf_info['modelo']}")
        st.plotly_chart(fig, use_container_width=True)