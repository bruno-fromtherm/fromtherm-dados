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
st.sidebar.title("Navegação")

# --- Funções de processamento de dados ---

# Mapeamento de nomes de colunas esperados
COLUNAS_ESPERADAS = [
    "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT",
    "Tensao", "Corrente", "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
]

@st.cache_data
def carregar_csv_caminho(caminho_arquivo):
    try:
        # Tenta ler o CSV sem cabeçalho, assumindo que a primeira linha são dados
        df = pd.read_csv(caminho_arquivo, header=None, decimal=',', sep=';', encoding='utf-8')

        # Se o DataFrame tiver mais colunas do que o esperado, pega apenas as primeiras
        if df.shape[1] > len(COLUNAS_ESPERADAS):
            df = df.iloc[:, :len(COLUNAS_ESPERADAS)]

        # Renomeia as colunas. Se tiver menos colunas, as restantes serão NaN.
        df.columns = COLUNAS_ESPERADAS[:df.shape[1]]

        # Preenche colunas que faltam com NaN para garantir que todas as COLUNAS_ESPERADAS existam
        for col in COLUNAS_ESPERADAS:
            if col not in df.columns:
                df[col] = pd.NA # ou np.nan

        # Converte colunas numéricas, tratando erros
        for col in ["Ambiente", "Entrada", "Saída", "DeltaT", "Tensao", "Corrente",
                    "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo CSV '{os.path.basename(caminho_arquivo)}': {e}")
        # Retorna um DataFrame vazio com as colunas esperadas em caso de erro
        return pd.DataFrame(columns=COLUNAS_ESPERADAS)

@st.cache_data
def listar_arquivos_csv(diretorio="."):
    arquivos_info = []
    # Padrão regex para extrair informações do nome do arquivo
    # Ex: historico_L1_20231026_1030_OP1234_FT567.csv
    # Grupos: [1] Modelo, [2] Ano, [3] Mês, [4] Dia, [5] Hora, [6] Minuto, [7] OP, [8] FT
    padrao_nome_arquivo = re.compile(
        r"historico_(L\d+)_(?P<ano>\d{4})(?P<mes>\d{2})(?P<dia>\d{2})_(?P<hora>\d{2})(?P<minuto>\d{2})_(OP\d+)_(FT\d+)\.csv",
        re.IGNORECASE
    )

    for root, _, files in os.walk(diretorio):
        for nome_arquivo in files:
            if nome_arquivo.endswith(".csv"):
                match = padrao_nome_arquivo.match(nome_arquivo)
                if match:
                    dados = match.groupdict()
                    modelo = match.group(1) # L1, L2, etc.
                    ano = int(dados.get("ano", 0))
                    mes = int(dados.get("mes", 0))
                    dia = int(dados.get("dia", 0))
                    hora_str = dados.get("hora", "00")
                    minuto_str = dados.get("minuto", "00")
                    operacao = dados.get("OP", "N/D")
                    ft = dados.get("FT", "N/D")

                    # Formata a hora de forma segura
                    hora_formatada = f"{hora_str.zfill(2)}:{minuto_str.zfill(2)}"

                    try:
                        data_hora_obj = datetime(ano, mes, dia, int(hora_str), int(minuto_str))
                    except ValueError:
                        data_hora_obj = datetime.min # Valor padrão se a data/hora for inválida

                    arquivos_info.append({
                        "nome_arquivo": nome_arquivo,
                        "caminho": os.path.join(root, nome_arquivo),
                        "modelo": modelo,
                        "ano": ano,
                        "mes": mes,
                        "dia": dia,
                        "hora": hora_formatada,
                        "operacao": operacao,
                        "ft": ft,
                        "data_hora_obj": data_hora_obj,
                    })
                else:
                    # Se o arquivo CSV não seguir o padrão, ainda o lista, mas com N/D
                    arquivos_info.append({
                        "nome_arquivo": nome_arquivo,
                        "caminho": os.path.join(root, nome_arquivo),
                        "modelo": "N/D",
                        "ano": 0, "mes": 0, "dia": 0, "hora": "N/D",
                        "operacao": "N/D", "ft": "N/D",
                        "data_hora_obj": datetime.min,
                    })

    # Ordena os arquivos pelo modelo, ano, mês, dia e hora (mais recente primeiro)
    arquivos_info.sort(key=lambda x: (x["modelo"], x["ano"], x["mes"], x["dia"], x["hora"]), reverse=True)
    return arquivos_info

# --- Inicialização do estado da sessão ---
if "todos_arquivos_info" not in st.session_state:
    st.session_state["todos_arquivos_info"] = listar_arquivos_csv()

todos_arquivos_info = st.session_state["todos_arquivos_info"]

# --- Aba "Dashboard" ---
st.header("Dashboard de Teste de Máquinas Fromtherm")

# Encontra o arquivo mais recente para a última leitura
ultima_leitura_info = None
if todos_arquivos_info:
    # Pega o primeiro arquivo, que já está ordenado como o mais recente
    ultima_leitura_info = todos_arquivos_info[0]

ultima_linha = pd.Series(dtype='object') # Inicializa como Series vazia
if ultima_leitura_info:
    df_ultima_leitura = carregar_csv_caminho(ultima_leitura_info["caminho"])
    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1] # Pega a última linha do DataFrame

# Exibição dos cards de última leitura
st.subheader("Última Leitura")
col1, col2, col3, col4, col5 = st.columns(5)

def display_card(col, title, value, unit, icon_class, color_class=""):
    display_value = f"{value:.2f}" if pd.notna(value) and isinstance(value, (int, float)) else "N/D"
    with col:
        st.markdown(
            f"""
            <div class="ft-card">
                <i class="bi {icon_class} ft-card-icon {color_class}"></i>
                <div class="ft-card-content">
                    <p class="ft-card-title">{title}</p>
                    <p class="ft-card-value">{display_value} {unit}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# Valores para os cards, com tratamento para N/D
get_val = lambda col_name: ultima_linha.get(col_name, pd.NA)

display_card(col1, "T-Ambiente", get_val("Ambiente"), "°C", "bi-thermometer-half")
display_card(col2, "T-Entrada", get_val("Entrada"), "°C", "bi-arrow-down-circle")
display_card(col3, "T-Saída", get_val("Saída"), "°C", "bi-arrow-up-circle", "red")
display_card(col4, "DIF (ΔT)", get_val("DeltaT"), "°C", "bi-arrow-down-up") # Ícone de diferencial
display_card(col5, "Tensão", get_val("Tensao"), "V", "bi-lightning-charge")

col6, col7, col8, col9, col10 = st.columns(5)
display_card(col6, "Corrente", get_val("Corrente"), "A", "bi-lightning")
display_card(col7, "kcal/h", get_val("Kcal_h"), "", "bi-fire")
display_card(col8, "Vazão", get_val("Vazao"), "L/min", "bi-water")
display_card(col9, "kW Aquecimento", get_val("KWAquecimento"), "", "bi-sun")
display_card(col10, "kW Consumo", get_val("KWConsumo"), "", "bi-plug")

st.markdown("---")

# --- Aba "Históricos Disponíveis" ---
st.subheader("Históricos Disponíveis")

if not todos_arquivos_info:
    st.info("Nenhum arquivo CSV de histórico encontrado na pasta.")
else:
    # Cria um DataFrame para exibir os históricos
    df_historicos = pd.DataFrame(todos_arquivos_info)
    df_historicos["Data"] = df_historicos["data_hora_obj"].dt.strftime("%d/%m/%Y %H:%M")
    df_historicos_display = df_historicos[[
        "Data", "modelo", "operacao", "ft", "nome_arquivo"
    ]].rename(columns={
        "modelo": "Modelo",
        "operacao": "OP",
        "ft": "FT",
        "nome_arquivo": "Nome do Arquivo"
    })
    st.dataframe(df_historicos_display, use_container_width=True)

    # Botão para baixar todos os históricos como PDF
    if st.button("Baixar Todos os Históricos como PDF"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Relatório de Todos os Históricos Fromtherm", styles["h1"]))
        elements.append(Spacer(1, 0.5 * cm))

        for _, row in df_historicos.iterrows():
            elements.append(Paragraph(f"<b>Arquivo:</b> {row['nome_arquivo']}", styles["h2"]))
            elements.append(Paragraph(f"<b>Modelo:</b> {row['modelo']} | <b>OP:</b> {row['operacao']} | <b>FT:</b> {row['ft']}", styles["Normal"]))
            elements.append(Paragraph(f"<b>Data/Hora:</b> {row['Data']}", styles["Normal"]))
            elements.append(Spacer(1, 0.2 * cm))

            df_detalhes = carregar_csv_caminho(row["caminho"])
            if not df_detalhes.empty:
                # Prepara os dados para a tabela PDF
                data_table = [df_detalhes.columns.tolist()] + df_detalhes.values.tolist()
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
            else:
                elements.append(Paragraph("<i>Dados não disponíveis para este arquivo.</i>", styles["Normal"]))
            elements.append(Spacer(1, 1 * cm)) # Espaço entre os arquivos

        doc.build(elements)
        st.download_button(
            label="Download PDF Completo",
            data=buffer.getvalue(),
            file_name="relatorio_todos_historicos_fromtherm.pdf",
            mime="application/pdf",
        )

st.markdown("---")

# --- Aba "Gráficos" ---
st.subheader("Visualização de Gráficos")

if not todos_arquivos_info:
    st.info("Nenhum arquivo CSV de histórico encontrado para gerar gráficos.")
else:
    # Filtra apenas arquivos com modelo e ano válidos para os seletores
    arquivos_validos_para_selecao = [a for a in todos_arquivos_info if a["modelo"] != "N/D" and a["ano"] != 0]

    modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in arquivos_validos_para_selecao)))
    anos_disponiveis_graf = sorted(list(set(a["ano"] for a in arquivos_validos_para_selecao)), reverse=True)

    meses_com_label = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    col1_graf, col2_graf, col3_graf, col4_graf = st.columns(4)
    with col1_graf:
        modelo_graf = st.selectbox("Modelo para Gráfico:", modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum Modelo"], key="graf_modelo")
    with col2_graf:
        ano_graf = st.selectbox("Ano para Gráfico:", anos_disponiveis_graf if anos_disponiveis_graf else ["Nenhum Ano"], key="graf_ano")
    with col3_graf:
        # Filtra meses com base no modelo e ano selecionados
        arquivos_por_modelo_ano = [a for a in arquivos_validos_para_selecao if a["modelo"] == modelo_graf and a["ano"] == ano_graf]
        meses_disponiveis_graf_num = sorted(list(set(a["mes"] for a in arquivos_por_modelo_ano if a["mes"] != 0)))
        meses_disponiveis_graf_label = ["Todos"] + [meses_com_label[m] for m in meses_disponiveis_graf_num]

        mes_graf_label = st.selectbox("Mês para Gráfico:", meses_disponiveis_graf_label, key="graf_mes")
        mes_graf = None
        if mes_graf_label != "Todos":
            mes_graf = {v: k for k, v in meses_com_label.items()}[mes_graf_label]

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