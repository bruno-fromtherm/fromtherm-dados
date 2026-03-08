import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm # Importar cm para unidades de medida
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
    /* Esconde o botão de menu que pode conter o "0" */
    button[data-testid="stSidebarNavToggle"] {
        display: none !important;
    }
    /* Outras tentativas genéricas para garantir que nenhum span pequeno e solto apareça */
    div[data-testid="stAppViewContainer"] > div:first-child span {
        font-size: 0px !important;
        color: transparent !important;
    }
    span[data-testid="stDecoration"] {
        display: none !important;
    }
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
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Teste de Máquinas Fromtherm")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# --- Nomes de colunas esperados para os arquivos CSV ---
COLUNAS_ESPERADAS = [
    "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao",
    "Corrente", "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
]

# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_YYYYMMDD_HHMM_OPXXXX_FTYYY.csv
    """
    if not os.path.exists(DADOS_DIR):
        st.warning(f"Diretório de dados não encontrado: {DADOS_DIR}")
        return []

    arquivos_csv = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    todos_arquivos_info = []

    for caminho_arquivo in arquivos_csv:
        nome_arquivo = os.path.basename(caminho_arquivo)
        partes = nome_arquivo.replace(".csv", "").split("_")

        info_arquivo = {
            "nome_arquivo": nome_arquivo,
            "caminho": caminho_arquivo,
            "data": None,
            "hora": None,
            "operacao": "N/D",
            "modelo": "N/D",
            "ano": None,
            "mes": None,
        }

        if len(partes) >= 5:
            try:
                data_str = partes[2]  # YYYYMMDD
                hora_str = partes[3]  # HHMM
                info_arquivo["data"] = datetime.strptime(data_str, "%Y%m%d").date()
                info_arquivo["hora"] = datetime.strptime(hora_str, "%H%M").strftime("%H:%M")
                info_arquivo["ano"] = info_arquivo["data"].year
                info_arquivo["mes"] = info_arquivo["data"].month
            except ValueError:
                # Se a data/hora não puder ser parseada, usa uma data muito antiga para ordenação
                info_arquivo["data"] = datetime.min.date()
                info_arquivo["hora"] "00:00" # Define uma hora padrão
                info_arquivo["ano"] = 1 # Ano padrão para não quebrar
                info_arquivo["mes"] = 1 # Mês padrão para não quebrar

            if len(partes) >= 4 and partes[4].startswith("OP"):
                info_arquivo["operacao"] = partes[4]
            if len(partes) >= 5 and partes[5].startswith("FT"):
                info_arquivo["modelo"] = partes[5]

        todos_arquivos_info.append(info_arquivo)

    # Ordena do mais recente para o mais antigo
    todos_arquivos_info.sort(key=lambda x: (x["data"], x["hora"]), reverse=True)
    return todos_arquivos_info

# --- Função para carregar um arquivo CSV específico e renomear colunas ---
@st.cache_data(ttl=10)
def carregar_csv_caminho(caminho_arquivo):
    try:
        # Tenta ler o CSV sem cabeçalho, assumindo que a primeira linha são dados
        df = pd.read_csv(caminho_arquivo, header=None)

        # Verifica se o número de colunas lidas é o esperado
        if df.shape[1] < len(COLUNAS_ESPERADAS):
            st.warning(f"O arquivo {os.path.basename(caminho_arquivo)} tem menos colunas do que o esperado. Preenchendo com NaN.")
            # Adiciona colunas vazias para corresponder ao número esperado
            for i in range(df.shape[1], len(COLUNAS_ESPERADAS)):
                df[i] = pd.NA # ou np.nan

        # Renomeia as colunas
        df.columns = COLUNAS_ESPERADAS[:df.shape[1]] # Renomeia apenas as colunas existentes

        # Se o arquivo tiver mais colunas do que o esperado, as colunas extras manterão os nomes numéricos
        # Isso é um trade-off para evitar erros, mas pode ser ajustado se houver um padrão para colunas extras

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV {os.path.basename(caminho_arquivo)}: {e}")
        return pd.DataFrame(columns=COLUNAS_ESPERADAS) # Retorna um DataFrame vazio com as colunas esperadas

# --- Carrega todos os arquivos de histórico ---
todos_arquivos_info = listar_arquivos_csv()

# --- Determinar o arquivo mais recente (por data + hora) ---
arquivo_mais_recente = None
if todos_arquivos_info:
    # Como já ordenamos, o primeiro é o mais recente
    arquivo_mais_recente = todos_arquivos_info[0]

# --- Carrega os dados da última leitura ---
ultima_linha = None
if arquivo_mais_recente:
    df_dados = carregar_csv_caminho(arquivo_mais_recente["caminho"])
    if not df_dados.empty:
        ultima_linha = df_dados.iloc[-1] # Pega a última linha do DataFrame

# --- Painel da Última Leitura Registrada ---
st.markdown("## Última Leitura Registrada")

if ultima_linha is not None:
    st.markdown(
        f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
        f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
        f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | "
        f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
    )

    st.markdown("---")

    # Layout em 3 colunas para os cards
    col1, col2, col3 = st.columns(3)

    # Função auxiliar para criar um card
    def criar_card(col, titulo, valor, icone, is_red=False):
        with col:
            st.markdown(
                f"""
                <div class="ft-card" style="border-left: 4px solid {'#dc3545' if is_red else '#0d6efd'};">
                    <i class="bi {icone} ft-card-icon {'red' if is_red else ''}"></i>
                    <div class="ft-card-content">
                        <p class="ft-card-title">{titulo}</p>
                        <p class="ft-card-value">{valor}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Cards de Temperatura
    criar_card(col1, "T-Ambiente", f"{ultima_linha.get('Ambiente', 'N/D')} °C", "bi-thermometer-half")
    criar_card(col2, "T-Entrada", f"{ultima_linha.get('Entrada', 'N/D')} °C", "bi-arrow-down-circle")
    criar_card(col3, "T-Saída", f"{ultima_linha.get('Saída', 'N/D')} °C", "bi-arrow-up-circle", is_red=True)

    col4, col5, col6 = st.columns(3)
    criar_card(col1, "ΔT", f"{ultima_linha.get('DeltaT', 'N/D')} °C", "bi-arrow-down-up") # Ícone para diferencial
    criar_card(col2, "Tensão", f"{ultima_linha.get('Tensao', 'N/D')} V", "bi-lightning-charge")
    criar_card(col3, "Corrente", f"{ultima_linha.get('Corrente', 'N/D')} A", "bi-plug")

    col7, col8, col9 = st.columns(3)
    criar_card(col1, "kcal/h", f"{ultima_linha.get('Kcal_h', 'N/D')}", "bi-fire")
    criar_card(col2, "Vazão", f"{ultima_linha.get('Vazao', 'N/D')} L/min", "bi-droplet")
    criar_card(col3, "kW Aquecimento", f"{ultima_linha.get('KWAquecimento', 'N/D')} kW", "bi-sun")

    col10, col11, col12 = st.columns(3)
    criar_card(col1, "kW Consumo", f"{ultima_linha.get('KWConsumo', 'N/D')} kW", "bi-power")
    criar_card(col2, "COP", f"{ultima_linha.get('COP', 'N/D')}", "bi-award")

else:
    st.info("Nenhum dado de leitura recente encontrado. Verifique a pasta de dados.")

st.markdown("---")

# --- Abas para Históricos e Gráficos ---
tab1, tab2 = st.tabs(["Históricos e Downloads", "Crie Seu Gráfico"])

with tab1:
    st.markdown("## Históricos e Downloads")

    # Garante que as listas de opções não estejam vazias antes de passar para st.selectbox
    modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])))
    meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
    ops_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))

    # Adiciona um placeholder se as listas estiverem vazias
    modelos_opcoes = modelos_disponiveis if modelos_disponiveis else ["Nenhum Modelo disponível"]
    anos_opcoes = sorted(anos_disponiveis, reverse=True) if anos_disponiveis else ["Nenhum Ano disponível"]
    meses_opcoes_label = ["Todos"] + [f"{m:02d} - {datetime(1, m, 1).strftime('%B')}" for m in meses_disponiveis] if meses_disponiveis else ["Nenhum Mês disponível"]
    ops_opcoes = ops_disponiveis if ops_disponiveis else ["Nenhuma OP disponível"]

    col_hist1, col_hist2, col_hist3 = st.columns(3)
    with col_hist1:
        modelo_selecionado = st.selectbox(
            "Modelo:",
            modelos_opcoes,
            key="hist_modelo",
        )
    with col_hist2:
        ano_selecionado = st.selectbox(
            "Ano:",
            anos_opcoes,
            key="hist_ano",
        )
    with col_hist3:
        mes_selecionado_label = st.selectbox(
            "Mês:",
            meses_opcoes_label,
            key="hist_mes",
        )
        mes_selecionado = None
        if mes_selecionado_label != "Todos" and "Nenhum Mês disponível" not in mes_selecionado_label:
            mes_selecionado = int(mes_selecionado_label.split(" ")[0])

    op_selecionada = st.selectbox(
        "Operação (OP):",
        ops_opcoes,
        key="hist_op",
    )

    st.markdown("---")

    arquivos_filtrados = []
    # Só filtra se houver modelos disponíveis e as seleções não forem placeholders
    if todos_arquivos_info and modelo_selecionado != "Nenhum Modelo disponível" and ano_selecionado != "Nenhum Ano disponível" and op_selecionada != "Nenhuma OP disponível":
        for arquivo in todos_arquivos_info:
            if (
                arquivo["modelo"] == modelo_selecionado
                and arquivo["ano"] == ano_selecionado
                and (mes_selecionado is None or arquivo["mes"] == mes_selecionado)
                and arquivo["operacao"] == op_selecionada
            ):
                arquivos_filtrados.append(arquivo)

    if not arquivos_filtrados:
        st.info("Nenhum arquivo encontrado para os filtros selecionados.")
    else:
        st.markdown(f"**{len(arquivos_filtrados)}** arquivo(s) encontrado(s).")
        for arquivo in arquivos_filtrados:
            st.markdown(f"**Arquivo:** {arquivo['nome_arquivo']} | **Data:** {arquivo['data'].strftime('%d/%m/%Y')} | **Hora:** {arquivo['hora']}")

            col_dl1, col_dl2, col_dl3 = st.columns([0.2, 0.2, 0.6])
            with col_dl1:
                # Botão de download CSV
                try:
                    with open(arquivo["caminho"], "rb") as f:
                        st.download_button(
                            label="Baixar CSV",
                            data=f.read(),
                            file_name=arquivo["nome_arquivo"],
                            mime="text/csv",
                            key=f"dl_csv_{arquivo['nome_arquivo']}",
                        )
                except FileNotFoundError:
                    st.error(f"Arquivo CSV não encontrado: {arquivo['nome_arquivo']}")
                except Exception as e:
                    st.error(f"Erro ao ler CSV para download: {e}")

            with col_dl2:
                # Botão de download PDF
                if st.button("Gerar PDF", key=f"btn_pdf_{arquivo['nome_arquivo']}"):
                    df_exibir = carregar_csv_caminho(arquivo["caminho"])
                    if not df_exibir.empty:
                        buffer = BytesIO()
                        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=cm, leftMargin=cm, topMargin=cm, bottomMargin=cm)
                        styles = getSampleStyleSheet()
                        styles.add(ParagraphStyle(name='Centered', alignment=1)) # 1 para CENTER

                        elements = []
                        elements.append(Paragraph(f"Relatório de Teste - Fromtherm", styles["h1"]))
                        elements.append(Spacer(1, 0.5 * cm))
                        elements.append(Paragraph(f"Modelo: {arquivo['modelo']} OP: {arquivo['operacao']}", styles["h3"]))
                        elements.append(Paragraph(f"Data: {arquivo['data'].strftime('%d/%m/%Y')} Hora: {arquivo['hora']}", styles["h3"]))
                        elements.append(Spacer(1, 0.5 * cm))

                        # Tabela de dados
                        # Converte o DataFrame para uma lista de listas para a tabela do ReportLab
                        data_table = [df_exibir.columns.tolist()] + df_exibir.values.tolist()
                        table = Table(data_table)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(table)

                        doc.build(elements)
                        pdf_data = buffer.getvalue()
                        buffer.close()

                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_data,
                            file_name=f"{arquivo['nome_arquivo'].replace('.csv', '.pdf')}",
                            mime="application/pdf",
                            key=f"dl_pdf_{arquivo['nome_arquivo']}",
                        )
                    else:
                        st.error("Não foi possível carregar os dados para exibição ou download.")

with tab2:
    st.markdown("## Crie Seu Gráfico Personalizado")

    # Garante que as listas de opções não estejam vazias antes de passar para st.selectbox
    modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    anos_disponiveis_graf = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])))
    meses_disponiveis_graf = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
    ops_disponiveis_graf = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))

    # Adiciona um placeholder se as listas estiverem vazias
    modelos_opcoes = modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum Modelo disponível"]
    anos_opcoes = sorted(anos_disponiveis_graf, reverse=True) if anos_disponiveis_graf else ["Nenhum Ano disponível"]
    meses_opcoes_label = ["Todos"] + [f"{m:02d} - {datetime(1, m, 1).strftime('%B')}" for m in meses_disponiveis_graf] if meses_disponiveis_graf else ["Nenhum Mês disponível"]
    ops_opcoes = ops_disponiveis_graf if ops_disponiveis_graf else ["Nenhuma OP disponível"]

    col_graf1, col_graf2, col_graf3 = st.columns(3)
    with col_graf1:
        modelo_graf = st.selectbox(
            "Modelo:",
            modelos_opcoes,
            key="graf_modelo",
        )
    with col_graf2:
        ano_graf = st.selectbox(
            "Ano:",
            anos_opcoes,
            key="graf_ano",
        )
    with col_graf3:
        mes_graf_label = st.selectbox(
            "Mês:",
            meses_opcoes_label,
            key="graf_mes",
        )
        mes_graf = None
        if mes_graf_label != "Todos" and "Nenhum Mês disponível" not in mes_graf_label:
            mes_graf = int(mes_graf_label.split(" ")[0])

    default_op_index = 0
    if ops_disponiveis_graf and len(ops_disponiveis_graf) == 1:
        default_op_index = 0
    elif not ops_disponiveis_graf:
        default_op_index = 0 # Mantém 0 para a opção "Nenhuma OP disponível"

    op_graf = st.selectbox(
        "Operação (OP):",
        ops_opcoes,
        index=default_op_index,
        key="graf_op",
    )

    arquivo_escolhido = None
    # Só tenta encontrar o arquivo se houver modelos disponíveis e as seleções não forem placeholders
    if modelos_disponiveis_graf and modelo_graf != "Nenhum Modelo disponível" and ano_graf != "Nenhum Ano disponível" and op_graf != "Nenhuma OP disponível":
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

            # Converte 'Date' e 'Time' para um único campo 'DateTime'
            # Garante que 'Date' e 'Time' são strings antes de concatenar
            df_graf["DateTime"] = pd.to_datetime(
                df_graf["Date"].astype(str) + " " + df_graf["Time"].astype(str),
                errors="coerce", # Coerce erros para NaT (Not a Time)
            )
            # Remove linhas onde DateTime não pôde ser convertido
            df_graf.dropna(subset=["DateTime"], inplace=True)

            st.markdown("### Variáveis para o gráfico")

            # Usa os nomes padronizados das colunas para as opções de variáveis
            variaveis_opcoes = [
                "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao",
                "Corrente", "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
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