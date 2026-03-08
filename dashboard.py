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
#  CSS GLOBAL (fundo padrão, correção do "0", cards com animação suave)
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
st.title("Teste de Máquinas Fromtherm") # Título visível na página

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
        data = datetime.min.date() # Inicializa com data mínima para evitar None
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
            # Se houver erro no parsing, data permanece datetime.min.date()
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


# --- Função para carregar um CSV (ponto e vírgula ou vírgula) ---
def carregar_csv_caminho(caminho: str) -> pd.DataFrame:
    try:
        return pd.read_csv(caminho, sep=";", engine="python")
    except Exception:
        return pd.read_csv(caminho, sep=",", engine="python")


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo .csv de histórico encontrado na pasta '{DADOS_DIR}'.")
    st.info("Verifique se os arquivos .csv foram sincronizados corretamente para o GitHub.")
    st.stop()

# --- Determinar o arquivo mais recente (por data + hora) ---
# Garante que 'data' seja sempre um objeto datetime.date válido
arquivo_mais_recente = max(
    todos_arquivos_info,
    key=lambda x: (
        x["data"], # Já inicializado com datetime.min.date() ou data real
        x["hora"] or "",
    ),
)

# =====================================================
#  PAINEL: Última leitura registrada (cards com ícones)
# =====================================================
st.markdown("### Última Leitura Registrada")

# Exibe as informações do arquivo mais recente
st.markdown(
    f"**Modelo:** **{arquivo_mais_recente['modelo']}** | **OP:** **{arquivo_mais_recente['operacao']}** | **Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | **Hora:** {arquivo_mais_recente['hora']}"
)

# Carrega os dados do arquivo mais recente para extrair a última linha
try:
    df_mais_recente = carregar_csv_caminho(arquivo_mais_recente["caminho"])
    ultima_linha = df_mais_recente.iloc[-1]

    # Mapeamento de nomes de colunas para exibição e ícones
    metricas = {
        "T-Ambiente": {"col": "Ambiente", "icon": "bi-thermometer-half"},
        "T-Entrada": {"col": "Entrada", "icon": "bi-arrow-down-circle"},
        "T-Saída": {"col": "Saída", "icon": "bi-arrow-up-circle", "class": "red"},
        "DIF (ΔT)": {"col": "ΔT", "icon": "bi-arrow-down-up"}, # Novo ícone para diferencial
        "Tensão": {"col": "Tensão", "icon": "bi-lightning-charge"},
        "Corrente": {"col": "Corrente", "icon": "bi-lightning"},
        "kcal/h": {"col": "kcal/h", "icon": "bi-fire"},
        "Vazão": {"col": "Vazão", "icon": "bi-droplet"},
        "kW Aquecimento": {"col": "kW Aquecimento", "icon": "bi-sun"},
        "kW Consumo": {"col": "kW Consumo", "icon": "bi-plug"},
        "COP": {"col": "COP", "icon": "bi-speedometer2"},
    }

    cols = st.columns(3) # 3 colunas para os cards

    for i, (titulo, info) in enumerate(metricas.items()):
        with cols[i % 3]: # Distribui os cards nas 3 colunas
            valor = ultima_linha[info["col"]] if info["col"] in ultima_linha else "N/A"
            icon_class = info.get("class", "") # Pega a classe 'red' se existir
            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi {info['icon']} ft-card-icon {icon_class}"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">{titulo}</p>
                    <p class="ft-card-value">{valor}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

except Exception as e:
    st.error(f"Não foi possível gerar o painel da última leitura: {e}")
    st.info("Verifique se o formato do CSV está conforme o padrão esperado e se há dados nos arquivos.")

st.markdown("---") # Separador visual

# =====================================================
#  ABA: Históricos e Planilhas
# =====================================================
tab1, tab2 = st.tabs(["📄 Históricos e Planilhas", "📊 Crie Seu Gráfico"])

with tab1:
    st.markdown("### Históricos Disponíveis")

    # Filtros para a lista de históricos
    modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    modelo_selecionado = st.selectbox(
        "Filtrar por Modelo:",
        ["Todos"] + modelos_disponiveis,
        key="hist_modelo",
    )

    anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])))
    ano_selecionado = st.selectbox(
        "Filtrar por Ano:",
        ["Todos"] + anos_disponiveis,
        key="hist_ano",
    )

    meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
    mes_label_map = {
        1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
        5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
        9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
    }
    meses_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis] if meses_disponiveis else ["Todos"]

    mes_selecionado_label = st.selectbox(
        "Filtrar por Mês:",
        meses_labels,
        key="hist_mes",
    )
    mes_selecionado = None
    if mes_selecionado_label != "Todos":
        mes_selecionado = int(mes_selecionado_label.split(" ")[0])

    data_especifica_str = st.text_input(
        "Data específica (opcional): YYYY/MM/DD", key="hist_data_especifica"
    )
    data_especifica = None
    if data_especifica_str:
        try:
            data_especifica = datetime.strptime(data_especifica_str, "%Y/%m/%d").date()
        except ValueError:
            st.error("Formato de data inválido. Use YYYY/MM/DD.")

    ops_disponiveis_filtro = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))
    op_selecionada = st.selectbox(
        "Operação (OPs):",
        ["Todas"] + ops_disponiveis_filtro,
        key="hist_op",
    )

    # Aplica os filtros
    arquivos_filtrados = [
        a
        for a in todos_arquivos_info
        if (modelo_selecionado == "Todos" or a["modelo"] == modelo_selecionado)
        and (ano_selecionado == "Todos" or a["ano"] == ano_selecionado)
        and (mes_selecionado is None or a["mes"] == mes_selecionado)
        and (data_especifica is None or a["data"] == data_especifica)
        and (op_selecionada == "Todas" or a["operacao"] == op_selecionada)
    ]

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arquivo in sorted(arquivos_filtrados, key=lambda x: (x["data"], x["hora"]), reverse=True):
            expander_title = f"**{arquivo['modelo']}** - Linha: {arquivo['linha']} - Data: {arquivo['data'].strftime('%d/%m/%Y')} - Hora: {arquivo['hora']} - Operação: {arquivo['operacao']}"
            with st.expander(expander_title):
                st.write(f"Nome do arquivo: `{arquivo['nome_arquivo']}`")
                df = carregar_csv_caminho(arquivo["caminho"])
                st.dataframe(df, use_container_width=True)

                # Botões de download
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    csv_data = df.to_csv(index=False, sep=";").encode("utf-8")
                    st.download_button(
                        label="Baixar como CSV",
                        data=csv_data,
                        file_name=f"{arquivo['nome_arquivo'].replace('.csv', '')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with col_dl2:
                    # Geração de PDF
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
                    styles = getSampleStyleSheet()
                    elements = []

                    elements.append(Paragraph(f"Relatório de Teste - {arquivo['modelo']} / {arquivo['operacao']}", styles["h2"]))
                    elements.append(Paragraph(f"Data: {arquivo['data'].strftime('%d/%m/%Y')} - Hora: {arquivo['hora']}", styles["Normal"]))
                    elements.append(Spacer(1, 12))

                    # Preparar dados para a tabela PDF
                    data_pdf = [df.columns.tolist()] + df.values.tolist()
                    table = Table(data_pdf)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                    ]))
                    elements.append(table)
                    doc.build(elements)
                    pdf_data = buffer.getvalue()

                    st.download_button(
                        label="Baixar como PDF",
                        data=pdf_data,
                        file_name=f"{arquivo['nome_arquivo'].replace('.csv', '')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

with tab2:
    st.markdown("### Crie Seu Gráfico")

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