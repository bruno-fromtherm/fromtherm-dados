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
#  CSS GLOBAL (fundo + correção do "0" + cards)
# =========================
st.markdown(
    """
    <style>
    /* Fundo geral da página (tom próximo ao site Fromtherm) */
    .stApp {
        background-color: #f4f6f9;
    }

    /* Container principal - deixa conteúdo sobre "cartão branco" */
    .main > div {
        background-color: #ffffff;
        padding: 10px 25px 40px 25px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-top: 5px;
    }

    /* Título principal */
    h1 {
        color: #003366 !important;  /* azul escuro Fromtherm */
        font-weight: 800 !important;
        letter-spacing: 0.02em;
    }

    /* Linha abaixo do título */
    h1 + div {
        border-bottom: 1px solid #dde2eb;
        margin-bottom: 8px;
        padding-bottom: 4px;
    }

    /* Sidebar com leve separação */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #dde2eb;
    }

    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva) */
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
arquivo_mais_recente = max(
    todos_arquivos_info,
    key=lambda x: (
        x["data"] if x["data"] else datetime.min.date(),
        x["hora"] or "",
    ),
)

# =====================================================
#  PAINEL: Última leitura registrada (cards com ícones)
# =====================================================
st.markdown("### Última Leitura Registrada")

# Informações do teste mais recente
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.markdown(f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'}")
with col_info2:
    st.markdown(f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'}")
with col_info3:
    data_formatada = (
        arquivo_mais_recente["data"].strftime("%d/%m/%Y")
        if arquivo_mais_recente["data"]
        else "N/D"
    )
    st.markdown(f"**Data:** {data_formatada} **Hora:** {arquivo_mais_recente['hora'] or 'N/D'}")

st.markdown("---") # Separador visual

try:
    df_ultimo = carregar_csv_caminho(arquivo_mais_recente["caminho"]).copy()
    # Assegura que a última linha seja a mais recente
    ultima_linha = df_ultimo.iloc[-1]

    # Mapeamento de colunas para nomes de exibição e ícones
    metricas = {
        "Ambiente": {"label": "T-Ambiente (°C)", "icon": "bi-thermometer-half"},
        "Entrada": {"label": "T-Entrada (°C)", "icon": "bi-arrow-down-circle"},
        "Saída": {"label": "T-Saída (°C)", "icon": "bi-arrow-up-circle", "color_class": "red"},
        "ΔT": {"label": "DIF (ΔT) (°C)", "icon": "bi-arrow-down-up"}, # Novo ícone para diferencial
        "Tensão": {"label": "Tensão (V)", "icon": "bi-lightning-charge"},
        "Corrente": {"label": "Corrente (A)", "icon": "bi-lightning"},
        "kcal/h": {"label": "kcal/h", "icon": "bi-fire"},
        "Vazão": {"label": "Vazão", "icon": "bi-droplet"},
        "kW Aquecimento": {"label": "kW Aquecimento", "icon": "bi-sun"},
        "kW Consumo": {"label": "kW Consumo", "icon": "bi-plug"},
        "COP": {"label": "COP", "icon": "bi-speedometer2"},
    }

    # Exibir métricas em 3 colunas
    cols = st.columns(3)
    for i, (col_name, info) in enumerate(metricas.items()):
        with cols[i % 3]:
            valor = ultima_linha.get(col_name, "N/D")
            # Formata valores numéricos para 2 casas decimais, se forem números
            if isinstance(valor, (int, float)):
                valor = f"{valor:.2f}"

            icon_class = info.get("color_class", "")
            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi {info['icon']} ft-card-icon {icon_class}"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">{info['label']}</p>
                    <p class="ft-card-value">{valor}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

except Exception as e:
    st.error(f"Não foi possível gerar o painel da última leitura: {e}")
    st.info("Verifique se o formato do CSV está conforme o padrão esperado.")


# =========================
#  TABS: Históricos e Gráficos
# =========================
tab_hist, tab_graf = st.tabs(["📄 Históricos e Planilhas", "📊 Crie Seu Gráfico"])

# Mapeamento de meses para labels
mes_label_map = {
    1: "01 - Jan", 2: "02 - Fev", 3: "03 - Mar", 4: "04 - Abr",
    5: "05 - Mai", 6: "06 - Jun", 7: "07 - Jul", 8: "08 - Ago",
    9: "09 - Set", 10: "10 - Out", 11: "11 - Nov", 12: "12 - Dez",
}

# =========================
#  TAB 1 - HISTÓRICOS E PLANILHAS
# =========================
with tab_hist:
    st.subheader("Históricos Disponíveis")

    # --- Filtros na barra lateral ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtros de Histórico")

    modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    modelo_filtro = st.sidebar.selectbox(
        "Modelo:",
        ["Todos"] + modelos_disponiveis,
        key="hist_modelo",
    )

    anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])))
    ano_filtro = st.sidebar.selectbox(
        "Ano:",
        ["Todos"] + anos_disponiveis,
        key="hist_ano",
    )

    meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
    meses_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis]
    mes_filtro_label = st.sidebar.selectbox(
        "Mês:",
        meses_labels,
        key="hist_mes",
    )
    mes_filtro = None
    if mes_filtro_label != "Todos":
        mes_filtro = int(mes_filtro_label.split(" ")[0])

    datas_disponiveis = sorted(list(set(a["data"] for a in todos_arquivos_info if a["data"])))
    data_filtro = st.sidebar.selectbox(
        "Data:",
        ["Todas"] + datas_disponiveis,
        format_func=lambda x: "Todas" if x == "Todas" else x.strftime("%d/%m/%Y"),
        key="hist_data",
    )

    ops_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))
    op_filtro = st.sidebar.selectbox(
        "Operação (OP):",
        ["Todas"] + ops_disponiveis,
        key="hist_op",
    )

    # --- Aplicar filtros ---
    arquivos_filtrados = [
        a
        for a in todos_arquivos_info
        if (modelo_filtro == "Todos" or a["modelo"] == modelo_filtro)
        and (ano_filtro == "Todos" or a["ano"] == ano_filtro)
        and (mes_filtro is None or a["mes"] == mes_filtro)
        and (data_filtro == "Todas" or a["data"] == data_filtro)
        and (op_filtro == "Todas" or a["operacao"] == op_filtro)
    ]

    if not arquivos_filtrados:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for i, arquivo in enumerate(arquivos_filtrados):
            data_nome = arquivo["data"].strftime("%d-%m-%Y") if arquivo["data"] else "N_D"
            hora_nome = arquivo["hora"].replace(":", "-") if arquivo["hora"] else "N_D"

            st.markdown(
                f"**{i+1}. Modelo:** {arquivo['modelo'] or 'N/D'} | **OP:** {arquivo['operacao'] or 'N/D'} | **Data:** {data_nome} | **Hora:** {arquivo['hora'] or 'N/D'}"
            )
            st.markdown(f"Arquivo: `{arquivo['nome_arquivo']}`")

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                try:
                    df_dados = carregar_csv_caminho(arquivo["caminho"])

                    output_excel = BytesIO()
                    with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                        df_dados.to_excel(writer, index=False, sheet_name="Dados")
                        workbook = writer.book
                        worksheet = writer.sheets["Dados"]

                        title_format = workbook.add_format(
                            {
                                "bold": True,
                                "font_size": 16,
                                "align": "center",
                                "valign": "vcenter",
                                "bg_color": "#DDEBF7",
                                "border": 1,
                            }
                        )
                        header_info_label = workbook.add_format(
                            {"bold": True, "bg_color": "#F2F2F2", "border": 1}
                        )
                        header_info_value = workbook.add_format({"border": 1})
                        header_data_format = workbook.add_format(
                            {"bold": True, "bg_color": "#DDEBF7", "border": 1}
                        )
                        cell_data_format = workbook.add_format({"border": 1})

                        col_count = len(df_dados.columns)
                        last_col_letter = chr(ord("A") + col_count - 1)
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

                    # A função criar_pdf_paisagem não está definida neste código.
                    # Se você quiser o download de PDF, precisará adicionar a definição dessa função.
                    # Por enquanto, o botão de PDF está comentado para evitar erros.
                    # pdf_buffer = BytesIO()
                    # pdf_buffer = criar_pdf_paisagem(df_dados, arquivo) # Descomente e defina esta função
                    # st.download_button(
                    #     label="Exportar para PDF",
                    #     data=pdf_buffer,
                    #     file_name=(
                    #         f"Maquina_{arquivo['modelo'] or 'N_D'}_"
                    #         f"{arquivo['operacao'] or 'OP'}_"
                    #         f"{data_nome}_{hora_nome}.pdf"
                    #     ),
                    #     mime="application/pdf",
                    #     key=f"pdf_download_{i}",
                    # )

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