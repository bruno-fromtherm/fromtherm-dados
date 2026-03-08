import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
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
    /* REMOÇÃO FINAL DO "0" TEIMOSO (corrigido e mais robusto) */
    /* Esconde o botão de menu que pode conter o "0" e o próprio ícone de menu */
    button[data-testid="stSidebarNavToggle"],
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > div:first-child > span,
    div[data-testid="stAppViewContainer"] > div:first-child > div:first-child > div:first-child > div:first-child > span,
    span[data-testid="stDecoration"],
    summary,
    button[title="View options"],
    .st-emotion-cache-1r6dm1x, /* Seletor específico para o ícone de menu */
    .st-emotion-cache-10q71g7 /* Seletor específico para o container do ícone de menu */
    {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
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

# --- Colunas esperadas e seus nomes padronizados ---
COLUNAS_ESPERADAS = [
    "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao",
    "Corrente", "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
]

# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para atualizar dados mais frequentemente
def listar_arquivos_csv():
    caminhos_arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    todos_arquivos_info = []

    for caminho in caminhos_arquivos:
        nome_arquivo = os.path.basename(caminho)
        info_arquivos = {
            "nome_arquivo": nome_arquivo,
            "caminho": caminho,
            "modelo": "N/D",
            "operacao": "N/D",
            "data": datetime.min.date(),  # Valor padrão muito antigo
            "hora": "00:00",
            "ano": 0,
            "mes": 0,
        }

        try:
            # Ex: historico_L1_20231026_1030_OP1234_FT567.csv
            partes = nome_arquivo.split("_")
            if len(partes) >= 6:
                info_arquivos["modelo"] = partes[1]
                data_str = partes[2]
                hora_str = partes[3]
                op_str = partes[4]

                info_arquivos["data"] = datetime.strptime(data_str, "%Y%m%d").date()
                info_arquivos["hora"] = f"{hora_str[:2]}:{hora_str[2:]}"
                info_arquivos["operacao"] = op_str.replace("OP", "")
                info_arquivos["ano"] = info_arquivos["data"].year
                info_arquivos["mes"] = info_arquivos["data"].month
        except Exception:
            # Se houver erro no parsing, usa os valores padrão (N/D, datetime.min.date(), etc.)
            pass
        todos_arquivos_info.append(info_arquivos)

    # Ordena os arquivos do mais recente para o mais antigo
    todos_arquivos_info.sort(key=lambda x: (x["data"], x["hora"]), reverse=True)
    return todos_arquivos_info

# --- Função para carregar um CSV específico e renomear colunas ---
@st.cache_data(ttl=10)
def carregar_csv_caminho(caminho_arquivo):
    try:
        # Tenta ler o CSV. Se tiver cabeçalho, ele será ignorado na renomeação.
        df = pd.read_csv(caminho_arquivo, header=None)

        # Verifica se o número de colunas é compatível
        if df.shape[1] < len(COLUNAS_ESPERADAS):
            # Se tiver menos colunas, preenche as faltantes com NaN
            for _ in range(len(COLUNAS_ESPERADAS) - df.shape[1]):
                df[f"col_extra_{df.shape[1]}"] = pd.NA
        elif df.shape[1] > len(COLUNAS_ESPERADAS):
            # Se tiver mais colunas, trunca para o número esperado
            df = df.iloc[:, :len(COLUNAS_ESPERADAS)]

        df.columns = COLUNAS_ESPERADAS
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV {os.path.basename(caminho_arquivo)}: {e}")
        return pd.DataFrame(columns=COLUNAS_ESPERADAS) # Retorna um DataFrame vazio com as colunas esperadas

# --- Carregar informações de todos os arquivos CSV ---
# Garante que todos_arquivos_info esteja sempre definida
todos_arquivos_info = listar_arquivos_csv()
if not todos_arquivos_info:
    st.warning("Nenhum arquivo de histórico encontrado na pasta especificada.")
    st.stop() # Para a execução do script se não houver arquivos

# --- Determinar o arquivo mais recente (por data + hora) ---
arquivo_mais_recente = max(
    todos_arquivos_info, key=lambda x: (x["data"], x["hora"])
)

# --- Carregar os dados do arquivo mais recente ---
df_dados = carregar_csv_caminho(arquivo_mais_recente["caminho"])

# --- Pega a última linha para exibir as métricas mais recentes ---
ultima_linha = df_dados.iloc[-1] if not df_dados.empty else pd.Series(index=COLUNAS_ESPERADAS)

# --- Exibir as métricas da última leitura ---
st.markdown("## Última Leitura")
st.markdown(
    f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
    f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
    f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | "
    f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
)

col1, col2, col3, col4 = st.columns(4)
col5, col6, col7, col8 = st.columns(4)
col9, col10, col11 = st.columns(3) # Ajustado para 3 colunas na última linha

# Função auxiliar para exibir um card de métrica
def exibir_card(col, titulo, valor, unidade, icone, is_red=False):
    with col:
        st.markdown(
            f"""
            <div class="ft-card {'red-border' if is_red else ''}">
                <i class="bi {icone} ft-card-icon {'red' if is_red else ''}"></i>
                <div class="ft-card-content">
                    <p class="ft-card-title">{titulo}</p>
                    <p class="ft-card-value">{valor} {unidade}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Exibir os cards com os valores da última linha
# Adicionado .get() com valor padrão para evitar KeyError se a coluna não existir
exibir_card(col1, "T-Ambiente", f"{ultima_linha.get('Ambiente', 'N/D'):.1f}", "°C", "bi-thermometer-half")
exibir_card(col2, "T-Entrada", f"{ultima_linha.get('Entrada', 'N/D'):.1f}", "°C", "bi-arrow-down-circle")
exibir_card(col3, "T-Saída", f"{ultima_linha.get('Saída', 'N/D'):.1f}", "°C", "bi-arrow-up-circle", is_red=True)
exibir_card(col4, "DIF (ΔT)", f"{ultima_linha.get('DeltaT', 'N/D'):.1f}", "°C", "bi-arrow-down-up") # Novo ícone para diferencial

exibir_card(col5, "Tensão", f"{ultima_linha.get('Tensao', 'N/D'):.1f}", "V", "bi-lightning-charge")
exibir_card(col6, "Corrente", f"{ultima_linha.get('Corrente', 'N/D'):.1f}", "A", "bi-lightning")
exibir_card(col7, "kcal/h", f"{ultima_linha.get('Kcal_h', 'N/D'):.1f}", "", "bi-fire")
exibir_card(col8, "Vazão", f"{ultima_linha.get('Vazao', 'N/D'):.1f}", "L/h", "bi-water")

exibir_card(col9, "kW Aquecimento", f"{ultima_linha.get('KWAquecimento', 'N/D'):.1f}", "kW", "bi-sun")
exibir_card(col10, "kW Consumo", f"{ultima_linha.get('KWConsumo', 'N/D'):.1f}", "kW", "bi-plug")
exibir_card(col11, "COP", f"{ultima_linha.get('COP', 'N/D'):.2f}", "", "bi-graph-up")

st.markdown("---")

# --- Abas para Histórico e Gráficos ---
tab1, tab2 = st.tabs(["Histórico de Planilhas", "Gráficos"])

with tab1:
    st.markdown("## Histórico de Planilhas")

    # Filtros para o histórico
    modelos_disponiveis_hist = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    modelo_hist = st.selectbox(
        "Modelo:",
        modelos_disponiveis_hist if modelos_disponiveis_hist else ["Nenhum modelo disponível"],
        key="hist_modelo",
    )

    anos_disponiveis_hist = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["modelo"] == modelo_hist)), reverse=True)
    ano_hist = st.selectbox(
        "Ano:",
        anos_disponiveis_hist if anos_disponiveis_hist else [datetime.now().year],
        key="hist_ano",
    )

    meses_disponiveis_hist = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["modelo"] == modelo_hist and a["ano"] == ano_hist)))
    meses_labels_hist = ["Todos"] + [f"{m:02d} - {datetime(1, m, 1).strftime('%B')}" for m in meses_disponiveis_hist]
    mes_hist_label = st.selectbox(
        "Mês:",
        meses_labels_hist,
        key="hist_mes",
    )
    mes_hist = None
    if mes_hist_label != "Todos":
        mes_hist = int(mes_hist_label.split(" ")[0])

    arquivos_filtrados_hist = [
        a for a in todos_arquivos_info
        if a["modelo"] == modelo_hist
        and a["ano"] == ano_hist
        and (a["mes"] == mes_hist or mes_hist is None)
    ]

    if not arquivos_filtrados_hist:
        st.info("Nenhum arquivo encontrado para os filtros selecionados.")
    else:
        # Cria um DataFrame para exibir na tabela
        df_historico = pd.DataFrame([
            {
                "Modelo": a["modelo"],
                "OP": a["operacao"],
                "Data": a["data"].strftime("%d/%m/%Y"),
                "Hora": a["hora"],
                "Nome do Arquivo": a["nome_arquivo"],
                "Caminho": a["caminho"],
            }
            for a in arquivos_filtrados_hist
        ])

        st.dataframe(df_historico[["Modelo", "OP", "Data", "Hora", "Nome do Arquivo"]], use_container_width=True)

        # Opções de download
        st.markdown("### Download de Históricos")
        arquivo_para_download_nome = st.selectbox(
            "Selecione um arquivo para download:",
            df_historico["Nome do Arquivo"].tolist(),
            key="download_file_name",
        )

        if arquivo_para_download_nome:
            caminho_download = df_historico[df_historico["Nome do Arquivo"] == arquivo_para_download_nome]["Caminho"].iloc[0]
            df_download = carregar_csv_caminho(caminho_download)

            col_dl1, col_dl2 = st.columns(2)

            with col_dl1:
                csv_data = df_download.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Baixar CSV",
                    data=csv_data,
                    file_name=f"{arquivo_para_download_nome}",
                    mime="text/csv",
                    use_container_width=True,
                )

            with col_dl2:
                # Geração de PDF
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
                styles = getSampleStyleSheet()
                elements = []

                # Título do PDF
                elements.append(Paragraph(f"Relatório de Dados - {arquivo_para_download_nome}", styles["h2"]))
                elements.append(Spacer(1, 0.5 * cm))

                # Tabela de dados
                data_table = [df_download.columns.tolist()] + df_download.values.tolist()
                table = Table(data_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)

                doc.build(elements)
                pdf_data = buffer.getvalue()
                buffer.close()

                st.download_button(
                    label="Baixar PDF",
                    data=pdf_data,
                    file_name=f"{arquivo_para_download_nome.replace('.csv', '.pdf')}",
                    mime="application/pdf",
                    use_container_width=True,
                )

with tab2:
    st.markdown("## Gráficos de Histórico")

    # Filtros para o gráfico
    modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    modelo_graf = st.selectbox(
        "Modelo:",
        modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum modelo disponível"],
        key="graf_modelo",
    )

    anos_disponiveis_graf = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["modelo"] == modelo_graf)), reverse=True)
    ano_graf = st.selectbox(
        "Ano:",
        anos_disponiveis_graf if anos_disponiveis_graf else [datetime.now().year],
        key="graf_ano",
    )

    meses_disponiveis_graf = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["modelo"] == modelo_graf and a["ano"] == ano_graf)))
    meses_labels_graf = ["Todos"] + [f"{m:02d} - {datetime(1, m, 1).strftime('%B')}" for m in meses_disponiveis_graf]
    mes_graf_label = st.selectbox(
        "Mês:",
        meses_labels_graf,
        key="graf_mes",
    )
    mes_graf = None
    if mes_graf_label != "Todos":
        mes_graf = int(mes_graf_label.split(" ")[0])

    arquivos_por_modelo_ano_mes = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf and a["ano"] == ano_graf and (a["mes"] == mes_graf or mes_graf is None)]

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
                "DeltaT", # Corrigido para DeltaT
                "Tensao", # Corrigido para Tensao
                "Corrente",
                "Kcal_h", # Corrigido para Kcal_h
                "Vazao", # Corrigido para Vazao
                "KWAquecimento", # Corrigido para KWAquecimento
                "KWConsumo", # Corrigido para KWConsumo
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

