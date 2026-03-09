import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import plotly.express as px
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# =========================
#  CSS GLOBAL
# =========================
st.markdown(
    """
    <style>
    .stApp { background-color: #f4f6f9; }
    .main > div {
        background-color: #ffffff;
        padding: 10px 25px 40px 25px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    h1 { color: #003366 !important; font-weight: 800 !important; }
    div[data-testid="stAppViewContainer"] > div:first-child span { font-size: 0px !important; color: transparent !important; }
    .ft-card {
        background: #ffffff; border-radius: 12px; padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08); display: flex;
        align-items: center; margin-bottom: 10px; border-left: 4px solid #0d6efd;
    }
    .ft-card-icon { font-size: 26px; margin-right: 10px; color: #0d6efd; animation: ft-pulse 1.5s ease-in-out infinite; }
    .ft-card-content { display: flex; flex-direction: column; }
    .ft-card-title { font-size: 13px; font-weight: 600; color: #444444; margin: 0; }
    .ft-card-value { font-size: 18px; font-weight: 700; color: #111111; margin: 0; }
    @keyframes ft-pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net">
    """,
    unsafe_allow_html=True,
)

# --- Funções de Exportação ---
def gerar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados_Teste')
    return output.getvalue()

def gerar_pdf(df, info):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Cabeçalho
    elements.append(Paragraph(f"Relatorio de Teste - Fromtherm", styles['Title']))
    elements.append(Paragraph(f"Modelo: {info['modelo']} | OP: {info['operacao']}", styles['Normal']))
    elements.append(Paragraph(f"Data: {info['data'].strftime('%d/%m/%Y')} | Hora: {info['hora']}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Tabela de dados (últimas 20 linhas para o PDF não ficar gigante)
    data = [df.columns.to_list()] + df.tail(20).values.tolist()
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

# --- Pasta de dados ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=60)
def listar_arquivos_csv():
    if not os.path.exists(DADOS_DIR): return []
    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []
    for caminho in arquivos:
        nome = os.path.basename(caminho)
        try:
            partes = nome.replace(".csv", "").split("_")
            if len(partes) >= 6:
                data_obj = datetime.strptime(partes[2], "%Y%m%d").date()
                info_arquivos.append({
                    "nome_exibicao": f"{partes[5]} - {partes[4]} ({data_obj.strftime('%d/%m/%Y')})",
                    "caminho": caminho, "modelo": partes[5], "operacao": partes[4],
                    "data": data_obj, "hora": f"{partes[3][:2]}:{partes[3][2:]}",
                    "timestamp": datetime.strptime(f"{partes[2]}{partes[3]}", "%Y%m%d%H%M")
                })
        except: pass
    return sorted(info_arquivos, key=lambda x: x["timestamp"], reverse=True)

def carregar_csv(caminho):
    try: df = pd.read_csv(caminho, sep=";", engine="python")
    except: df = pd.read_csv(caminho, sep=",", engine="python")
    df.columns = ["Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]
    for col in df.columns[2:]:
        if df[col].dtype == 'object': df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
    return df

# --- Lógica Principal ---
lista_testes = listar_arquivos_csv()
if not lista_testes:
    st.warning("Nenhum dado encontrado."); st.stop()

st.sidebar.image("https://fromtherm.com.br", use_container_width=True)
teste_selecionado = st.sidebar.selectbox("Selecione o Teste:", options=lista_testes, format_func=lambda x: x["nome_exibicao"])

df_dados = carregar_csv(teste_selecionado["caminho"])
ultima = df_dados.iloc[-1]

# --- Botões de Exportação na Sidebar ---
st.sidebar.markdown("---")
st.sidebar.subheader("Exportar Dados")
col_pdf, col_xls = st.sidebar.columns(2)

with col_pdf:
    pdf_bytes = gerar_pdf(df_dados, teste_selecionado)
    st.download_button("📄 PDF", data=pdf_bytes, file_name=f"Relatorio_{teste_selecionado['operacao']}.pdf", mime="application/pdf")

with col_xls:
    xls_bytes = gerar_excel(df_dados)
    st.download_button("📊 Excel", data=xls_bytes, file_name=f"Dados_{teste_selecionado['operacao']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Dashboard ---
st.title("Máquina de Teste Fromtherm")
st.info(f"**Visualizando:** {teste_selecionado['modelo']} | **OP:** {teste_selecionado['operacao']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="ft-card"><i class="bi bi-thermometer-half ft-card-icon"></i><div class="ft-card-content"><p class="ft-card-title">T-Ambiente</p><p class="ft-card-value">{ultima["Ambiente"]:.1f}°C</p></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ft-card" style="border-left-color: #dc3545;"><i class="bi bi-arrow-up-circle ft-card-icon" style="color: #dc3545;"></i><div class="ft-card-content"><p class="ft-card-title">T-Saída</p><p class="ft-card-value" style="color: #dc3545;">{ultima["Saída"]:.1f}°C</p></div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="ft-card" style="border-left-color: #198754;"><i class="bi bi-lightning-charge ft-card-icon" style="color: #198754;"></i><div class="ft-card-content"><p class="ft-card-title">COP</p><p class="ft-card-value">{ultima["COP"]:.2f}</p></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ft-card"><i class="bi bi-water ft-card-icon"></i><div class="ft-card-content"><p class="ft-card-title">Vazão</p><p class="ft-card-value">{ultima["Vazão"]:.0f} L/h</p></div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="ft-card" style="border-left-color: #ffc107;"><i class="bi bi-cpu ft-card-icon" style="color: #ffc107;"></i><div class="ft-card-content"><p class="ft-card-title">Tensão</p><p class="ft-card-value">{ultima["Tensão"]:.0f}V</p></div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ft-card" style="border-left-color: #ffc107;"><i class="bi bi-speedometer2 ft-card-icon" style="color: #ffc107;"></i><div class="ft-card-content"><p class="ft-card-title">Consumo</p><p class="ft-card-value">{ultima["kW Consumo"]:.2f}kW</p></div></div>', unsafe_allow_html=True)

fig = px.line(df_dados, x="Time", y=["Entrada", "Saída", "Ambiente"], color_discrete_map={"Entrada": "#0d6efd", "Saída": "#dc3545", "Ambiente": "#6c757d"}, template="plotly_white")
st.plotly_chart(fig, use_container_width=True)
