import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import time
import altair as alt
import base64 # Para codificar/decodificar imagens para PDF

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("MÁQUINA DE TESTE FROMTHERM")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados"  # pasta 'dados' no mesmo nível do dashboard.py


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10) # TTL de 10 segundos para o auto-refresh
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


# --- Função para carregar e renomear dados do CSV ---
@st.cache_data(ttl=10) # Cache para os dados do CSV também
def carregar_e_renomear_csv(caminho_arquivo):
    df_dados = pd.read_csv(caminho_arquivo)
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
    # Converte 'Date' e 'Time' para datetime para facilitar gráficos
    df_dados['Timestamp'] = pd.to_datetime(df_dados['Date'] + ' ' + df_dados['Time'])
    return df_dados


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
        leading=14, # Espaçamento entre linhas
        fontName="Helvetica-Bold"
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

    # Bloco de informações no formato solicitado (linhas separadas)
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
    cols = list(df_dados.columns) # AGORA DF_DADOS JÁ VEM COM NOMES CORRETOS
    # Remove a coluna 'Timestamp' se existir, pois é para uso interno do gráfico
    if 'Timestamp' in cols:
        cols.remove('Timestamp')
    data_rows = df_dados[cols].values.tolist() # Usa apenas as colunas selecionadas
    table_data = [cols] + data_rows

    # Largura de tabela para ocupar bem a página paisagem
    num_cols = len(cols)
    total_width = 780  # largura útil aproximada

    # Ajuste de largura de coluna mais inteligente para caber os nomes longos
    col_widths = []
    for col_name in cols:
        if "kW" in col_name: # Colunas de kW são mais longas
            col_widths.append(90) # Largura maior para kW Aquecimento/Consumo
        elif "Ambiente" in col_name or "Corrente" in col_name:
            col_widths.append(70)
        elif "Date" in col_name:
            col_widths.append(60)
        elif "Time" in col_name:
            col_widths.append(50)
        else:
            col_widths.append(60) # Largura padrão para outras colunas

    # Ajustar para que a soma das larguras seja igual à total_width
    current_total_width = sum(col_widths)
    if current_total_width != total_width:
        scale_factor = total_width / current_total_width
        col_widths = [w * scale_factor for w in col_widths]


    azul_cabecalho = colors.HexColor("#004A99")  # azul corporativo

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

# --- Função para criar PDF do gráfico ---
def criar_pdf_do_grafico(chart_png_bytes: bytes, titulo_grafico: str) -> BytesIO:
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
    normal_center = ParagraphStyle(
        name="NormalCenter",
        parent=styles["Normal"],
        alignment=1,
        fontSize=9,
    )

    story = []
    story.append(Paragraph("Gráfico de Tendência Fromtherm", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>{titulo_grafico}</b>", normal_center))
    story.append(Spacer(1, 12))

    # Adiciona a imagem do gráfico ao PDF
    # A imagem precisa ser redimensionada para caber na página A4 paisagem
    # Largura útil da página A4 paisagem é ~780 pontos. Altura útil ~520 pontos.
    img = Image(BytesIO(chart_png_bytes), width=750, height=450) # Ajuste de tamanho
    img.hAlign = 'CENTER'
    story.append(img)
    story.append(Spacer(1, 10))

    # Rodapé
    rodape = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Fromtherm © {datetime.now().year}"
    story.append(Paragraph(rodape, normal_center))

    doc.build(story)
    buffer.seek(0)
    return buffer


# --- SELEÇÃO DE PÁGINA NA BARRA LATERAL ---
st.sidebar.header("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Escolha uma opção:",
    ["Históricos Disponíveis", "Criar Gráficos"]
)

# --- Carregar lista de arquivos para ambas as páginas ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning("Nenhum arquivo .csv de histórico encontrado na pasta 'dados'.")
    st.info("Coloque os arquivos .csv de histórico dentro da pasta 'dados' do repositório.")
    # Adiciona um placeholder para o auto-refresh mesmo sem arquivos
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(10) # Espera 10 segundos antes de tentar novamente
    st.rerun() # Força o rerun do script
    st.stop() # Para a execução aqui se não houver arquivos


# --- LÓGICA DA PÁGINA "HISTÓRICOS DISPONÍVEIS" ---
if pagina_selecionada == "Históricos Disponíveis":
    st.header("Históricos de Operação")

    # --- Filtros na barra lateral (apenas para esta página) ---
    st.sidebar.subheader("Filtros de Históricos")

    modelos_disponiveis = sorted(list(set([a["modelo"] for a in todos_arquivos_info if a["modelo"]])))
    modelo_selecionado = st.sidebar.selectbox(
        "Filtrar por Modelo:",
        ["Todos"] + modelos_disponiveis,
        key="filtro_modelo_historicos" # Key única para este widget
    )

    datas_disponiveis = sorted(
        list(set([a["data"] for a in todos_arquivos_info if a["data"]])),
        reverse=True,
    )
    data_selecionada = st.sidebar.date_input(
        "Filtrar por Data:",
        value=None,
        min_value=min(datas_disponiveis) if datas_disponiveis else None,
        max_value=max(datas_disponiveis) if datas_disponiveis else None,
        key="filtro_data_historicos" # Key única para este widget
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

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros selecionados.")
    else:
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
                    df_dados = carregar_e_renomear_csv(arquivo["caminho"])

                    st.subheader("Dados da Operação")
                    st.dataframe(df_dados.drop(columns=['Timestamp']), use_container_width=True) # Exibe sem Timestamp

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

                        # Título mesclado na primeira linha
                        num_cols = len(df_dados.columns) - 1 # Exclui 'Timestamp'
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

                        # Informações (formato solicitado)
                        data_excel = arquivo["data"].strftime("%d/%m/%Y") if arquivo["data"] else ""
                        hora_excel = arquivo["hora"] or ""
                        oper_excel = arquivo["operacao"] or ""
                        modelo_excel = arquivo["modelo"] or ""
                        linha_excel = arquivo["linha"] or ""

                        info_labels = ["Data", "Hora", "Operação", "Modelo", "Linha"]
                        info_values = [data_excel, hora_excel, oper_excel, modelo_excel, linha_excel]

                        for idx, (label, value) in enumerate(zip(info_labels, info_values)):
                            row = 2 + idx  # começando na linha 3
                            worksheet.write(row, 0, label, header_info_label)
                            worksheet.write(row, 1, value, header_info_value)

                        worksheet.set_column(0, 0, 15)
                        worksheet.set_column(1, 1, 20)

                        # Cabeçalho dos dados (linha 9)
                        header_row = 8
                        # Pega as colunas, excluindo 'Timestamp'
                        cols_para_excel = [col for col in df_dados.columns if col != 'Timestamp']
                        for col, col_name in enumerate(cols_para_excel):
                            worksheet.write(header_row, col, col_name, header_data_format)

                        # Dados (a partir da linha 10)
                        for row in range(len(df_dados)):
                            for col, col_name in enumerate(cols_para_excel):
                                worksheet.write(
                                    row + header_row + 1,
                                    col,
                                    df_dados.iloc[row][col_name], # Acessa pelo nome da coluna
                                    cell_data_format,
                                )

                        # Ajustar largura das colunas de dados no Excel
                        for col_idx, col_name in enumerate(cols_para_excel):
                            if "kW" in col_name:
                                worksheet.set_column(col_idx, col_idx, 15) # Mais largo para kW
                            elif "Ambiente" in col_name or "Corrente" in col_name:
                                worksheet.set_column(col_idx, col_idx, 10)
                            elif "Date" in col_name:
                                worksheet.set_column(col_idx, col_idx, 10)
                            elif "Time" in col_name:
                                worksheet.set_column(col_idx, col_idx, 8)
                            else:
                                worksheet.set_column(col_idx, col_idx, 12) # Padrão

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
                    pdf_buffer = criar_pdf_paisagem(df_dados.drop(columns=['Timestamp']), arquivo) # df_dados JÁ RENOMEADO, sem Timestamp
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


# --- LÓGICA DA PÁGINA "CRIAR GRÁFICOS" ---
elif pagina_selecionada == "Criar Gráficos":
    st.header("Criar Gráficos Dinâmicos")

    if not todos_arquivos_info:
        st.warning("Nenhum histórico disponível para criar gráficos.")
    else:
        # --- Filtros interdependentes ---
        modelos_disponiveis_grafico = sorted(list(set([a["modelo"] for a in todos_arquivos_info if a["modelo"]])))
        modelo_selecionado_grafico = st.selectbox(
            "Selecione o Modelo da Máquina:",
            ["Selecione..."] + modelos_disponiveis_grafico,
            key="filtro_modelo_graficos"
        )

        df_selecionado = None
        arquivo_meta_selecionado = None # Para passar as infos para o título do gráfico
        if modelo_selecionado_grafico != "Selecione...":
            operacoes_disponiveis = [
                f"{a['operacao']} - {a['data'].strftime('%d/%m/%Y')} {a['hora']}"
                for a in todos_arquivos_info
                if a["modelo"] == modelo_selecionado_grafico
            ]
            operacoes_disponiveis = sorted(operacoes_disponiveis, reverse=True)

            operacao_selecionada_grafico = st.selectbox(
                "Selecione a Operação/Histórico:",
                ["Selecione..."] + operacoes_disponiveis,
                key="filtro_operacao_graficos"
            )

            if operacao_selecionada_grafico != "Selecione...":
                # Encontra o arquivo correspondente
                partes_operacao = operacao_selecionada_grafico.split(' - ')
                op_id = partes_operacao[0]
                data_hora_str = partes_operacao[1]

                arquivo_meta_selecionado = next((
                    a for a in todos_arquivos_info
                    if a["modelo"] == modelo_selecionado_grafico and
                       a["operacao"] == op_id and
                       f"{a['data'].strftime('%d/%m/%Y')} {a['hora']}" == data_hora_str
                ), None)

                if arquivo_meta_selecionado:
                    df_selecionado = carregar_e_renomear_csv(arquivo_meta_selecionado["caminho"])
                    st.write(f"Dados carregados para: **{operacao_selecionada_grafico}**")
                else:
                    st.warning("Não foi possível carregar os dados para a operação selecionada.")

        if df_selecionado is not None:
            st.subheader("Selecione as Métricas para o Gráfico")

            # Métricas técnicas disponíveis (excluindo Date, Time, Timestamp)
            metricas_disponiveis = [col for col in df_selecionado.columns if col not in ['Date', 'Time', 'Timestamp']]

            metricas_selecionadas = st.multiselect(
                "Escolha uma ou mais métricas:",
                metricas_disponiveis,
                default=metricas_disponiveis[0] if metricas_disponiveis else [] # Seleciona a primeira por padrão
            )

            if metricas_selecionadas:
                # Título do gráfico personalizado
                titulo_grafico_completo = (
                    f"Modelo: {arquivo_meta_selecionado['modelo'] or 'N/D'} | "
                    f"Operação: {arquivo_meta_selecionado['operacao'] or 'N/D'} | "
                    f"Data: {arquivo_meta_selecionado['data'].strftime('%d/%m/%Y') if arquivo_meta_selecionado['data'] else 'N/D'} | "
                    f"Hora: {arquivo_meta_selecionado['hora'] or 'N/D'}"
                )
                st.subheader("Gráfico de Tendência")
                st.markdown(f"**{titulo_grafico_completo}**")


                # Preparar dados para o Altair (long format)
                df_plot = df_selecionado[['Timestamp'] + metricas_selecionadas].melt('Timestamp', var_name='Métrica', value_name='Valor')

                # Criar o gráfico interativo com Altair
                chart = alt.Chart(df_plot).mark_line().encode(
                    x=alt.X('Timestamp', title='Tempo'),
                    y=alt.Y('Valor', title='Valor da Métrica'),
                    color='Métrica', # Cada métrica terá uma cor diferente
                    tooltip=['Timestamp', 'Métrica', 'Valor']
                ).properties(
                    title="" # Título vazio aqui, pois já colocamos acima com markdown
                ).interactive() # Permite zoom e pan

                st.altair_chart(chart, use_container_width=True)

                # --- Opções de download/impressão para o gráfico ---
                st.markdown("---")
                st.markdown("### Opções do Gráfico")

                # Para baixar o gráfico como PNG (funcionalidade nativa do Altair)
                st.info("Para baixar o gráfico como imagem (PNG), passe o mouse sobre o gráfico e clique no ícone de câmera (📷) que aparece no canto superior direito.")

                # Botão para baixar o gráfico em PDF
                # Primeiro, precisamos salvar o gráfico como PNG em um buffer
                chart_json = chart.to_json()
                # Para converter JSON do Altair para PNG, Streamlit usa o Vega-Lite renderer.
                # Não há uma forma direta de pegar o PNG do chart object no Streamlit sem renderizá-lo.
                # Uma solução é usar o `st.download_button` com um SVG ou JSON e pedir para o usuário converter,
                # ou usar uma biblioteca externa como `altair_saver` (que requer instalação de Node.js e Vega-Lite CLI)
                # ou renderizar o gráfico em um ambiente headless.
                # Para simplificar e usar o que já temos (reportlab), vamos simular o download do PNG
                # e depois encapsulá-lo em um PDF.

                # A forma mais simples de obter o PNG é instruir o usuário a usar o botão nativo do Altair.
                # Para um botão de download de PDF, precisaríamos de uma imagem PNG do gráfico.
                # Como não temos uma forma direta de pegar o PNG do chart object no Streamlit sem renderizá-lo
                # e sem dependências externas complexas, a melhor abordagem é:
                # 1. Instruir o usuário a baixar o PNG via botão nativo do Altair.
                # 2. Se ele quiser em PDF, ele teria que fazer um upload dessa imagem.
                # Isso adiciona um passo manual.

                # ALTERNATIVA: Se o ambiente Streamlit Cloud tiver `altair_saver` configurado (não é padrão),
                # poderíamos fazer:
                # from altair_saver import save
                # chart_png_bytes = BytesIO()
                # save(chart, chart_png_bytes, fmt="png")
                # chart_png_bytes.seek(0)
                # pdf_buffer_grafico = criar_pdf_do_grafico(chart_png_bytes.read(), titulo_grafico_completo)
                # st.download_button(...)

                # Por enquanto, vamos manter a instrução para o PNG e uma nota sobre o PDF.
                # Se for CRÍTICO ter o botão de PDF direto, precisaremos de uma solução mais robusta
                # que pode envolver serviços externos ou mais setup no ambiente.

                # Para fins de demonstração e para atender ao pedido, vou criar um placeholder
                # para o botão de PDF, mas a funcionalidade de "gerar o PNG do gráfico programaticamente"
                # é o desafio aqui sem dependências extras.

                # Para simular, vamos criar um PNG dummy ou instruir o usuário.
                # Para o escopo atual, a melhor forma é o usuário baixar o PNG e, se quiser,
                # usar uma ferramenta externa para converter para PDF.
                # No entanto, para cumprir o pedido de "botão para baixar o gráfico em PDF",
                # vou criar uma função que *simula* a criação do PDF com uma imagem placeholder,
                # e deixo um comentário sobre a complexidade de gerar o PNG do Altair diretamente.

                # --- Solução para o botão de PDF do gráfico (com ressalvas) ---
                # Para realmente gerar o PNG do Altair no backend, precisaríamos de `altair_saver`
                # e `vl-convert-python` (que requer Node.js e Vega-Lite CLI no ambiente).
                # Como isso é complexo para o Streamlit Cloud sem setup extra,
                # a alternativa é o usuário baixar o PNG e depois converter.
                # Mas para ter o botão, vamos fazer uma abordagem que funcionaria se tivéssemos o PNG.

                # Vamos criar um "botão" que, se clicado, informa sobre a limitação
                # ou, se tivermos um PNG (mesmo que dummy), o encapsula.

                # Para o propósito de ter um botão funcional, vamos gerar um PNG temporário
                # usando o método `to_json` do Altair e uma conversão base64 para embedar no PDF.
                # Isso ainda não é o PNG "real" do gráfico renderizado, mas é um passo mais próximo.
                # A melhor forma de obter o PNG real é via o botão nativo do Altair.

                # Para ter um botão de download de PDF, o Streamlit precisa de bytes.
                # Vamos criar um PDF que diz "Gráfico indisponível para download direto em PDF"
                # ou que usa uma imagem placeholder, a menos que tenhamos o PNG real.

                # Para o seu caso, o mais prático é o usuário usar o botão nativo do Altair (câmera).
                # Mas se o requisito é um botão de PDF, vamos tentar uma abordagem.
                # O Altair chart object pode ser salvo como JSON ou SVG.
                # SVG pode ser convertido para PNG e depois para PDF.

                # Para evitar dependências complexas e ainda ter um botão de PDF,
                # vamos gerar um SVG do gráfico e tentar convertê-lo para PNG (se possível)
                # ou embedar o SVG diretamente no PDF (ReportLab suporta SVG com algumas limitações).
                # A forma mais confiável para ReportLab é PNG.

                # A solução mais simples para o Streamlit Cloud sem dependências externas é:
                # 1. O usuário baixa o PNG via botão nativo do Altair.
                # 2. Se ele quiser em PDF, ele pode usar um conversor online ou local.
                # Isso não atende ao "botão para baixar o gráfico em PDF" diretamente.

                # Vamos tentar uma abordagem que gera um SVG e o embeda no PDF.
                # ReportLab tem suporte limitado a SVG. A melhor forma é PNG.
                # Para ter o PNG do Altair sem `altair_saver`, é complicado.

                # Vou reverter para a instrução de baixar PNG e uma nota sobre PDF,
                # pois a implementação de um botão de PDF direto para o gráfico Altair
                # sem dependências extras é um desafio técnico no Streamlit Cloud.
                # Se isso for um requisito *absoluto*, teríamos que explorar soluções mais avançadas.

                # Por enquanto, vou remover o botão de PDF para o gráfico e manter a instrução do PNG.
                # Se você realmente precisar do botão de PDF, me avise que buscaremos uma solução mais complexa.

                # Removendo o botão de PDF para o gráfico e a instrução de compartilhamento.
                # Mantendo apenas a instrução para o PNG.

                # st.info("Para imprimir o dashboard completo (incluindo o gráfico), use as opções do seu navegador (Ctrl+P).")
            else:
                st.info("Selecione pelo menos uma métrica para gerar o gráfico.")
        else:
            st.info("Selecione um modelo e uma operação para começar a criar gráficos.")


# --- Adiciona o auto-refresh no final do script ---
placeholder = st.empty()
with placeholder.container():
    st.markdown(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10) # Espera 10 segundos
st.rerun() # Força o rerun do script
