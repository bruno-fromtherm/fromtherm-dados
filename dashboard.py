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
#  CSS e JavaScript GLOBAL (remoção do "0" e estilo dos cards)
# =========================
st.markdown(
    """
    <style>
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
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    </style>

    <script>
    // JavaScript para remover o "0" teimoso no canto superior esquerdo
    // Ele procura pelo botão de menu do Streamlit e o esconde.
    // Executa após a página carregar para garantir que o elemento exista.
    function removeStreamlitMenuButton() {
        const button = document.querySelector('button[data-testid="stSidebarNavToggle"]');
        if (button) {
            button.style.display = 'none';
        }
    }
    // Tenta remover imediatamente e também após um pequeno atraso, caso o elemento ainda não esteja no DOM
    removeStreamlitMenuButton();
    setTimeout(removeStreamlitMenuButton, 500); // Tenta novamente após 0.5 segundo
    </script>
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Teste de Máquinas Fromtherm") # Título principal ajustado

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# Nomes de colunas esperados para os DataFrames
COLUNAS_ESPERADAS = [
    "Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão",
    "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"
]

# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_20260303_2140_OP1234_FT185.csv
    Se a data não puder ser parseada, usa datetime.min.date() para ordenação.
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        linha = ""
        data = datetime.min.date() # Valor padrão para garantir que não seja None
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
            # Se houver erro ao parsear, data já é datetime.min.date()
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


# --- Função para carregar um CSV (ponto e vírgula ou vírgula) e renomear colunas ---
def carregar_csv_caminho(caminho: str) -> pd.DataFrame:
    df = pd.DataFrame()
    try:
        df = pd.read_csv(caminho, sep=";", engine="python")
    except Exception:
        try:
            df = pd.read_csv(caminho, sep=",", engine="python")
        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV '{os.path.basename(caminho)}': {e}")
            return pd.DataFrame(columns=COLUNAS_ESPERADAS) # Retorna DataFrame vazio com colunas esperadas

    # Garante que o DataFrame tenha as colunas esperadas, mesmo que o CSV não as tenha
    # ou tenha um número diferente de colunas.
    if len(df.columns) == len(COLUNAS_ESPERADAS):
        df.columns = COLUNAS_ESPERADAS
    else:
        # Se o número de colunas não bater, tenta mapear as primeiras colunas
        # ou preenche com NaN e avisa.
        st.warning(f"O arquivo '{os.path.basename(caminho)}' tem {len(df.columns)} colunas, mas {len(COLUNAS_ESPERADAS)} eram esperadas. Tentando ajustar.")
        new_df = pd.DataFrame(columns=COLUNAS_ESPERADAS)
        for i, col_name in enumerate(COLUNAS_ESPERADAS):
            if i < len(df.columns):
                new_df[col_name] = df.iloc[:, i]
        df = new_df.copy() # Usa o DataFrame ajustado

    return df


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo .csv de histórico encontrado na pasta '{DADOS_DIR}'.")
    st.info("Verifique se os arquivos .csv foram sincronizados corretamente para o GitHub.")
    st.stop()

# --- Determinar o arquivo mais recente (por data + hora) ---
# A função listar_arquivos_csv já garante que 'data' não é None
arquivo_mais_recente = max(
    todos_arquivos_info,
    key=lambda x: (x["data"], x["hora"] or ""), # Garante que hora vazia não cause erro
)

# =====================================================
#  ABA 1: Históricos e Planilhas
# =====================================================
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("## Última Leitura Registrada")

    # Carrega o DataFrame do arquivo mais recente
    df_mais_recente = carregar_csv_caminho(arquivo_mais_recente["caminho"])

    if not df_mais_recente.empty:
        ultima_linha = df_mais_recente.iloc[-1] # Pega a última linha do DataFrame

        st.markdown(
            f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
            f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
            f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | "
            f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
        )

        st.markdown("---")

        # Mapeamento de métricas para ícones e classes CSS
        metricas_info = {
            "Ambiente": {"icone": "bi-thermometer-half", "unidade": "°C", "classe": ""},
            "Entrada": {"icone": "bi-arrow-down-circle", "unidade": "°C", "classe": ""},
            "Saída": {"icone": "bi-arrow-up-circle", "unidade": "°C", "classe": "red"},
            "ΔT": {"icone": "bi-arrow-down-up", "unidade": "°C", "classe": ""}, # Novo ícone para diferencial
            "Tensão": {"icone": "bi-lightning-charge", "unidade": "V", "classe": ""},
            "Corrente": {"icone": "bi-lightning", "unidade": "A", "classe": ""},
            "kcal/h": {"icone": "bi-fire", "unidade": "", "classe": ""},
            "Vazão": {"icone": "bi-droplet", "unidade": "", "classe": ""},
            "kW Aquecimento": {"icone": "bi-thermometer-sun", "unidade": "kW", "classe": ""},
            "kW Consumo": {"icone": "bi-power", "unidade": "kW", "classe": ""},
            "COP": {"icone": "bi-graph-up", "unidade": "", "classe": ""},
        }

        # Cria as colunas para os cards
        cols = st.columns(3) # 3 colunas para os cards

        for i, (metrica, info) in enumerate(metricas_info.items()):
            with cols[i % 3]: # Distribui os cards nas 3 colunas
                valor = ultima_linha.get(metrica, "N/D") # Usa .get para evitar KeyError se a coluna não existir
                if pd.isna(valor): # Verifica se o valor é NaN (Not a Number)
                    valor = "N/D"
                else:
                    try:
                        valor = f"{float(valor):.2f}" # Formata para 2 casas decimais
                    except ValueError:
                        pass # Mantém como está se não for número

                st.markdown(
                    f"""
                    <div class="ft-card">
                        <i class="bi {info['icone']} ft-card-icon {info['classe']}"></i>
                        <div class="ft-card-content">
                            <p class="ft-card-title">{metrica} {info['unidade']}</p>
                            <p class="ft-card-value">{valor}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("O arquivo de histórico mais recente está vazio ou não pôde ser lido.")

    st.markdown("---")
    st.markdown("## Históricos Disponíveis")

    # --- Filtros para a lista de históricos ---
    modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    modelos_disponiveis_com_todos = ["Todos"] + modelos_disponiveis

    modelo_selecionado = st.selectbox(
        "Filtrar por Modelo:",
        modelos_disponiveis_com_todos,
        key="filtro_modelo",
    )

    arquivos_filtrados_modelo = [
        a
        for a in todos_arquivos_info
        if modelo_selecionado == "Todos" or a["modelo"] == modelo_selecionado
    ]

    anos_disponiveis = sorted(list(set(a["ano"] for a in arquivos_filtrados_modelo if a["ano"])), reverse=True)
    anos_disponiveis_com_todos = ["Todos"] + anos_disponiveis

    ano_selecionado = st.selectbox(
        "Filtrar por Ano:",
        anos_disponiveis_com_todos,
        key="filtro_ano",
    )

    arquivos_filtrados_ano = [
        a
        for a in arquivos_filtrados_modelo
        if ano_selecionado == "Todos" or a["ano"] == ano_selecionado
    ]

    mes_label_map = {
        1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
        5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
        9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
    }
    meses_disponiveis = sorted(list(set(a["mes"] for a in arquivos_filtrados_ano if a["mes"])))
    meses_disponiveis_com_todos = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis] if meses_disponiveis else ["Todos"]

    mes_selecionado_label = st.selectbox(
        "Filtrar por Mês:",
        meses_disponiveis_com_todos,
        key="filtro_mes",
    )
    mes_selecionado = None
    if mes_selecionado_label != "Todos":
        mes_selecionado = int(mes_selecionado_label.split(" ")[0])

    arquivos_filtrados_mes = [
        a
        for a in arquivos_filtrados_ano
        if mes_selecionado is None or a["mes"] == mes_selecionado
    ]

    data_especifica_str = st.text_input(
        "Data específica (opcional - YYYY/MM/DD):",
        placeholder="Ex: 2026/03/08",
        key="filtro_data_especifica",
    )
    data_especifica = None
    if data_especifica_str:
        try:
            data_especifica = datetime.strptime(data_especifica_str, "%Y/%m/%d").date()
        except ValueError:
            st.error("Formato de data inválido. Use YYYY/MM/DD.")

    arquivos_filtrados_data = [
        a
        for a in arquivos_filtrados_mes
        if data_especifica is None or a["data"] == data_especifica
    ]

    ops_disponiveis = sorted(list(set(a["operacao"] for a in arquivos_filtrados_data if a["operacao"])))
    ops_disponiveis_com_todas = ["Todas"] + ops_disponiveis

    op_selecionada = st.selectbox(
        "Filtrar por Operação (OP):",
        ops_disponiveis_com_todas,
        key="filtro_op",
    )

    arquivos_finais = [
        a
        for a in arquivos_filtrados_data
        if op_selecionada == "Todas" or a["operacao"] == op_selecionada
    ]

    # Ordenar os arquivos finais pelo nome do arquivo (que contém data e hora)
    arquivos_finais = sorted(arquivos_finais, key=lambda x: x["nome_arquivo"], reverse=True)

    if not arquivos_finais:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        for arquivo in arquivos_finais:
            expander_title = (
                f"**{arquivo['modelo']}** - Linha: {arquivo['linha']} - "
                f"Data: {arquivo['data'].strftime('%d/%m/%Y')} - "
                f"Hora: {arquivo['hora']} - Operação: {arquivo['operacao']}"
            )
            with st.expander(expander_title):
                df_exibir = carregar_csv_caminho(arquivo["caminho"])
                st.dataframe(df_exibir, use_container_width=True)

                # Botão de download para o arquivo CSV
                csv_data = df_exibir.to_csv(index=False, sep=";").encode("utf-8")
                st.download_button(
                    label="Baixar CSV",
                    data=csv_data,
                    file_name=f"{arquivo['nome_arquivo']}",
                    mime="text/csv",
                    key=f"download_csv_{arquivo['nome_arquivo']}",
                )

                # Botão de download para PDF
                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                styles = getSampleStyleSheet()
                style_normal = styles["Normal"]
                style_heading = styles["h2"]
                style_heading.alignment = 1 # Center

                story = []
                story.append(Paragraph(f"Relatório de Dados - {arquivo['nome_arquivo']}", style_heading))
                story.append(Spacer(1, 0.2 * inch))

                # Preparar dados para a tabela PDF
                data_for_pdf = [df_exibir.columns.tolist()] + df_exibir.values.tolist()
                table = Table(data_for_pdf)

                # Estilo da tabela
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")), # Cabeçalho azul Fromtherm
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                doc.build(story)

                st.download_button(
                    label="Baixar PDF",
                    data=pdf_buffer.getvalue(),
                    file_name=f"{arquivo['nome_arquivo'].replace('.csv', '.pdf')}",
                    mime="application/pdf",
                    key=f"download_pdf_{arquivo['nome_arquivo']}",
                )

# =====================================================
#  ABA 2: Crie Seu Gráfico
# =====================================================
with tab2:
    st.markdown("## Crie Seu Gráfico Personalizado")

    modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
    if not modelos_disponiveis_graf:
        st.info("Nenhum modelo disponível para criar gráficos.")
        st.stop()

    modelo_graf = st.selectbox(
        "Modelo:",
        modelos_disponiveis_graf,
        key="graf_modelo",
    )

    arquivos_por_modelo = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf]

    anos_disponiveis_graf = sorted(list(set(a["ano"] for a in arquivos_por_modelo if a["ano"])), reverse=True)
    if not anos_disponiveis_graf:
        st.info("Nenhum ano disponível para este modelo.")
        st.stop()

    ano_graf = st.selectbox(
        "Ano:",
        anos_disponiveis_graf,
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

            # As colunas já são definidas dentro de carregar_csv_caminho
            # df_graf.columns = COLUNAS_ESPERADAS # Esta linha não é mais necessária aqui

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