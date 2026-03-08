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

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
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
        ano = None
        mes = None
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
                modelo = partes[5]            # FT185 ou similar

                data = datetime.strptime(data_str, "%Y%m%d").date()
                ano = data.year
                mes = data.month
                hora = f"{hora_str[:2]}:{hora_str[2:]}"
        except Exception:
            pass

        info_arquivos.append(
            {
                "nome_arquivo": nome,
                "caminho": caminho,
                "linha": linha,
                "data": data,
                "ano": ano,
                "mes": mes,
                "hora": hora,
                "operacao": operacao,
                "modelo": modelo,
            }
        )

    return info_arquivos


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo .csv de histórico encontrado na pasta '{DADOS_DIR}'.")
    st.info("Verifique se os arquivos .csv foram sincronizados corretamente para o GitHub.")
    st.stop()

# --- TABS PRINCIPAIS ---
tab_hist, tab_graf = st.tabs(["📄 Históricos e Planilhas", "📊 Crie Seu Gráfico"])


# =========================
#  TAB 1 - HISTÓRICOS
# =========================
with tab_hist:
    st.sidebar.header("Filtros - Históricos")

    # Conjuntos disponíveis
    modelos_disponiveis = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"]})
    anos_disponiveis = sorted({a["ano"] for a in todos_arquivos_info if a["ano"]})
    meses_disponiveis = sorted({a["mes"] for a in todos_arquivos_info if a["mes"]})
    datas_disponiveis = sorted(
        {a["data"] for a in todos_arquivos_info if a["data"]},
        reverse=True,
    )
    ops_disponiveis = sorted({a["operacao"] for a in todos_arquivos_info if a["operacao"]})

    # Filtro por Modelo
    modelo_selecionado = st.sidebar.selectbox(
        "Modelo:",
        ["Todos"] + modelos_disponiveis,
        key="hist_modelo",
    )

    # Filtro por Ano
    ano_selecionado = st.sidebar.selectbox(
        "Ano:",
        ["Todos"] + anos_disponiveis if anos_disponiveis else ["Todos"],
        key="hist_ano",
    )

    # Filtro por Mês
    mes_label_map = {
        1: "01 - Jan", 2: "02 - Fev", 3: "03 - Mar", 4: "04 - Abr",
        5: "05 - Mai", 6: "06 - Jun", 7: "07 - Jul", 8: "08 - Ago",
        9: "09 - Set", 10: "10 - Out", 11: "11 - Nov", 12: "12 - Dez",
    }
    meses_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis] if meses_disponiveis else ["Todos"]
    mes_selecionado_label = st.sidebar.selectbox(
        "Mês:",
        meses_labels,
        key="hist_mes",
    )
    # Converter label de volta para número de mês
    mes_selecionado = None
    if mes_selecionado_label != "Todos":
        mes_selecionado = int(mes_selecionado_label.split(" ")[0])

    # Filtro por Data (opcional)
    data_selecionada = st.sidebar.date_input(
        "Data específica (opcional):",
        value=None,
        min_value=min(datas_disponiveis) if datas_disponiveis else None,
        max_value=max(datas_disponiveis) if datas_disponiveis else None,
        key="hist_data",
    )

    # Filtro por Operação (OP)
    operacao_selecionada = st.sidebar.selectbox(
        "Operação (OP):",
        ["Todas"] + ops_disponiveis,
        key="hist_op",
    )

    # Aplicar filtros em cadeia
    arquivos_filtrados = todos_arquivos_info

    if modelo_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == modelo_selecionado]

    if ano_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["ano"] == ano_selecionado]

    if mes_selecionado is not None:
        arquivos_filtrados = [a for a in arquivos_filtrados if a["mes"] == mes_selecionado]

    if data_selecionada:
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data"] == data_selecionada]

    if operacao_selecionada != "Todas":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == operacao_selecionada]

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
        normal_left_bold = ParagraphStyle(
            name="NormalLeftBold",
            parent=styles["Normal"],
            alignment=0,
            fontSize=10,
            leading=14,  # Espaçamento entre linhas
            fontName="Helvetica-Bold",
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

        # Bloco de informações
        story.append(Paragraph(f"<b>Data:</b> {data_str}", normal_left_bold))
        story.append(Paragraph(f"<b>Hora:</b> {hora_str}", normal_left_bold))
        story.append(Paragraph(f"<b>Operação:</b> {operacao_str}", normal_left_bold))
        story.append(Paragraph(f"<b>Modelo:</b> {modelo_str}", normal_left_bold))
        story.append(Paragraph(f"<b>Linha:</b> {linha_str}", normal_left_bold))
        story.append(Spacer(1, 10))

        # Título da seção de dados
        story.append(Paragraph("Dados da Operação:", subtitle_style))
        story.append(Spacer(1, 6))

        # Preparar dados da tabela
        cols = list(df_dados.columns)
        data_rows = df_dados.values.tolist()
        table_data = [cols] + data_rows

        # Largura de tabela
        total_width = 780
        col_widths = []
        for col_name in cols:
            if "kW" in col_name:
                col_widths.append(90)
            elif "Ambiente" in col_name or "Corrente" in col_name:
                col_widths.append(70)
            elif "Date" in col_name:
                col_widths.append(60)
            elif "Time" in col_name:
                col_widths.append(50)
            else:
                col_widths.append(60)

        current_total_width = sum(col_widths)
        if current_total_width != total_width:
            scale_factor = total_width / current_total_width
            col_widths = [w * scale_factor for w in col_widths]

        azul_cabecalho = colors.HexColor("#004A99")

        dados_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        dados_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), azul_cabecalho),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.HexColor("#F7FBFF"), colors.HexColor("#E6F0FF")]),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        story.append(dados_table)
        story.append(Spacer(1, 10))

        rodape = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Fromtherm © {datetime.now().year}"
        story.append(Paragraph(rodape, normal_center))

        doc.build(story)
        buffer.seek(0)
        return buffer

    # --- Listar cada arquivo filtrado ---
    for i, arquivo in enumerate(arquivos_filtrados):
        data_str = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else "sem data"

        # Formatações para nomes de arquivo (download)
        if arquivo["data"]:
            data_nome = arquivo["data"].strftime("%d-%m-%Y")
        else:
            data_nome = "sem-data"

        hora_nome = (arquivo["hora"] or "").replace(":", "-")
        if hora_nome:
            hora_nome = hora_nome + "hs"
        else:
            hora_nome = "sem-hora"

        titulo_expander = (
            f"**{arquivo['modelo'] or 'Modelo não identificado'}** - "
            f"Linha: {arquivo['linha'] or '-'} - "
            f"Data: {data_str} - Hora: {arquivo['hora'] or '-'} - "
            f"Operação: {arquivo['operacao'] or '-'}"
        )

        with st.expander(titulo_expander):
            try:
                # lê CSV
                try:
                    df_dados = pd.read_csv(arquivo["caminho"], sep=";", engine="python")
                except Exception:
                    df_dados = pd.read_csv(arquivo["caminho"], sep=",", engine="python")

                df_dados.columns = [
                    "Date",
                    "Time",
                    "Ambiente",
                    "Entrada",
                    "Saída",
                    "ΔT",
                    "Tensão",
                    "Corrente",
                    "kcal/h",
                    "Vazão",
                    "kW Aquecimento",
                    "kW Consumo",
                    "COP",
                ]

                st.subheader("Dados da Operação")
                st.dataframe(df_dados, use_container_width=True)

                # Exportar Excel
                output_excel = BytesIO()
                with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                    workbook = writer.book
                    worksheet = workbook.add_worksheet("Dados")
                    writer.sheets["Dados"] = worksheet

                    azul_cabecalho = "#004A99"
                    title_format = workbook.add_format(
                        {"bold": True, "font_size": 16, "align": "center"}
                    )
                    header_info_label = workbook.add_format(
                        {
                            "bold": True,
                            "bg_color": "#D9E3F0",
                            "border": 1,
                            "align": "left",
                        }
                    )
                    header_info_value = workbook.add_format(
                        {
                            "border": 1,
                            "align": "left",
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

                    num_cols = len(df_dados.columns)
                    merge_cols = max(num_cols, 10)
                    last_col_letter = ""
                    idx_temp = merge_cols - 1
                    while idx_temp >= 0:
                        last_col_letter = chr(ord("A") + (idx_temp % 26)) + last_col_letter
                        idx_temp = idx_temp // 26 - 1

                    worksheet.merge_range(
                        f"A1:{last_col_letter}1",
                        "Planilha Teste de Máquinas Fromtherm",
                        title_format,
                    )

                    data_excel = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else ""
                    hora_excel = arquivo["hora"] or ""
                    oper_excel = arquivo["operacao"] or ""
                    modelo_excel = arquivo["modelo"] or ""
                    linha_excel = arquivo["linha"] or ""

                    info_labels = ["Data", "Hora", "Operação", "Modelo", "Linha"]
                    info_values = [data_excel, hora_excel, oper_excel, modelo_excel, linha_excel]

                    for idx, (label, value) in enumerate(zip(info_labels, info_values)):
                        row = 2 + idx
                        worksheet.write(row, 0, label, header_info_label)
                        worksheet.write(row, 1, value, header_info_value)

                    worksheet.set_column(0, 0, 15)
                    worksheet.set_column(1, 1, 20)

                    header_row = 8
                    for col, col_name in enumerate(df_dados.columns):
                        worksheet.write(header_row, col, col_name, header_data_format)

                    for row in range(len(df_dados)):
                        for col in range(len(df_dados.columns)):
                            worksheet.write(
                                row + header_row + 1,
                                col,
                                df_dados.iloc[row, col],
                                cell_data_format,
                            )

                    for col_idx, col_name in enumerate(df_dados.columns):
                        if "kW" in col_name:
                            worksheet.set_column(col_idx, col_idx, 15)
                        elif "Ambiente" in col_name or "Corrente" in col_name:
                            worksheet.set_column(col_idx, col_idx, 10)
                        elif "Date" in col_name:
                            worksheet.set_column(col_idx, col_idx, 10)
                        elif "Time" in col_name:
                            worksheet.set_column(col_idx, col_idx, 8)
                        else:
                            worksheet.set_column(col_idx, col_idx, 12)

                output_excel.seek(0)
                st.download_button(
                    label="Exportar para Excel",
                    data=output_excel,
                    file_name=(
                        f"Maquina_{arquivo['modelo'] or 'N_D'}_"
                        f"{arquivo['operacao'] or 'OP'}_"
                        f"{data_nome}_{hora_nome}.xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"excel_download_{i}",
                )

                # Exportar PDF
                pdf_buffer = criar_pdf_paisagem(df_dados, arquivo)
                st.download_button(
                    label="Exportar para PDF",
                    data=pdf_buffer,
                    file_name=(
                        f"Maquina_{arquivo['modelo'] or 'N_D'}_"
                        f"{arquivo['operacao'] or 'OP'}_"
                        f"{data_nome}_{hora_nome}.pdf"
                    ),
                    mime="application/pdf",
                    key=f"pdf_download_{i}",
                )

            except Exception as e:
                st.error(f"Erro ao carregar ou exibir o arquivo '{arquivo['nome_arquivo']}': {e}")
                st.info("Verifique se o arquivo CSV está no formato correto (separado por ponto e vírgula ';' ou vírgula ',').")


# =========================
#  TAB 2 - CRIE SEU GRÁFICO
# =========================
with tab_graf:
    st.subheader("Crie Seu Gráfico")

    st.markdown(
        "Selecione o **Modelo**, **Ano**, **Mês**, **Operação (OP)** e os itens que deseja visualizar no gráfico."
    )

    # Obter todos os modelos disponíveis
    modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))

    # Seleção de Modelo
    modelo_graf = st.selectbox(
        "Modelo:",
        modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum modelo disponível"],
        key="graf_modelo",
    )

    # Filtrar arquivos baseados no modelo selecionado
    arquivos_por_modelo = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf]

    # Obter anos disponíveis para o modelo selecionado
    anos_disponiveis_graf = sorted(list(set(a["ano"] for a in arquivos_por_modelo if a["ano"])))

    # Seleção de Ano
    ano_graf = st.selectbox(
        "Ano:",
        anos_disponiveis_graf if anos_disponiveis_graf else ["Nenhum ano disponível"],
        key="graf_ano",
    )

    # Filtrar arquivos baseados no modelo e ano selecionados
    arquivos_por_modelo_ano = [a for a in arquivos_por_modelo if a["ano"] == ano_graf]

    # Obter meses disponíveis para o modelo e ano selecionados
    meses_disponiveis_graf = sorted(list(set(a["mes"] for a in arquivos_por_modelo_ano if a["mes"])))
    meses_labels_graf = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis_graf] if meses_disponiveis_graf else ["Todos"]

    # Seleção de Mês
    mes_graf_label = st.selectbox(
        "Mês:",
        meses_labels_graf,
        key="graf_mes",
    )
    mes_graf = None
    if mes_graf_label != "Todos":
        mes_graf = int(mes_graf_label.split(" ")[0])

    # Filtrar arquivos baseados no modelo, ano e mês selecionados
    arquivos_por_modelo_ano_mes = [a for a in arquivos_por_modelo_ano if a["mes"] == mes_graf or mes_graf is None]

    # Obter OPs disponíveis para o modelo, ano e mês selecionados
    ops_disponiveis_graf = sorted(list(set(a["operacao"] for a in arquivos_por_modelo_ano_mes if a["operacao"])))

    # Determinar valor padrão para OP
    default_op_index = 0
    if len(ops_disponiveis_graf) == 1:
        default_op_index = ops_disponiveis_graf.index(ops_disponiveis_graf[0])

    op_graf = st.selectbox(
        "Operação (OP):",
        ops_disponiveis_graf if ops_disponiveis_graf else ["Nenhuma OP disponível"],
        index=default_op_index if ops_disponiveis_graf else 0, # Seleciona a única OP se houver, ou a primeira
        key="graf_op",
    )

    # Filtrar arquivo específico para esse modelo + ano + mês + OP
    arquivo_escolhido = None
    for a in todos_arquivos_info:
        if (a["modelo"] == modelo_graf and 
            a["ano"] == ano_graf and 
            (a["mes"] == mes_graf or mes_graf is None) and
            a["operacao"] == op_graf):
            arquivo_escolhido = a
            break

    if not modelos_disponiveis_graf:
        st.info("Ainda não há dados suficientes para criar gráficos.")
    elif arquivo_escolhido is None:
        st.warning("Não foi encontrado um arquivo que combine este Modelo, Ano, Mês e Operação.")
    else:
        st.markdown(
            f"Arquivo selecionado: **{arquivo_escolhido['nome_arquivo']}**"
        )

        # Carregar dados do arquivo escolhido
        try:
            try:
                df_graf = pd.read_csv(arquivo_escolhido["caminho"], sep=";", engine="python")
            except Exception:
                df_graf = pd.read_csv(arquivo_escolhido["caminho"], sep=",", engine="python")

            df_graf.columns = [
                "Date",
                "Time",
                "Ambiente",
                "Entrada",
                "Saída",
                "ΔT",
                "Tensão",
                "Corrente",
                "kcal/h",
                "Vazão",
                "kW Aquecimento",
                "kW Consumo",
                "COP",
            ]

            # Criar coluna de tempo completo (Date + Time) para eixo X
            try:
                df_graf["DateTime"] = pd.to_datetime(
                    df_graf["Date"].astype(str) + " " + df_graf["Time"].astype(str),
                    errors="coerce",
                )
            except Exception:
                df_graf["DateTime"] = df_graf["Time"]  # fallback

            # Seleção de variáveis
            st.markdown("### Variáveis para o gráfico")

            variaveis_opcoes = [
                "Ambiente",
                "Entrada",
                "Saída",
                "ΔT",
                "Tensão",
                "Corrente",
                "kcal/h",
                "Vazão",
                "kW Aquecimento",
                "kW Consumo",
                "COP",
            ]

            vars_selecionadas = st.multiselect(
                "Selecione uma ou mais variáveis:",
                variaveis_opcoes,
                default=["Ambiente", "Entrada", "Saída"],
            )

            if not vars_selecionadas:
                st.info("Selecione pelo menos uma variável para gerar o gráfico.")
            else:
                # Derreter o DataFrame para formato longo (para Plotly)
                df_plot = df_graf[["DateTime"] + vars_selecionadas].copy()
                df_melted = df_plot.melt(
                    id_vars="DateTime",
                    value_vars=vars_selecionadas,
                    var_name="Variável",
                    value_name="Valor",
                )

                # Gráfico interativo com Plotly
                fig = px.line(
                    df_melted,
                    x="DateTime",
                    y="Valor",
                    color="Variável",
                    title=f"Gráfico - Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{mes_graf_label.split(' ')[0]}",
                    markers=True,
                )

                fig.update_layout(
                    xaxis_title="Tempo",
                    yaxis_title="Valor",
                    hovermode="x unified",
                    legend_title="Variáveis",
                )

                st.plotly_chart(fig, use_container_width=True)

                st.markdown(
                    "- Use o botão de **fullscreen** no gráfico para expandir.\n"
                    "- Use o ícone de **câmera** no gráfico para baixar como imagem (PNG).\n"
                    "- A imagem baixada pode ser compartilhada via WhatsApp, e-mail, etc., em qualquer dispositivo."
                )

        except Exception as e:
            st.error(f"Erro ao carregar dados para o gráfico: {e}")
            st.info("Verifique se o arquivo CSV está no formato correto.")
