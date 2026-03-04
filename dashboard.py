import streamlit as st
import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
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
            # Se o nome não seguir o padrão, apenas ignora os detalhes
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
    arquivos_filtrados = [
        a for a in arquivos_filtrados if a["modelo"] == modelo_selecionado
    ]
if data_selecionada:
    arquivos_filtrados = [
        a for a in arquivos_filtrados if a["data"] == data_selecionada
    ]

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

# --- Função para gerar PDF a partir do DataFrame de dados ---
def criar_pdf_com_cabecalho(df_dados, arquivo_info):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Informações do cabeçalho
    data_str = arquivo_info["data"].strftime("%d/%m/%Y") if arquivo_info["data"] else "N/D"
    hora_str = arquivo_info["hora"] or "N/D"
    operacao_str = arquivo_info["operacao"] or "N/D"
    modelo_str = arquivo_info["modelo"] or "N/D"
    linha_str = arquivo_info["linha"] or "N/D"

    # Título principal do PDF
    story.append(Paragraph("<b>Planilha Teste de Máquinas Fromtherm</b>", styles["h1"]))
    story.append(Spacer(1, 0.2 * 2.54 * 0.5)) # 0.5 cm

    # Tabela de informações (replicando o formato do seu exemplo)
    info_header_data = [
        ["Data", "Hora", "Operação", "Modelo", "Linha"],
        [data_str, hora_str, operacao_str, modelo_str, linha_str]
    ]
    info_table = Table(info_header_data, colWidths=[1.5*2.54, 1.5*2.54, 2*2.54, 1.5*2.54, 1.5*2.54]) # Larguras em cm
    info_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2 * 2.54 * 0.5)) # 0.5 cm

    # Título para os dados da operação
    story.append(Paragraph("<b>Dados da Operação:</b>", styles["h2"]))
    story.append(Spacer(1, 0.2 * 2.54 * 0.2)) # 0.2 cm

    # Tabela de dados
    dados_data = [list(df_dados.columns)] + df_dados.values.tolist()
    dados_table = Table(dados_data)
    dados_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(dados_table)
    story.append(Spacer(1, 0.2 * 2.54 * 0.5)) # 0.5 cm

    # Rodapé
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Fromtherm © {datetime.now().year}", styles["Normal"]))

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
            # Lê o CSV
            df_dados = pd.read_csv(arquivo["caminho"])

            st.subheader("Dados da Operação")
            st.dataframe(df_dados, use_container_width=True)

            # --- Exportar para Excel (convertendo o CSV para XLSX com cabeçalho) ---
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                # Cria um DataFrame para as informações do cabeçalho
                info_df = pd.DataFrame({
                    "Data": [arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else "N/D"],
                    "Hora": [arquivo["hora"] or "N/D"],
                    "Operação": [arquivo["operacao"] or "N/D"],
                    "Modelo": [arquivo["modelo"] or "N/D"],
                    "Linha": [arquivo["linha"] or "N/D"]
                })

                # Escreve o título na primeira linha
                worksheet = writer.book.add_worksheet("Dados")
                worksheet.write(0, 0, "Planilha Teste de Máquinas Fromtherm", writer.book.add_format({'bold': True, 'font_size': 14}))

                # Escreve as informações do cabeçalho a partir da linha 2
                info_df.to_excel(writer, sheet_name="Dados", startrow=2, index=False, header=True)

                # Escreve os dados da operação a partir da linha 5 (ajustar conforme necessidade)
                df_dados.to_excel(writer, sheet_name="Dados", startrow=5, index=False, header=True)

                # Adiciona o rodapé
                worksheet.write(df_dados.shape[0] + 7, 0, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Fromtherm © {datetime.now().year}")

            output_excel.seek(0)
            st.download_button(
                label="Exportar para Excel",
                data=output_excel,
                file_name=(
                    f"Maquina_{arquivo['modelo'] or 'N/D'}_"
                    f"{arquivo['operacao'] or 'N/D'}_"
                    f"{arquivo['data'].strftime('%d%m%Y') if arquivo['data'] else 'semdata'}_"
                    f"{(arquivo['hora'] or '').replace(':', '')}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"excel_download_{i}",
            )

            # --- Exportar para PDF ---
            pdf_buffer = criar_pdf_com_cabecalho(df_dados, arquivo)

            st.download_button(
                label="Exportar para PDF",
                data=pdf_buffer,
                file_name=(
                    f"Maquina_{arquivo['modelo'] or 'N/D'}_"
                    f"{arquivo['operacao'] or 'N/D'}_"
                    f"{arquivo['data'].strftime('%d%m%Y') if arquivo['data'] else 'semdata'}_"
                    f"{(arquivo['hora'] or '').replace(':', '')}.pdf"
                ),
                mime="application/pdf",
                key=f"pdf_download_{i}",
            )

        except Exception as e:
            st.error(f"Erro ao carregar ou exibir o arquivo '{arquivo['nome_arquivo']}': {e}")
            st.info("Verifique se o arquivo CSV está no formato correto (separado por vírgulas).")
