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

# --- Configurações da Página ---
st.set_page_config(layout="wide", page_title="Dashboard FromTherm")

# --- Cabeçalho simples, sem login (Autenticação removida) ---
st.sidebar.title("FromTherm")
st.title("Dashboard de Históricos FromTherm")

# --- Configuração da pasta de dados ---
DADOS_DIR = "dados"  # A pasta 'dados' deve estar no mesmo nível do dashboard.py

# --- Função para listar arquivos XLSX localmente ---
@st.cache_data(ttl=3600)  # Cache para não ler os arquivos toda hora
def listar_arquivos_local():
    """
    Lista todos os arquivos .xlsx dentro da pasta 'dados'
    e devolve uma lista com informações básicas extraídas do nome.
    """
    if not os.path.exists(DADOS_DIR):
        st.error(f"A pasta '{DADOS_DIR}' não foi encontrada no repositório.")
        st.stop()

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.xlsx"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        linha, data, hora, operacao, modelo = "", None, "", "", ""

        # Tenta extrair infos do padrão de nome: historico_L1_20260303_2140_OP1234_FT185.xlsx
        try:
            partes = nome.replace(".xlsx", "").split("_")
            if len(partes) >= 6:  # Garante que há partes suficientes
                linha = partes[1]
                data_str = partes[2]
                hora_str = partes[3]
                operacao = partes[4]
                modelo = partes[5]

                data = datetime.strptime(data_str, "%Y%m%d").date()
                hora = f"{hora_str[:2]}:{hora_str[2:]}"
        except Exception as e:
            st.warning(f"Não foi possível extrair informações do arquivo '{nome}'. Erro: {e}")
            # Se der erro, as variáveis ficam vazias/None

        info_arquivos.append({
            "nome_arquivo": nome,
            "caminho": caminho,
            "linha": linha,
            "data": data,
            "hora": hora,
            "operacao": operacao,
            "modelo": modelo,
        })

    return info_arquivos

# --- Carregar e processar arquivos ---
todos_arquivos_info = listar_arquivos_local()

if not todos_arquivos_info:
    st.warning("Nenhum arquivo .xlsx de histórico encontrado na pasta 'dados'.")
    st.info("Por favor, adicione os arquivos .xlsx de histórico dentro da pasta 'dados' do seu repositório.")
    st.stop()

# --- Filtros ---
st.sidebar.header("Filtros")

# Extrair modelos únicos
modelos_disponiveis = sorted(list(set([a["modelo"] for a in todos_arquivos_info if a["modelo"]])))
modelo_selecionado = st.sidebar.selectbox("Filtrar por Modelo:", ["Todos"] + modelos_disponiveis)

# Extrair datas únicas
datas_disponiveis = sorted(list(set([a["data"] for a in todos_arquivos_info if a["data"]])), reverse=True)
data_selecionada = st.sidebar.date_input(
    "Filtrar por Data:",
    value=None,
    min_value=min(datas_disponiveis) if datas_disponiveis else None,
    max_value=max(datas_disponiveis) if datas_disponiveis else None
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
    key=lambda x: (x["data"] if x["data"] else datetime.min.date(), x["hora"]),
    reverse=True
)

st.subheader("Históricos Disponíveis")

if not arquivos_filtrados:
    st.info("Nenhum histórico encontrado com os filtros selecionados.")
else:
    # Exibir lista de históricos
    for i, arquivo in enumerate(arquivos_filtrados):
        data_str = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else "sem data"
        expander_title = (
            f"**{arquivo['modelo']}** - Linha: {arquivo['linha']} - "
            f"Data: {data_str} - Hora: {arquivo['hora']} - Operação: {arquivo['operacao']}"
        )
        with st.expander(expander_title):
            try:
                df_info = pd.read_excel(arquivo["caminho"], sheet_name="Informações")
                df_dados = pd.read_excel(arquivo["caminho"], sheet_name="Dados")

                st.subheader("Informações do Histórico")
                # Transpõe para melhor visualização (campos na vertical)
                st.dataframe(df_info.T, use_container_width=True)

                st.subheader("Dados da Operação")
                st.dataframe(df_dados, use_container_width=True)

                # --- Exportar para Excel ---
                output_excel = BytesIO()
                with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                    df_info.to_excel(writer, sheet_name="Informações", index=False)
                    df_dados.to_excel(writer, sheet_name="Dados", index=False)
                output_excel.seek(0)
                st.download_button(
                    label="Exportar para Excel",
                    data=output_excel,
                    file_name=(
                        f"historico_{arquivo['modelo']}_"
                        f"{arquivo['data'].strftime('%Y%m%d') if arquivo['data'] else 'semdata'}_"
                        f"{arquivo['hora'].replace(':', '')}.xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"excel_download_{i}"
                )

                # --- Exportar para PDF ---
                def create_pdf(info_df, dados_df, filename):
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []

                    story.append(Paragraph(
                        f"<b>Histórico FromTherm - Modelo: {arquivo['modelo']}</b>",
                        styles["h1"]
                    ))
                    story.append(Paragraph(
                        f"Data: {data_str} - Hora: {arquivo['hora']}",
                        styles["h3"]
                    ))
                    story.append(Spacer(1, 12))

                    story.append(Paragraph("<b>Informações do Histórico:</b>", styles["h2"]))
                    info_data = [list(info_df.columns)] + info_df.values.tolist()
                    info_table = Table(info_data)
                    info_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(info_table)
                    story.append(Spacer(1, 12))

                    story.append(Paragraph("<b>Dados da Operação:</b>", styles["h2"]))
                    dados_data = [list(dados_df.columns)] + dados_df.values.tolist()
                    dados_table = Table(dados_data)
                    dados_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(dados_table)

                    doc.build(story)
                    buffer.seek(0)
                    return buffer

                pdf_buffer = create_pdf(
                    df_info,
                    df_dados,
                    f"historico_{arquivo['modelo']}_"
                    f"{arquivo['data'].strftime('%Y%m%d') if arquivo['data'] else 'semdata'}_"
                    f"{arquivo['hora'].replace(':', '')}.pdf"
                )
                st.download_button(
                    label="Exportar para PDF",
                    data=pdf_buffer,
                    file_name=(
                        f"historico_{arquivo['modelo']}_"
                        f"{arquivo['data'].strftime('%Y%m%d') if arquivo['data'] else 'semdata'}_"
                        f"{arquivo['hora'].replace(':', '')}.pdf"
                    ),
                    mime="application/pdf",
                    key=f"pdf_download_{i}"
                )

            except Exception as e:
                st.error(f"Erro ao carregar ou exibir o arquivo '{arquivo['nome_arquivo']}': {e}")
                st.info("Verifique se o arquivo Excel possui as abas 'Informações' e 'Dados' e se está no formato correto.")
