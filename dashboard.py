import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re # Importar módulo de expressões regulares
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm  # Importar cm para unidades de medida
from io import BytesIO
import plotly.express as px

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm") # Título da aba do navegador

# =========================
#  CSS GLOBAL (correção do "0", cards com animação suave)
# =========================
st.markdown(
    """
    <style>
    /* REMOÇÃO FINAL DO "0" TEIMOSO (mais abrangente e direto) */
    /* Esconde o botão de menu do Streamlit e o ícone de menu */
    button[data-testid="stSidebarNavToggle"],
    .st-emotion-cache-1r6dm1x, /* Seletor específico para o ícone de menu */
    .st-emotion-cache-10q71g7, /* Seletor específico para o container do ícone de menu */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > div:first-child > span,
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > span,
    span[data-testid="stDecoration"],
    summary {
        display: none !important;
    }

    /* Estilo dos cards de métricas */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd; /* Cor padrão da borda */
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd; /* Cor padrão do ícone */
        animation: ft-pulse 1.5s ease-in-out infinite; /* Animação de pulso suave para todos */
    }
    .ft-card-icon.red {
        color: #dc3545; /* Cor vermelha para T-Saída */
    }
    .ft-card-content {
        display: flex;
        flex-direction: column;
    }
    .ft-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #6c757d;
        margin-bottom: 2px;
    }
    .ft-card-value {
        font-size: 20px;
        font-weight: 700;
        color: #343a40;
    }
    .ft-card-value.red {
        color: #dc3545; /* Cor vermelha para T-Saída */
    }

    /* Animação de pulso para os ícones */
    @keyframes ft-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    /* Ajustes para o título principal */
    .st-emotion-cache-10trblm { /* Seletor para o título h1 */
        text-align: center;
        color: #0d6efd;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }

    /* Ajustes para o logo */
    .st-emotion-cache-1v0mbdj { /* Seletor para o container do logo */
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }

    /* Ajustes para o multiselect */
    .stMultiSelect {
        margin-bottom: 15px;
    }
    </style>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    """,
    unsafe_allow_html=True,
)

# =========================
#  FUNÇÕES AUXILIARES
# =========================

# Função para listar arquivos CSV e extrair informações de forma robusta
def listar_arquivos_csv(pasta):
    arquivos_info = []
    # Padrão regex para extrair informações do nome do arquivo
    # Ex: historico_L1_20240308_1842_OP1234_FTA987BR.csv
    # Grupos: 1=modelo, 2=data, 3=hora, 4=operacao, 5=maquina
    padrao_nome_arquivo = re.compile(
        r"historico_L\d+_(\d{8})_(\d{4})_OP(\d+)_([A-Z0-9]+)\.csv", re.IGNORECASE
    )

    for root, _, files in os.walk(pasta):
        for nome_arquivo in files:
            if nome_arquivo.endswith(".csv"):
                match = padrao_nome_arquivo.match(nome_arquivo)
                if match:
                    data_str, hora_str, operacao, maquina = match.groups()

                    try:
                        ano = int(data_str[:4])
                        mes = int(data_str[4:6])
                        dia = int(data_str[6:8])

                        # Formata a hora para HH:MM
                        hora_formatada = f"{hora_str[:2]}:{hora_str[2:]}"

                        # Formata a data para DD/MM/YYYY
                        data_formatada = f"{dia:02d}/{mes:02d}/{ano}"

                        arquivos_info.append(
                            {
                                "nome_arquivo": nome_arquivo,
                                "caminho": os.path.join(root, nome_arquivo),
                                "modelo": maquina, # Usando 'maquina' como modelo
                                "ano": ano,
                                "mes": mes,
                                "dia": dia,
                                "data_str": data_formatada,
                                "hora_str": hora_formatada,
                                "operacao": operacao,
                            }
                        )
                    except ValueError:
                        # Ignora arquivos com datas/horas mal formatadas
                        continue
                else:
                    # Se o nome do arquivo não corresponder ao padrão, ainda adiciona, mas com N/D
                    arquivos_info.append(
                        {
                            "nome_arquivo": nome_arquivo,
                            "caminho": os.path.join(root, nome_arquivo),
                            "modelo": "N/D",
                            "ano": 0,
                            "mes": 0,
                            "dia": 0,
                            "data_str": "N/D",
                            "hora_str": "N/D",
                            "operacao": "N/D",
                        }
                    )
    return arquivos_info

# Função para carregar CSV de forma robusta
@st.cache_data(ttl=3600) # Cache para melhorar performance
def carregar_csv_caminho(caminho_arquivo):
    try:
        # Tenta ler o CSV sem cabeçalho, pois os arquivos parecem não ter
        df = pd.read_csv(caminho_arquivo, header=None, encoding="utf-8", sep=';', on_bad_lines='skip')

        # Nomes de colunas esperados
        colunas_esperadas = [
            "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT",
            "Tensao", "Corrente", "Kcal_h", "Vazao", "KWAquecimento",
            "KWConsumo", "COP"
        ]

        # Se o número de colunas for diferente, ajusta
        if df.shape[1] < len(colunas_esperadas):
            # Adiciona colunas faltantes com NaN
            for i in range(df.shape[1], len(colunas_esperadas)):
                df[i] = pd.NA
        elif df.shape[1] > len(colunas_esperadas):
            # Remove colunas extras
            df = df.iloc[:, :len(colunas_esperadas)]

        df.columns = colunas_esperadas
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {os.path.basename(caminho_arquivo)}: {e}")
        # Retorna um DataFrame vazio com as colunas esperadas em caso de erro
        return pd.DataFrame(columns=colunas_esperadas)

# =========================
#  INICIALIZAÇÃO E CARREGAMENTO DE DADOS
# =========================

# Define o diretório onde os arquivos CSV estão localizados
CSV_DIR = "dados_csv" # Ajuste para o seu diretório real se for diferente

# Garante que o diretório exista
if not os.path.exists(CSV_DIR):
    os.makedirs(CSV_DIR)
    st.warning(f"O diretório '{CSV_DIR}' não foi encontrado. Criando-o. Por favor, adicione seus arquivos CSV aqui.")

# Carrega informações de todos os arquivos CSV
# Usa st.session_state para evitar recarregar a cada interação
if "todos_arquivos_info" not in st.session_state:
    st.session_state.todos_arquivos_info = listar_arquivos_csv(CSV_DIR)

todos_arquivos_info = st.session_state.todos_arquivos_info

# =========================
#  LAYOUT DO DASHBOARD
# =========================

# Logo da Fromtherm (substitua 'path/to/your/logo.png' pelo caminho real da sua logo)
# st.image("path/to/your/logo.png", width=200) # Descomente e ajuste o caminho da sua logo

st.markdown("<h1 style='text-align: center; color: #0d6efd;'>Dashboard de Teste de Máquinas Fromtherm</h1>", unsafe_allow_html=True)

# Abas para navegação
tab1, tab2, tab3 = st.tabs(["Última Leitura", "Históricos Disponíveis", "Crie Seu Gráfico"])

# --- ABA 1: Última Leitura ---
with tab1:
    st.markdown("## Última Leitura Registrada")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo CSV encontrado para exibir a última leitura.")
    else:
        # Encontra o arquivo mais recente
        # Ordena por ano, mês, dia, hora_str (que já está HH:MM) e operacao
        arquivos_ordenados = sorted(
            todos_arquivos_info,
            key=lambda x: (x["ano"], x["mes"], x["dia"], x["hora_str"], x["operacao"]),
            reverse=True,
        )
        arquivo_mais_recente = arquivos_ordenados[0]

        st.markdown(
            f"**Arquivo:** {arquivo_mais_recente['nome_arquivo']} | "
            f"**Data:** {arquivo_mais_recente['data_str']} | "
            f"**Hora:** {arquivo_mais_recente['hora_str']} | "
            f"**Modelo:** {arquivo_mais_recente['modelo']} | "
            f"**OP:** {arquivo_mais_recente['operacao']}"
        )

        df_dados = carregar_csv_caminho(arquivo_mais_recente["caminho"])

        if not df_dados.empty:
            ultima_linha = df_dados.iloc[-1]

            # Exibe as métricas em colunas
            col1, col2, col3, col4, col5, col6 = st.columns(6)

            def metric_card(col, icon, title, value, unit="", is_red=False):
                with col:
                    st.markdown(
                        f"""
                        <div class="ft-card {'red-border' if is_red else ''}">
                            <i class="bi {icon} ft-card-icon {'red' if is_red else ''}"></i>
                            <div class="ft-card-content">
                                <div class="ft-card-title">{title}</div>
                                <div class="ft-card-value {'red' if is_red else ''}">{value:.2f}{unit}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Usando .get() para acessar valores de forma segura e fornecer um default
            metric_card(col1, "bi-thermometer-half", "Ambiente", ultima_linha.get("Ambiente", 0.0), "°C")
            metric_card(col2, "bi-arrow-down", "T. Entrada", ultima_linha.get("Entrada", 0.0), "°C")
            metric_card(col3, "bi-arrow-up", "T. Saída", ultima_linha.get("Saída", 0.0), "°C", is_red=True)
            metric_card(col4, "bi-arrow-down-up", "ΔT", ultima_linha.get("DeltaT", 0.0), "°C")
            metric_card(col5, "bi-lightning", "Tensão", ultima_linha.get("Tensao", 0.0), "V")
            metric_card(col6, "bi-lightning-charge", "Corrente", ultima_linha.get("Corrente", 0.0), "A")

            col7, col8, col9, col10, col11 = st.columns(5)
            metric_card(col7, "bi-fire", "kcal/h", ultima_linha.get("Kcal_h", 0.0))
            metric_card(col8, "bi-speedometer", "Vazão", ultima_linha.get("Vazao", 0.0), "L/h")
            metric_card(col9, "bi-thermometer-sun", "kW Aquecimento", ultima_linha.get("KWAquecimento", 0.0), "kW")
            metric_card(col10, "bi-plug", "kW Consumo", ultima_linha.get("KWConsumo", 0.0), "kW")
            metric_card(col11, "bi-graph-up", "COP", ultima_linha.get("COP", 0.0))

        else:
            st.warning("Não foi possível carregar dados da última linha do arquivo mais recente.")

# --- ABA 2: Históricos Disponíveis ---
with tab2:
    st.markdown("## Históricos Disponíveis")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo CSV encontrado.")
    else:
        # Filtros
        col_filtro1, col_filtro2, col_filtro3, col_filtro4 = st.columns(4)

        with col_filtro1:
            modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))
            filtro_modelo = st.selectbox("Filtrar por Modelo:", ["Todos"] + modelos_disponiveis)

        with col_filtro2:
            anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"] != 0)), reverse=True)
            filtro_ano = st.selectbox("Filtrar por Ano:", ["Todos"] + anos_disponiveis)

        with col_filtro3:
            meses_map = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
            meses_disponiveis_numeros = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"] != 0)))
            meses_disponiveis_labels = ["Todos"] + [meses_map[m] for m in meses_disponiveis_numeros]
            filtro_mes_label = st.selectbox("Filtrar por Mês:", meses_disponiveis_labels)
            filtro_mes = list(meses_map.keys())[list(meses_map.values()).index(filtro_mes_label)] if filtro_mes_label != "Todos" else None

        with col_filtro4:
            ops_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"] != "N/D")))
            filtro_op = st.selectbox("Filtrar por OP:", ["Todas"] + ops_disponiveis)

        # Aplica os filtros
        arquivos_filtrados = todos_arquivos_info
        if filtro_modelo != "Todos":
            arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == filtro_modelo]
        if filtro_ano != "Todos":
            arquivos_filtrados = [a for a in arquivos_filtrados if a["ano"] == filtro_ano]
        if filtro_mes is not None:
            arquivos_filtrados = [a for a in arquivos_filtrados if a["mes"] == filtro_mes]
        if filtro_op != "Todas":
            arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == filtro_op]

        if not arquivos_filtrados:
            st.info("Nenhum arquivo encontrado com os filtros selecionados.")
        else:
            # Ordena para exibição
            arquivos_filtrados_ordenados = sorted(
                arquivos_filtrados,
                key=lambda x: (x["ano"], x["mes"], x["dia"], x["hora_str"], x["operacao"]),
                reverse=True,
            )

            # Cria um DataFrame para exibir na tabela
            df_exibicao = pd.DataFrame([
                {
                    "Modelo": a["modelo"],
                    "OP": a["operacao"],
                    "Data": a["data_str"],
                    "Hora": a["hora_str"],
                    "Nome do Arquivo": a["nome_arquivo"],
                    "Caminho": a["caminho"] # Mantém o caminho para uso interno
                }
                for a in arquivos_filtrados_ordenados
            ])

            # Exibe a tabela
            st.dataframe(df_exibicao.drop(columns=["Caminho"]), use_container_width=True)

            # Opção de download do arquivo selecionado
            st.markdown("### Baixar Arquivo Histórico")
            col_download1, col_download2 = st.columns(2)

            with col_download1:
                nomes_arquivos_para_download = [a["Nome do Arquivo"] for a in df_exibicao.to_dict('records')]
                arquivo_selecionado_nome = st.selectbox(
                    "Selecione o arquivo para baixar:",
                    nomes_arquivos_para_download,
                    key="download_select"
                )

            if arquivo_selecionado_nome:
                arquivo_selecionado_info = next((a for a in df_exibicao.to_dict('records') if a["Nome do Arquivo"] == arquivo_selecionado_nome), None)

                if arquivo_selecionado_info:
                    caminho_completo = arquivo_selecionado_info["Caminho"]
                    df_para_download = carregar_csv_caminho(caminho_completo)

                    # Formata o nome do arquivo para download
                    # Ex: Maquina_FTA987BR_OP987_08/03/2026_09:39hs.pdf
                    modelo_dl = arquivo_selecionado_info["Modelo"]
                    op_dl = arquivo_selecionado_info["OP"]
                    data_dl = arquivo_selecionado_info["Data"].replace("/", "") # Remove barras para nome de arquivo
                    hora_dl = arquivo_selecionado_info["Hora"].replace(":", "") # Remove dois pontos

                    nome_base_formatado = f"Maquina_{modelo_dl}_OP{op_dl}_{data_dl}_{hora_dl}"

                    # Download CSV
                    csv_buffer = BytesIO()
                    df_para_download.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8')
                    st.download_button(
                        label="Baixar CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"{nome_base_formatado}.csv",
                        mime="text/csv",
                        key="download_csv"
                    )

                    # Download PDF
                    def gerar_pdf(dataframe, info_arquivo):
                        buffer = BytesIO()
                        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
                        styles = getSampleStyleSheet()

                        # Estilo para título
                        style_title = ParagraphStyle(
                            'TitleStyle',
                            parent=styles['h2'],
                            fontSize=16,
                            spaceAfter=12,
                            alignment=1, # Center
                            textColor=colors.HexColor('#0d6efd')
                        )

                        # Estilo para subtítulos
                        style_subtitle = ParagraphStyle(
                            'SubtitleStyle',
                            parent=styles['h3'],
                            fontSize=12,
                            spaceAfter=6,
                            alignment=1, # Center
                            textColor=colors.HexColor('#343a40')
                        )

                        story = []
                        story.append(Paragraph(f"Relatório de Dados - Máquina {info_arquivo['Modelo']} OP {info_arquivo['OP']}", style_title))
                        story.append(Paragraph(f"Data: {info_arquivo['Data']} Hora: {info_arquivo['Hora']}", style_subtitle))
                        story.append(Spacer(1, 0.5*cm))

                        # Converte DataFrame para lista de listas para a tabela
                        data = [dataframe.columns.tolist()] + dataframe.values.tolist()
                        table = Table(data)

                        # Estilo da tabela
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
                            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
                        ]))
                        story.append(table)
                        doc.build(story)
                        buffer.seek(0)
                        return buffer

                    pdf_buffer = gerar_pdf(df_para_download, arquivo_selecionado_info)
                    st.download_button(
                        label="Baixar PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"{nome_base_formatado}.pdf",
                        mime="application/pdf",
                        key="download_pdf"
                    )

# --- ABA 3: Crie Seu Gráfico ---
with tab3:
    st.markdown("## Crie Seu Gráfico Personalizado")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo CSV encontrado para criar gráficos.")
    else:
        col1_graf, col2_graf, col3_graf, col4_graf = st.columns(4)

        with col1_graf:
            modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))
            modelo_graf = st.selectbox(
                "Selecione o Modelo:",
                modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum Modelo disponível"],
                key="graf_modelo",
            )

        with col2_graf:
            # Filtra anos com base no modelo selecionado
            anos_disponiveis_graf = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["modelo"] == modelo_graf and a["ano"] != 0)), reverse=True)
            ano_graf = st.selectbox(
                "Selecione o Ano:",
                anos_disponiveis_graf if anos_disponiveis_graf else ["Nenhum Ano disponível"],
                key="graf_ano",
            )

        with col3_graf:
            # Filtra meses com base no modelo e ano selecionados
            meses_disponiveis_graf_numeros = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["modelo"] == modelo_graf and a["ano"] == ano_graf and a["mes"] != 0)))
            meses_map = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
            meses_disponiveis_graf_labels = ["Todos"] + [meses_map[m] for m in meses_disponiveis_graf_numeros]
            mes_graf_label = st.selectbox(
                "Selecione o Mês:",
                meses_disponiveis_graf_labels,
                key="graf_mes",
            )
            mes_graf = list(meses_map.keys())[list(meses_map.values()).index(mes_graf_label)] if mes_graf_label != "Todos" else None

        with col4_graf:
            # Filtra as OPs com base nos modelos, anos e meses já selecionados
            arquivos_por_modelo_ano = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf and a["ano"] == ano_graf]
            arquivos_por_modelo_ano_mes = [a for a in arquivos_por_modelo_ano if a["mes"] == mes_graf or mes_graf is None]
            ops_disponiveis_graf = sorted(list(set(a["operacao"] for a in arquivos_por_modelo_ano_mes if a["operacao"] != "N/D")))

            default_op_index = 0
            if len(ops_disponiveis_graf) == 1:
                default_op_index = 0

            op_graf = st.selectbox(
                "Operação (OP):",
                ops_disponiveis_graf if ops_disponiveis_graf else ["Nenhuma OP disponível"],
                index=default_op_index if ops_disponiveis_graf else 0,
                key="graf_op",
            )

        arquivo_escolhido = None
        for a in todos_arquivos_info:
            if (
                a["modelo"] == modelo_graf
                and a["ano"] == ano_graf
                and (a["mes"] == mes_graf or mes_graf is None)
                and a["operacao"] == op_graf
            ):
                arquivo_escolhido = a
                break

        if not modelos_disponiveis_graf:
            st.info("Ainda não há dados suficientes para criar gráficos.")
        elif arquivo_escolhido is None:
            st.warning("Não foi encontrado um arquivo que combine este Modelo, Ano, Mês e Operação.")
        else:
            st.markdown(f"Arquivo selecionado: **{arquivo_escolhido['nome_arquivo']}**")

            try:
                df_graf = carregar_csv_caminho(arquivo_escolhido["caminho"]).copy()

                # As colunas já foram renomeadas dentro de carregar_csv_caminho
                # df_graf.columns = [ ... ] # Esta linha não é mais necessária aqui

                try:
                    df_graf["DateTime"] = pd.to_datetime(
                        df_graf["Date"].astype(str) + " " + df_graf["Time"].astype(str),
                        errors="coerce",
                    )
                except Exception:
                    df_graf["DateTime"] = df_graf["Time"]

                st.markdown("### Variáveis para o gráfico")

                variaveis_opcoes = [
                    "Ambiente",
                    "Entrada",
                    "Saída",
                    "DeltaT",
                    "Tensao",
                    "Corrente",
                    "Kcal_h",
                    "Vazao",
                    "KWAquecimento",
                    "KWConsumo",
                    "COP",
                ]

                # Filtra as variáveis que realmente existem no DataFrame carregado
                variaveis_disponiveis_no_df = [v for v in variaveis_opcoes if v in df_graf.columns]

                vars_selecionadas = st.multiselect(
                    "Selecione uma ou mais variáveis:",
                    variaveis_disponiveis_no_df,
                    default=[v for v in ["Ambiente", "Entrada", "Saída"] if v in variaveis_disponiveis_no_df], # Define um default mais seguro
                )

                if not vars_selecionadas:
                    st.info("Selecione pelo menos uma variável para gerar o gráfico.")
                else:
                    # Garante que apenas as colunas selecionadas e 'DateTime' sejam usadas
                    df_plot = df_graf[["DateTime"] + vars_selecionadas].copy()

                    # Melt o DataFrame para o formato longo, ideal para Plotly Express
                    df_melted = df_plot.melt(
                        id_vars="DateTime",
                        value_vars=vars_selecionadas,
                        var_name="Variável",
                        value_name="Valor",
                    )

                    fig = px.line(
                        df_melted,
                        x="DateTime",
                        y="Valor",
                        color="Variável",
                        title=f"Gráfico - Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{mes_graf_label.split(' ')[0] if mes_graf_label != 'Todos' else 'Todos os Meses'}",
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

                    st.markdown(
                        "- Use o botão de **fullscreen** no gráfico para expandir.\n"
                        "- Use o ícone de **câmera** no gráfico para baixar como imagem (PNG).\n"
                        "- A imagem baixada pode ser compartilhada via WhatsApp, e-mail, etc., em qualquer dispositivo."
                    )

            except Exception as e:
                st.error(f"Erro ao carregar dados para o gráfico: {e}")
                st.info("Verifique se o arquivo CSV está no formato correto e se as colunas esperadas existem.")