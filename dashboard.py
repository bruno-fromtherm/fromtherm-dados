import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados"  # pasta 'dados' no mesmo nível do dashboard.py


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=3600)
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta 'dados'
    e extrai informações básicas do nome:
    historico_L1_20260303_2140_OP1234_FT185.csv
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        linha = ""
        data = None
        hora = ""
        operacao = ""
        modelo = ""

        try:
            partes = nome.replace(".csv", "").split("_")
            if len(partes) >= 6:
                # partes[0] = "historico"
                linha = partes[1]             # L1
                data_str = partes[2]          # 20260303
                hora_str = partes[3]          # 2140
                operacao = partes[4]          # OP1234
                modelo = partes[5]            # FT185

                data = datetime.strptime(data_str, "%Y%m%d").date()
                hora = f"{hora_str[:2]}:{hora_str[2:]}"
        except Exception:
            pass

        info_arquivos.append(
            {
                "nome_arquivo": nome,
                "caminho": caminho,
                "linha": linha,
                "data": data,
                "hora": hora,
                "operacao": operacao,
                "modelo": modelo,
            }
        )

    return info_arquivos


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning("Nenhum arquivo .csv de histórico encontrado na pasta 'dados'.")
    st.info("Coloque os arquivos .csv de histórico dentro da pasta 'dados' do repositório.")
    st.stop()

# --- Filtros na barra lateral ---
st.sidebar.header("Filtros")

modelos_disponiveis = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"]})
modelo_selecionado = st.sidebar.selectbox(
    "Filtrar por Modelo:",
    ["Todos"] + modelos_disponiveis
)

datas_disponiveis = sorted(
    {a["data"] for a in todos_arquivos_info if a["data"]},
    reverse=True,
)
data_selecionada = st.sidebar.date_input(
    "Filtrar por Data:",
    value=None,
    min_value=min(datas_disponiveis) if datas_disponiveis else None,
    max_value=max(datas_disponiveis) if datas_disponiveis else None,
)

# Aplicar filtros
arquivos_filtrados = todos_arquivos_info
if modelo_selecionado != "Todos":
    arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == modelo_selecionado]
if data_selecionada:
    arquivos_filtrados = [a for a in arquivos_filtrados if a["data"] == data_selecionada]

# Ordenar por data e hora (mais recente primeiro)
arquivos_filtrados = sorted(
    arquivos_filtrados,
    key=lambda x: (
        x["data"] if x["data"] else datetime.min.date(),
        x["hora"],
    ),
    reverse=True,
)

st.subheader("Históricos Disponíveis")

if not arquivos_filtrados:
    st.info("Nenhum histórico encontrado com os filtros selecionados.")
    st.stop()


# --- Função para gerar PDF A4 bonito e organizado ---
def criar_pdf_a4(df_dados: pd.DataFrame, meta: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25,
        rightMargin=25,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TitleCenter",
        parent=styles["Title"],
        alignment=1,  # centralizado
        fontSize=16,
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        name="SubTitle",
        parent=styles["Heading2"],
        alignment=0,
        fontSize=11,
        spaceAfter=6,
    )

    story = []

    # Cabeçalho
    story.append(Paragraph("Planilha Teste de Máquinas Fromtherm", title_style))
    story.append(Spacer(1, 8))

    data_str = meta["data"].strftime("%d/%m/%Y") if meta["data"] else "N/D"
    hora_str = meta["hora"] or "N/D"
    operacao_str = meta["operacao"] or "N/D"
    modelo_str = meta["modelo"] or "N/D"
    linha_str = meta["linha"] or "N/D"

    # Tabela de informações em duas linhas (mais limpo)
    info_data = [
        ["Data", data_str, "Hora", hora_str],
        ["Operação", operacao_str, "Modelo", modelo_str],
        ["Linha", linha_str, "", ""],
    ]
    info_table = Table(info_data, colWidths=[60, 120, 60, 120])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 12))

    # Título da tabela de dados
    story.append(Paragraph("Dados da Operação:", subtitle_style))
    story.append(Spacer(1, 6))

    # Tabela dos dados com ajuste de largura de coluna
    cols = list(df_dados.columns)
    data_rows = df_dados.values.tolist()

    # Cabeçalho + linhas
    table_data = [cols] + data_rows

    # Definir larguras aproximadas em pontos (A4 ~ 540 pts de largura útil)
    # Ajuste mais largura para colunas de texto curto, menos para numéricas
    num_cols = len(cols)
    if num_cols <= 8:
        col_widths = [65] + [60] * (num_cols - 1)
    else:
        # Distribuição proporcional
        base = 520 / num_cols
        col_widths = [base] * num_cols

    dados_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    dados_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ]
        )
    )
    story.append(dados_table)
    story.append(Spacer(1, 12))

    # Rodapé simples
    rodape = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Fromtherm © {datetime.now().year}"
    story.append(Paragraph(rodape, styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


# --- Listar cada arquivo filtrado ---
for i, arquivo in enumerate(arquivos_filtrados):
    data_str = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else "sem data"
    titulo_expander = (
        f"**{arquivo['modelo'] or 'Modelo não identificado'}** - "
        f"Linha: {arquivo['linha'] or '-'} - "
        f"Data: {data_str} - Hora: {arquivo['hora'] or '-'} - "
        f"Operação: {arquivo['operacao'] or '-'}"
    )

    with st.expander(titulo_expander):
        try:
            # Lê o CSV que veio da IHM
            df_dados = pd.read_csv(arquivo["caminho"])

            st.subheader("Dados da Operação")
            st.dataframe(df_dados, use_container_width=True)

            # --- Exportar para Excel (organizado) ---
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet("Dados")
                writer.sheets["Dados"] = worksheet

                # Formatos
                title_format = workbook.add_format(
                    {"bold": True, "font_size": 14}
                )
                header_format = workbook.add_format(
                    {
                        "bold": True,
                        "bg_color": "#D9D9D9",
                        "border": 1,
                        "align": "center",
                    }
                )
                cell_format = workbook.add_format(
                    {
                        "border": 1,
                        "align": "center",
                    }
                )

                # Título
                worksheet.merge_range("A1:M1", "Planilha Teste de Máquinas Fromtherm", title_format)

                # Infos (Data, Hora, Operação, Modelo, Linha)
                data_excel = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else ""
                hora_excel = arquivo["hora"] or ""
                oper_excel = arquivo["operacao"] or ""
                modelo_excel = arquivo["modelo"] or ""
                linha_excel = arquivo["linha"] or ""

                worksheet.write("A3", "Data", header_format)
                worksheet.write("B3", data_excel, cell_format)
                worksheet.write("C3", "Hora", header_format)
                worksheet.write("D3", hora_excel, cell_format)
                worksheet.write("E3", "Operação", header_format)
                worksheet.write("F3", oper_excel, cell_format)
                worksheet.write("G3", "Modelo", header_format)
                worksheet.write("H3", modelo_excel, cell_format)
                worksheet.write("I3", "Linha", header_format)
                worksheet.write("J3", linha_excel, cell_format)

                # Cabeçalho dos dados na linha 5
                for col, col_name in enumerate(df_dados.columns):
                    worksheet.write(4, col, col_name, header_format)

                # Dados a partir da linha 6
                for row in range(len(df_dados)):
                    for col in range(len(df_dados.columns)):
                        worksheet.write(row + 5, col, df_dados.iloc[row, col], cell_format)

                # Ajustar largura das colunas (mais bonito)
                for col in range(len(df_dados.columns)):
                    worksheet.set_column(col, col, 12)

            output_excel.seek(0)
            st.download_button(
                label="Exportar para Excel",
                data=output_excel,
                file_name=(
                    f"Maquina_{arquivo['modelo'] or 'N_D'}_"
                    f"{arquivo['operacao'] or 'OP'}_"
                    f"{arquivo['data'].strftime('%d%m%Y') if arquivo['data'] else 'semdata'}_"
                    f"{(arquivo['hora'] or '').replace(':', '')}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"excel_download_{i}",
            )

            # --- Exportar para PDF (A4, ajustado) ---
            pdf_buffer = criar_pdf_a4(df_dados, arquivo)
            st.download_button(
                label="Exportar para PDF",
                data=pdf_buffer,
                file_name=(
                    f"Maquina_{arquivo['modelo'] or 'N_D'}_"
                    f"{arquivo['operacao'] or 'OP'}_"
                    f"{arquivo['data'].strftime('%d%m%Y') if arquivo['data'] else 'semdata'}_"
                    f"{(arquivo['hora'] or '').replace(':', '')}.pdf"
                ),
                mime="application/pdf",
                key=f"pdf_download_{i}",
            )

        except Exception as e:
            st.error(f"Erro ao carregar ou exibir o arquivo '{arquivo['nome_arquivo']}': {e}")
            st.info("Verifique se o arquivo CSV está no formato correto (separado por vírgulas).")
