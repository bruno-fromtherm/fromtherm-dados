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
            # esperado: historico_L1_20260303_2140_OP1234_FT185.csv
            if len(partes) >= 6:
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


# --- Função para gerar PDF A4 paisagem, com azul no cabeçalho ---
def criar_pdf_paisagem(df_dados: pd.DataFrame, meta: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TitleCenter",
        parent=styles["Title"],
        alignment=1,  # centralizado
        fontSize=18,
        spaceAfter=16,
    )
    subtitle_style = ParagraphStyle(
        name="SubTitleLeft",
        parent=styles["Heading2"],
        alignment=0,
        fontSize=12,
        spaceAfter=8,
    )
    normal_center = ParagraphStyle(
        name="NormalCenter",
        parent=styles["Normal"],
        alignment=1,
        fontSize=9,
    )

    story = []

    # Título principal
    story.append(Paragraph("Planilha Teste de Máquinas Fromtherm", title_style))
    story.append(Spacer(1, 6))

    data_str = meta["data"].strftime("%d/%m/%Y") if meta["data"] else "N/D"
    hora_str = meta["hora"] or "N/D"
    operacao_str = meta["operacao"] or "N/D"
    modelo_str = meta["modelo"] or "N/D"
    linha_str = meta["linha"] or "N/D"

    # Bloco de informações no formato solicitado
    info_lines = [
        f"Data {data_str}",
        f"Hora {hora_str}",
        f"Operação {operacao_str}",
        f"Modelo {modelo_str}",
        f"Linha {linha_str}",
    ]
    for line in info_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 10))

    # Título da seção de dados
    story.append(Paragraph("Dados da Operação:", subtitle_style))
    story.append(Spacer(1, 6))

    # Preparar dados da tabela
    cols = list(df_dados.columns)
    data_rows = df_dados.values.tolist()
    table_data = [cols] + data_rows

    # Largura de tabela para ocupar bem a página paisagem
    num_cols = len(cols)
    total_width = 780  # largura útil aproximada
    base = total_width / num_cols
    col_widths = [base] * num_cols

    azul_cabecalho = colors.HexColor("#004A99")  # azul mais corporativo

    dados_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    dados_table.setStyle(
        TableStyle(
            [
                # Cabeçalho azul
                ("BACKGROUND", (0, 0), (-1, 0), azul_cabecalho),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),

                # Corpo da tabela listrado suave
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#F7FBFF"), colors.HexColor("#E6F0FF")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),

                # Linhas de grade finas
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(dados_table)
    story.append(Spacer(1, 10))

    # Rodapé
    rodape = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Fromtherm © {datetime.now().year}"
    story.append(Paragraph(rodape, normal_center))

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

            # --- Exportar para Excel (organizado e com azul no cabeçalho) ---
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet("Dados")
                writer.sheets["Dados"] = worksheet

                # Formatos de Excel
                azul_cabecalho = "#004A99"
                title_format = workbook.add_format(
                    {"bold": True, "font_size": 16, "align": "center"}
                )
                header_info_label = workbook.add_format(
                    {
                        "bold": True,
                        "bg_color": "#D9E3F0",
                        "border": 1,
                        "align": "center",
                    }
                )
                header_info_value = workbook.add_format(
                    {
                        "border": 1,
                        "align": "center",
                    }
                )
                header_data_format = workbook.add_format(
                    {
                        "bold": True,
                        "bg_color": azul_cabecalho,
                        "font_color": "white",
                        "border": 1,
                        "align": "center",
                    }
                )
                cell_data_format = workbook.add_format(
                    {
                        "border": 1,
                        "align": "center",
                        "bg_color": "#F7FBFF",
                    }
                )

                # Título mesclado na primeira linha
                num_cols = len(df_dados.columns)
                last_col_idx = num_cols - 1
                # Converter índice numérico de coluna em letra (A, B, C, ... até Z, depois AA, AB, etc.)
                def col_letter(idx: int) -> str:
                    result = ""
                    idx_temp = idx
                    while idx_temp >= 0:
                        result = chr(ord("A") + (idx_temp % 26)) + result
                        idx_temp = idx_temp // 26 - 1
                    return result

                last_col_letter = col_letter(last_col_idx)
                worksheet.merge_range(
                    f"A1:{last_col_letter}1",
                    "Planilha Teste de Máquinas Fromtherm",
                    title_format,
                )

                # Informações (formato solicitado)
                data_excel = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else ""
                hora_excel = arquivo["hora"] or ""
                oper_excel = arquivo["operacao"] or ""
                modelo_excel = arquivo["modelo"] or ""
                linha_excel = arquivo["linha"] or ""

                # Linha 3 a 7 com texto na forma:
                # Data 03/03/2026
                # Hora 21:40
                # Operação OP1234
                # Modelo FT185
                # Linha L1
                info_labels = ["Data", "Hora", "Operação", "Modelo", "Linha"]
                info_values = [data_excel, hora_excel, oper_excel, modelo_excel, linha_excel]

                for idx, (label, value) in enumerate(zip(info_labels, info_values)):
                    row = 2 + idx  # começando na linha 3 (índice 2)
                    worksheet.write(row, 0, label, header_info_label)
                    worksheet.write(row, 1, value, header_info_value)

                # Cabeçalho dos dados (linha 9)
                header_row = 8
                for col, col_name in enumerate(df_dados.columns):
                    worksheet.write(header_row, col, col_name, header_data_format)

                # Dados (a partir da linha 10)
                for row in range(len(df_dados)):
                    for col in range(len(df_dados.columns)):
                        worksheet.write(row + header_row + 1, col, df_dados.iloc[row, col], cell_data_format)

                # Ajustar largura das colunas
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

            # --- Exportar para PDF (A4 paisagem, azul, profissional) ---
            pdf_buffer = criar_pdf_paisagem(df_dados, arquivo)
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
