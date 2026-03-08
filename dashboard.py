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
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm") # Título da aba do navegador

# =========================
#  CSS GLOBAL (correção do "0", cards com animação suave)
# =========================
st.markdown(
    """
    <style>
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde qualquer elemento span que seja o primeiro filho de um div no topo da página */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > div:first-child > span {
        display: none !important;
    }
    /* Uma alternativa mais genérica, caso a de cima não funcione em todos os casos */
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > span {
        display: none !important;
    }
    /* E uma última tentativa para qualquer span pequeno e solto no topo */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Outra tentativa para esconder o "0" que pode ser um elemento de "summary" */
    summary {
        display: none !important;
    }
    /* Esconder o botão de menu que pode conter o "0" */
    button[title="View options"] {
        display: none !important;
    }
    /* Esconder o ícone de menu do Streamlit que pode conter o "0" */
    .st-emotion-cache-1r6dm1x { /* Seletor específico para o ícone de menu */
        display: none !important;
    }
    /* Esconder o elemento pai do ícone de menu */
    .st-emotion-cache-10q71g7 { /* Seletor específico para o container do ícone de menu */
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
        color: #444444;
        margin: 0;
        padding: 0;
    }
    .ft-card-value {
        font-size: 18px;
        font-weight: 700;
        color: #111111;
        margin: 0;
        padding: 0;
    }

    /* Animação de pulso suave (única para todos os ícones) */
    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 0.9; }
        50%  { transform: scale(1.05); opacity: 1; }
        100% { transform: scale(1);   opacity: 0.9; }
    }
    </style>

    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Teste de Máquinas Fromtherm") # Título principal do dashboard

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
        data = datetime.min.date() # Garante que data nunca será None
        ano = None
        mes = None
        hora = ""
        operacao = ""
        modelo = ""

        try:
            partes = nome.replace(".csv", "").split("_")
            # esperado: historico_L1_20260303_2140_OP1234_FT185.csv
            if len(partes) >= 6:
                linha = partes[1]
                data_str = partes[2]
                hora_str = partes[3]
                operacao = partes[4]
                modelo = partes[5]

                data = datetime.strptime(data_str, "%Y%m%d").date()
                ano = data.year
                mes = data.month
                hora = hora_str[:2] + ":" + hora_str[2:] # Formato HH:MM

        except Exception:
            # Se houver erro na extração, usa valores padrão
            pass

        info_arquivos.append(
            {
                "caminho": caminho,
                "nome_arquivo": nome,
                "linha": linha,
                "data": data,
                "ano": ano,
                "mes": mes,
                "hora": hora,
                "operacao": operacao,
                "modelo": modelo,
            }
        )
    return sorted(info_arquivos, key=lambda x: (x["data"], x["hora"]), reverse=True)


# --- Função para carregar CSV e renomear colunas ---
@st.cache_data(ttl=60)
def carregar_csv_caminho(caminho_arquivo):
    try:
        # Tenta ler com ponto e vírgula, depois com vírgula
        try:
            df = pd.read_csv(caminho_arquivo, sep=";", encoding="latin1")
        except Exception:
            df = pd.read_csv(caminho_arquivo, sep=",", encoding="latin1")

        # Renomeia as colunas para os nomes esperados
        df.columns = [
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
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{caminho_arquivo}': {e}")
        st.info("Verifique se o arquivo CSV está no formato correto e não está vazio.")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro


# --- Mapeamento de números de mês para nomes ---
mes_label_map = {
    1: "01 Janeiro",
    2: "02 Fevereiro",
    3: "03 Março",
    4: "04 Abril",
    5: "05 Maio",
    6: "06 Junho",
    7: "07 Julho",
    8: "08 Agosto",
    9: "09 Setembro",
    10: "10 Outubro",
    11: "11 Novembro",
    12: "12 Dezembro",
}


# --- Função para criar PDF (se necessário) ---
# Esta função não está definida no código fornecido,
# então o botão de download de PDF estará comentado.
# Se você precisar dela, precisará implementá-la.
def criar_pdf_paisagem(df, info_arquivo):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = []

    # Título
    story.append(Paragraph("Relatório de Teste FromTherm", styles["h1"]))
    story.append(Spacer(1, 0.2 * cm))

    # Informações do arquivo
    info_text = (
        f"<b>Modelo:</b> {info_arquivo['modelo'] or 'N/D'}<br/>"
        f"<b>Operação (OP):</b> {info_arquivo['operacao'] or 'N/D'}<br/>"
        f"<b>Data:</b> {info_arquivo['data'].strftime('%d/%m/%Y') if info_arquivo['data'] else 'N/D'}<br/>"
        f"<b>Hora:</b> {info_arquivo['hora'] or 'N/D'}"
    )
    story.append(Paragraph(info_text, styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    # Tabela de dados
    data_table = [df.columns.tolist()] + df.values.tolist()
    table = Table(data_table)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer


# --- Carregar todos os arquivos CSV disponíveis ---
todos_arquivos_info = listar_arquivos_csv()

# --- Abas do Dashboard ---
tab_leitura, tab_historicos, tab_graf = st.tabs(
    ["Última Leitura Registrada", "Históricos e Planilhas", "Crie Seu Gráfico"]
)


# =========================
#  TAB 1 - ÚLTIMA LEITURA REGISTRADA
# =========================
with tab_leitura:
    st.subheader("Última Leitura Registrada")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo de histórico encontrado na pasta de dados.")
    else:
        # O arquivo mais recente já está no topo da lista ordenada
        arquivo_mais_recente = todos_arquivos_info[0]

        try:
            df_dados = carregar_csv_caminho(arquivo_mais_recente["caminho"])
            if df_dados.empty:
                st.warning("O arquivo mais recente está vazio ou não pôde ser lido.")
            else:
                ultima_linha = df_dados.iloc[-1]

                st.markdown(
                    f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
                    f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
                    f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | "
                    f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
                )
                st.markdown("---")

                col1, col2, col3 = st.columns(3)

                # Dicionário de métricas com ícones e classes CSS
                metricas = [
                    {"titulo": "T-Ambiente", "valor": ultima_linha["Ambiente"], "unidade": "°C", "icone": "bi-thermometer-half", "class": ""},
                    {"titulo": "T-Entrada", "valor": ultima_linha["Entrada"], "unidade": "°C", "icone": "bi-arrow-down-circle", "class": ""},
                    {"titulo": "T-Saída", "valor": ultima_linha["Saída"], "unidade": "°C", "icone": "bi-arrow-up-circle", "class": "red"},
                    {"titulo": "DIF (ΔT)", "valor": ultima_linha["ΔT"], "unidade": "°C", "icone": "bi-arrow-down-up", "class": ""},
                    {"titulo": "Tensão", "valor": ultima_linha["Tensão"], "unidade": "V", "icone": "bi-lightning-charge", "class": ""},
                    {"titulo": "Corrente", "valor": ultima_linha["Corrente"], "unidade": "A", "icone": "bi-plug", "class": ""},
                    {"titulo": "kcal/h", "valor": ultima_linha["kcal/h"], "unidade": "", "icone": "bi-fire", "class": ""},
                    {"titulo": "Vazão", "valor": ultima_linha["Vazão"], "unidade": "", "icone": "bi-water", "class": ""},
                    {"titulo": "kW Aquecimento", "valor": ultima_linha["kW Aquecimento"], "unidade": "", "icone": "bi-thermometer-sun", "class": ""},
                    {"titulo": "kW Consumo", "valor": ultima_linha["kW Consumo"], "unidade": "", "icone": "bi-power", "class": ""},
                    {"titulo": "COP", "valor": ultima_linha["COP"], "unidade": "", "icone": "bi-graph-up", "class": ""},
                ]

                # Exibir as métricas em 3 colunas
                for i, metrica in enumerate(metricas):
                    with [col1, col2, col3][i % 3]:
                        st.markdown(
                            f"""
                            <div class="ft-card">
                                <i class="bi {metrica['icone']} ft-card-icon {metrica['class']}"></i>
                                <div class="ft-card-content">
                                    <p class="ft-card-title">{metrica['titulo']}</p>
                                    <p class="ft-card-value">{metrica['valor']:.2f} {metrica['unidade']}</p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                st.markdown("---")

        except Exception as e:
            st.error(f"Não foi possível gerar o painel da última leitura: {e}")
            st.info("Verifique se o formato do CSV está conforme o padrão esperado.")


# =========================
#  TAB 2 - HISTÓRICOS E PLANILHAS
# =========================
with tab_historicos:
    st.subheader("Históricos Disponíveis")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo de histórico encontrado na pasta de dados.")
    else:
        # Filtros para a lista de históricos
        modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
        modelo_selecionado = st.selectbox(
            "Filtrar por Modelo:",
            ["Todos"] + modelos_disponiveis,
            key="hist_modelo",
        )

        anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])), reverse=True)
        ano_selecionado = st.selectbox(
            "Filtrar por Ano:",
            ["Todos"] + anos_disponiveis,
            key="hist_ano",
        )

        meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
        meses_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis]
        mes_selecionado_label = st.selectbox(
            "Filtrar por Mês:",
            meses_labels,
            key="hist_mes",
        )
        mes_selecionado = None
        if mes_selecionado_label != "Todos":
            mes_selecionado = int(mes_selecionado_label.split(" ")[0])

        arquivos_filtrados = [
            a
            for a in todos_arquivos_info
            if (modelo_selecionado == "Todos" or a["modelo"] == modelo_selecionado)
            and (ano_selecionado == "Todos" or a["ano"] == ano_selecionado)
            and (mes_selecionado is None or a["mes"] == mes_selecionado)
        ]

        if not arquivos_filtrados:
            st.warning("Nenhum arquivo encontrado com os filtros selecionados.")
        else:
            st.markdown("---")
            st.markdown("### Lista de Históricos")

            for i, arquivo in enumerate(arquivos_filtrados):
                st.markdown(
                    f"**{arquivo['modelo'] or 'N/D'}** | "
                    f"OP: **{arquivo['operacao'] or 'N/D'}** | "
                    f"Data: **{arquivo['data'].strftime('%d/%m/%Y')}** | "
                    f"Hora: **{arquivo['hora'] or 'N/D'}**"
                )

                col_download_csv, col_download_pdf = st.columns(2)

                # Botão de download CSV
                try:
                    df_download = carregar_csv_caminho(arquivo["caminho"])
                    csv_buffer = BytesIO()
                    df_download.to_csv(csv_buffer, index=False, sep=";", encoding="latin1")
                    csv_buffer.seek(0)

                    data_nome = arquivo["data"].strftime("%Y%m%d")
                    hora_nome = arquivo["hora"].replace(":", "")

                    with col_download_csv:
                        st.download_button(
                            label="Baixar CSV",
                            data=csv_buffer,
                            file_name=(
                                f"Maquina_{arquivo['modelo'] or 'N_D'}_"
                                f"{arquivo['operacao'] or 'OP'}_"
                                f"{data_nome}_{hora_nome}.csv"
                            ),
                            mime="text/csv",
                            key=f"csv_download_{i}",
                        )
                except Exception as e:
                    with col_download_csv:
                        st.error(f"Erro ao preparar CSV para download: {e}")

                # Botão de download PDF (descomentado e usando a função criar_pdf_paisagem)
                with col_download_pdf:
                    try:
                        df_pdf = carregar_csv_caminho(arquivo["caminho"])
                        if not df_pdf.empty:
                            pdf_buffer = criar_pdf_paisagem(df_pdf, arquivo)
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
                        else:
                            st.warning("PDF não disponível (arquivo CSV vazio).")
                    except Exception as e:
                        st.error(f"Erro ao preparar PDF para download: {e}")

                st.markdown("---")

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

    modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))

    modelo_graf = st.selectbox(
        "Modelo:",
        modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum modelo disponível"],
        key="graf_modelo",
    )

    arquivos_por_modelo = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf]

    anos_disponiveis_graf = sorted(list(set(a["ano"] for a in arquivos_por_modelo if a["ano"])))

    ano_graf = st.selectbox(
        "Ano:",
        anos_disponiveis_graf if anos_disponiveis_graf else ["Nenhum ano disponível"],
        key="graf_ano",
    )

    arquivos_por_modelo_ano = [a for a in arquivos_por_modelo if a["ano"] == ano_graf]

    meses_disponiveis_graf = sorted(list(set(a["mes"] for a in arquivos_por_modelo_ano if a["mes"])))
    meses_labels_graf = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis_graf] if meses_disponiveis_graf else ["Todos"]

    mes_graf_label = st.selectbox(
        "Mês:",
        meses_labels_graf,
        key="graf_mes",
    )
    mes_graf = None
    if mes_graf_label != "Todos":
        mes_graf = int(mes_graf_label.split(" ")[0])

    arquivos_por_modelo_ano_mes = [a for a in arquivos_por_modelo_ano if a["mes"] == mes_graf or mes_graf is None]

    ops_disponiveis_graf = sorted(list(set(a["operacao"] for a in arquivos_por_modelo_ano_mes if a["operacao"])))

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
                df_plot = df_graf[["DateTime"] + vars_selecionadas].copy()
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
                    title=f"Gráfico - Modelo {modelo_graf} | OP {op_graf} | {ano_graf}/{mes_graf_label.split(' ')[0]}",
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
            st.info("Verifique se o arquivo CSV está no formato correto.")

