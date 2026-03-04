import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Planilha Teste de Máquinas Fromtherm",
    page_icon="🏭",
    layout="wide"
)

# ============================================================
# CONFIGURAÇÕES GITHUB
# ============================================================
GITHUB_USER   = "bruno-fromtherm"
GITHUB_REPO   = "fromtherm-dados"
GITHUB_BRANCH = "main"
GITHUB_PATH   = "dados"

API_BASE = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_PATH}?ref={GITHUB_BRANCH}"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_PATH}"

# ============================================================
# LOGIN
# ============================================================
credentials = {
    "usernames": {
        "operador": {
            "name": "Operador",
            "password": "123456",
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "fromtherm_cookie",
    "chave_secreta_fromtherm_2026",
    cookie_expiry_days=1
)

authenticator.login(location="main")

authentication_status = st.session_state.get("authentication_status")

if authentication_status is False:
    st.error("Usuário ou senha incorretos.")
    st.stop()

if authentication_status is None:
    st.warning("Digite usuário e senha para acessar.")
    st.info("Usuário: operador  |  Senha: 123456")
    st.stop()

# ============================================================
# AUTO-REFRESH (a cada 10 segundos)
# ============================================================
st_autorefresh(interval=10000, limit=None, key="autorefresh_fromtherm")

# ============================================================
# FUNÇÕES — EXCEL / PDF / NOME
# ============================================================
def nome_exportacao(info, extensao):
    data   = info.get("Data",     "00/00/0000").replace("/", "-")
    hora   = info.get("Hora",     "00:00").replace(":", "h")
    op     = info.get("Operação", "OP")
    modelo = info.get("Modelo",   "MDL")
    return f"Maquina_{modelo}_{op}_{data}_{hora}.{extensao}"

def gerar_excel(df, info=None):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        workbook  = writer.book
        worksheet = workbook.add_worksheet("Maquina")
        writer.sheets["Maquina"] = worksheet

        fmt_titulo = workbook.add_format({
            "bold": True, "font_size": 14,
            "font_color": "#FFFFFF", "bg_color": "#003366",
            "align": "center", "valign": "vcenter"
        })
        fmt_label = workbook.add_format({
            "bold": True, "font_size": 10,
            "font_color": "#003366", "bg_color": "#D9E1F2",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        fmt_valor = workbook.add_format({
            "font_size": 10, "bg_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        fmt_header_dados = workbook.add_format({
            "bold": True, "font_size": 9,
            "font_color": "#FFFFFF", "bg_color": "#003366",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        fmt_linha_par = workbook.add_format({
            "font_size": 9, "bg_color": "#E8F0FE",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        fmt_linha_impar = workbook.add_format({
            "font_size": 9, "bg_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        fmt_rodape = workbook.add_format({
            "italic": True, "font_size": 8,
            "font_color": "#888888", "align": "right"
        })

        num_colunas = max(len(df.columns), 1)

        worksheet.merge_range(
            0, 0, 0, num_colunas - 1,
            "Planilha Teste de Máquinas Fromtherm", fmt_titulo
        )
        worksheet.set_row(0, 24)

        if info is not None:
            labels  = ["Data", "Hora", "Operação", "Modelo", "Linha"]
            valores = [
                info.get("Data", "-"), info.get("Hora", "-"),
                info.get("Operação", "-"), info.get("Modelo", "-"),
                info.get("Linha", "-"),
            ]
            bloco = max(num_colunas // len(labels), 1)
            col_atual = 0
            for i, (lbl, val) in enumerate(zip(labels, valores)):
                col_fim = col_atual + bloco - 1
                if i == len(labels) - 1:
                    col_fim = num_colunas - 1
                worksheet.merge_range(1, col_atual, 1, col_fim, lbl, fmt_label)
                worksheet.merge_range(2, col_atual, 2, col_fim, val, fmt_valor)
                col_atual = col_fim + 1

        worksheet.set_row(1, 18)
        worksheet.set_row(2, 18)
        worksheet.set_row(3, 6)

        for col_num, col_name in enumerate(df.columns):
            worksheet.write(4, col_num, col_name, fmt_header_dados)
            worksheet.set_column(col_num, col_num, 14)
        worksheet.set_row(4, 18)

        for row_idx, (_, row) in enumerate(df.iterrows()):
            fmt = fmt_linha_par if row_idx % 2 == 0 else fmt_linha_impar
            for col_num, value in enumerate(row):
                worksheet.write(5 + row_idx, col_num, value, fmt)
            worksheet.set_row(5 + row_idx, 16)

        ultima_linha = 5 + len(df)
        worksheet.merge_range(
            ultima_linha + 1, 0, ultima_linha + 1, num_colunas - 1,
            f"Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}  |  Fromtherm © 2026",
            fmt_rodape
        )

    buf.seek(0)
    return buf

def gerar_pdf(df, info=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=20, leftMargin=20,
        topMargin=30, bottomMargin=20
    )
    styles    = getSampleStyleSheet()
    elementos = []

    estilo_titulo = styles["Title"].clone("titulo_from")
    estilo_titulo.textColor = colors.HexColor("#003366")
    estilo_titulo.fontSize  = 16
    elementos.append(Paragraph("Planilha Teste de Máquinas Fromtherm", estilo_titulo))
    elementos.append(Spacer(1, 8))

    if info is not None:
        dados_info = [
            ["Data", "Hora", "Operação", "Modelo", "Linha"],
            [
                info.get("Data", "-"), info.get("Hora", "-"),
                info.get("Operação", "-"), info.get("Modelo", "-"),
                info.get("Linha", "-"),
            ]
        ]
        largura_info = (landscape(A4)[0] - 40) / 5
        tab_info = Table(dados_info, colWidths=[largura_info] * 5)
        tab_info.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#003366")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("BACKGROUND",    (0, 1), (-1, 1),  colors.HexColor("#D9E1F2")),
            ("FONTNAME",      (0, 1), (-1, 1),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 1), (-1, 1),  9),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tab_info)
        elementos.append(Spacer(1, 12))

    colunas = list(df.columns)
    dados   = [colunas]
    for _, row in df.iterrows():
        dados.append([str(v) for v in row.values])

    largura_pagina = landscape(A4)[0] - 40
    largura_col    = largura_pagina / max(len(colunas), 1)

    tab_dados = Table(dados, colWidths=[largura_col] * len(colunas), repeatRows=1)
    tab_dados.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.HexColor("#003366")),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0),  8),
        ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",       (0, 1), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8F0FE")]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tab_dados)
    elementos.append(Spacer(1, 8))

    estilo_rodape = styles["Normal"].clone("rodape_from")
    estilo_rodape.fontSize  = 7
    estilo_rodape.textColor = colors.grey
    elementos.append(Paragraph(
        f"Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}  |  Fromtherm © 2026",
        estilo_rodape
    ))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# ============================================================
# FUNÇÕES — LER DO GITHUB
# ============================================================
@st.cache_data(ttl=10)
def listar_csv_github():
    r = requests.get(API_BASE)
    if r.status_code != 200:
        st.error(f"Erro ao acessar GitHub: {r.status_code}")
        return []

    conteudo = r.json()
    arquivos = [item["name"] for item in conteudo if item["name"].lower().endswith(".csv")]
    resultado = []

    for f in arquivos:
        partes    = f.replace(".csv", "").split("_")
        data_str  = hora_str = numero_op = modelo = linha_str = "-"
        try:
            linha_raw = partes[1] if len(partes) > 1 else "-"
            data_raw  = partes[2] if len(partes) > 2 else "-"
            hora_raw  = partes[3] if len(partes) > 3 else "-"
            numero_op = partes[4] if len(partes) > 4 else "-"
            modelo    = partes[5] if len(partes) > 5 else "-"

            if linha_raw.upper().startswith("L"):
                num = linha_raw[1:]
                linha_str = f"Linha {num.zfill(2)}" if num.isdigit() else linha_raw
            else:
                linha_str = linha_raw

            if len(data_raw) == 8 and data_raw.isdigit():
                data_str = f"{data_raw[6:8]}/{data_raw[4:6]}/{data_raw[0:4]}"
            else:
                data_str = data_raw

            if len(hora_raw) == 4 and hora_raw.isdigit():
                hora_str = f"{hora_raw[0:2]}:{hora_raw[2:4]}"
            else:
                hora_str = hora_raw
        except Exception:
            pass

        resultado.append({
            "Arquivo"  : f,
            "Data"     : data_str,
            "Hora"     : hora_str,
            "Operação" : numero_op,
            "Modelo"   : modelo,
            "Linha"    : linha_str,
        })

    return sorted(resultado, key=lambda x: x["Arquivo"], reverse=True)

@st.cache_data(ttl=10)
def carregar_csv_github(nome_arquivo):
    url = f"{RAW_BASE}/{nome_arquivo}"
    r   = requests.get(url)
    if r.status_code != 200:
        st.error(f"Erro ao baixar arquivo: {r.status_code}")
        return pd.DataFrame()
    content = r.content
    try:
        df = pd.read_csv(BytesIO(content), sep=",", encoding="utf-8", skipinitialspace=True)
    except Exception:
        df = pd.read_csv(BytesIO(content), sep=";", encoding="utf-8-sig", skipinitialspace=True)
    df.columns = df.columns.str.strip()
    cols_internas = [c for c in df.columns if str(c).startswith("_")]
    if cols_internas:
        df = df.drop(columns=cols_internas)
    return df

# ============================================================
# CABEÇALHO
# ============================================================
col_titulo, col_logout = st.columns([8, 1])
with col_titulo:
    st.title("🏭 Planilha Teste de Máquinas Fromtherm")
with col_logout:
    authenticator.logout("Sair", location="main")

st.markdown("---")

# ============================================================
# CARREGAR HISTÓRICO DO GITHUB
# ============================================================
historico = listar_csv_github()

if not historico:
    st.warning("⏳ Nenhum arquivo recebido ainda. Aguardando envio da IHM...")
    st.info("Verifique se o PC da máquina está enviando os dados para o GitHub.")
    st.stop()

df_hist = pd.DataFrame(historico)

# ============================================================
# PESQUISA POR MODELO
# ============================================================
st.markdown("### 🔍 Pesquisar por Modelo da Máquina")

col_p1, col_p2 = st.columns([3, 1])
with col_p1:
    termo = st.text_input(
        "Digite o modelo da máquina:",
        placeholder="Ex: FT185, 180L, FT200..."
    )
with col_p2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Limpar"):
        termo = ""

termo_strip = termo.strip() if termo else ""

if termo_strip:
    mask        = df_hist["Modelo"].str.contains(termo_strip, case=False, na=False)
    df_filtrado = df_hist[mask]
else:
    df_filtrado = df_hist

st.markdown("---")

if df_filtrado.empty:
    st.warning(f"Nenhum arquivo encontrado para o modelo: **{termo_strip}**")
    st.stop()

modelos_disponiveis = df_filtrado["Modelo"].unique().tolist()
st.markdown(
    f"**{len(df_filtrado)} arquivo(s) encontrado(s)** | "
    f"Modelos: `{'`, `'.join(modelos_disponiveis)}`"
)

colunas_tabela = ["Data", "Hora", "Operação", "Modelo", "Linha", "Arquivo"]
st.dataframe(df_filtrado[colunas_tabela], use_container_width=True)

st.markdown("---")

# ============================================================
# SELEÇÃO DO ARQUIVO
# ============================================================
st.markdown("### 📂 Arquivo visualizado")

opcoes             = df_filtrado["Arquivo"].tolist()
arquivo_selecionado = st.selectbox(
    "Selecione o arquivo (padrão: mais recente):",
    options=opcoes,
    index=0
)

# ============================================================
# EXIBIÇÃO
# ============================================================
if arquivo_selecionado:
    info = df_filtrado[df_filtrado["Arquivo"] == arquivo_selecionado].iloc[0].to_dict()

    st.markdown("#### 📋 Informações")
    col_i1, col_i2, col_i3, col_i4, col_i5 = st.columns(5)
    col_i1.metric("📅 Data",     info["Data"])
    col_i2.metric("🕐 Hora",     info["Hora"])
    col_i3.metric("🔢 Operação", info["Operação"])
    col_i4.metric("🏭 Modelo",   info["Modelo"])
    col_i5.metric("📍 Linha",    info["Linha"])

    st.markdown("---")

    df_sel = carregar_csv_github(arquivo_selecionado)

    st.markdown(f"#### 📊 Planilha — `{arquivo_selecionado}`")
    st.dataframe(df_sel, use_container_width=True, height=500)

    st.markdown("---")

    st.markdown("#### ⬇️ Exportar")
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        buf_excel = gerar_excel(df_sel, info=info)
        st.download_button(
            "📊 Baixar Excel",
            data=buf_excel,
            file_name=nome_exportacao(info, "xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col_d2:
        buf_pdf = gerar_pdf(df_sel, info=info)
        st.download_button(
            "📄 Baixar PDF",
            data=buf_pdf,
            file_name=nome_exportacao(info, "pdf"),
            mime="application/pdf",
            use_container_width=True
        )

st.markdown("---")
st.caption("🔄 Atualização automática a cada 10 segundos  |  Fromtherm © 2026")
