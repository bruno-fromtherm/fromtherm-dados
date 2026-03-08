import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm # Importar cm para espaçamento
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
st.title("Teste de Máquinas Fromtherm") # Título principal do dashboard

# --- Pasta onde ficam os arquivos de histórico ---
# No Streamlit Cloud, o diretório de trabalho é o root do repositório.
# Então, o caminho deve ser relativo a esse root.
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# --- Colunas esperadas e seus nomes padronizados ---
COLUNAS_ESPERADAS = [
    "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao",
    "Corrente", "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
]
# Mapeamento de nomes de colunas do CSV para nomes padronizados
# Adicione aqui variações que você sabe que podem aparecer nos seus CSVs
COLUNA_MAP = {
    "Date": "Date", "Time": "Time", "Ambiente": "Ambiente", "Entrada": "Entrada",
    "Saída": "Saída", "ΔT": "DeltaT", "Tensão": "Tensao", "Corrente": "Corrente",
    "kcal/h": "Kcal_h", "Vazão": "Vazao", "kW Aquecimento": "KWAquecimento",
    "kW Consumo": "KWConsumo", "COP": "COP"
}


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_20260303_2140_OP1234_FT185.csv
    """
    if not os.path.exists(DADOS_DIR):
        st.warning(f"Diretório de dados não encontrado: {DADOS_DIR}. Certifique-se de que a estrutura de pastas está correta no repositório.")
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

        # Exemplo: historico_L1_20260303_2140_OP1234_FT185.csv
        partes = nome.replace(".csv", "").split("_")
        if len(partes) >= 6:
            linha = partes[1]
            try:
                data_str = partes[2]
                hora_str = partes[3]
                data = datetime.strptime(data_str, "%Y%m%d").date()
                ano = data.year
                mes = data.month
                hora = hora_str[:2] + ":" + hora_str[2:]
            except ValueError:
                data = datetime.min.date() # Em caso de erro, usa data mínima
            operacao = partes[4]
            modelo = partes[5]
        elif len(partes) >= 2: # Caso o nome seja mais simples, tenta pegar o modelo
            modelo = partes[1]

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


# --- Função para carregar um CSV específico e padronizar colunas ---
@st.cache_data(ttl=600)
def carregar_csv_caminho(caminho_arquivo):
    try:
        df = pd.read_csv(caminho_arquivo, sep=";", decimal=",", encoding="utf-8")

        # Renomear colunas usando o mapeamento para padronizar
        # Cria um dicionário de renomeação apenas para as colunas que existem no df
        rename_dict = {k: v for k, v in COLUNA_MAP.items() if k in df.columns}
        df.rename(columns=rename_dict, inplace=True)

        # Garantir que todas as COLUNAS_ESPERADAS existam, adicionando NaN se faltarem
        for col in COLUNAS_ESPERADAS:
            if col not in df.columns:
                df[col] = pd.NA # Adiciona a coluna com valores nulos

        # Reordenar as colunas para seguir a ordem padrão
        df = df[COLUNAS_ESPERADAS]

        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro


# --- Carregar todos os arquivos de histórico ---
todos_arquivos_info = listar_arquivos_csv()

# --- Painel da Última Leitura Registrada ---
st.markdown("## Última Leitura Registrada")

if not todos_arquivos_info:
    st.info("Nenhum arquivo de histórico encontrado na pasta de dados.")
else:
    # Determinar o arquivo mais recente (por data + hora)
    arquivo_mais_recente = max(
        todos_arquivos_info, key=lambda x: (x["data"], x["hora"])
    )

    st.markdown(
        f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
        f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
        f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | "
        f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
    )

    # Carregar os dados do arquivo mais recente
    df_dados = carregar_csv_caminho(arquivo_mais_recente["caminho"])

    if not df_dados.empty:
        ultima_linha = df_dados.iloc[-1]

        # Mapeamento de variáveis para ícones e títulos (usando os nomes padronizados)
        cards_info = [
            {"var": "Ambiente", "title": "T-Ambiente", "icon": "bi-thermometer-half"},
            {"var": "Entrada", "title": "T-Entrada", "icon": "bi-arrow-down-circle"},
            {"var": "Saída", "title": "T-Saída", "icon": "bi-arrow-up-circle", "class": "red"}, # T-Saída vermelho
            {"var": "DeltaT", "title": "DIF (ΔT)", "icon": "bi-arrow-down-up"}, # Novo ícone para DIF
            {"var": "Tensao", "title": "Tensão", "icon": "bi-lightning-charge"},
            {"var": "Corrente", "title": "Corrente", "icon": "bi-plug"},
            {"var": "Kcal_h", "title": "kcal/h", "icon": "bi-fire"},
            {"var": "Vazao", "title": "Vazão", "icon": "bi-water"},
            {"var": "KWAquecimento", "title": "kW Aquecimento", "icon": "bi-sun"},
            {"var": "KWConsumo", "title": "kW Consumo", "icon": "bi-power"},
            {"var": "COP", "title": "COP", "icon": "bi-graph-up"},
        ]

        # Exibir os cards em 3 colunas
        cols = st.columns(3)
        for i, card in enumerate(cards_info):
            with cols[i % 3]:
                # Verifica se a coluna existe e não é nula antes de tentar acessá-la
                if card["var"] in ultima_linha and pd.notna(ultima_linha[card["var"]]):
                    valor = f"{ultima_linha[card['var']]:.2f}" if isinstance(ultima_linha[card['var']], (int, float)) else str(ultima_linha[card['var']])
                    icon_class = f"ft-card-icon {card.get('class', '')}"
                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="{card['icon']} {icon_class}"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">{card['title']}</p>
                                <p class="ft-card-value">{valor}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    # Exibe "N/D" se a coluna não existir ou o valor for nulo
                    icon_class = f"ft-card-icon {card.get('class', '')}"
                    st.markdown(
                        f"""
                        <div class="ft-card">
                            <i class="{card['icon']} {icon_class}"></i>
                            <div class="ft-card-content">
                                <p class="ft-card-title">{card['title']}</p>
                                <p class="ft-card-value">N/D</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
    else:
        st.warning("O arquivo de dados mais recente está vazio ou não pôde ser lido.")

st.markdown("---") # Separador visual

# --- Abas para Históricos e Gráficos ---
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("## Históricos Disponíveis")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo de histórico encontrado.")
    else:
        # Filtros
        modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
        anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])), reverse=True)
        meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"])))
        ops_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"])))

        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_modelo = st.selectbox("Modelo:", ["Todos"] + modelos_disponiveis, key="hist_modelo")
        with col2:
            filtro_ano = st.selectbox("Ano:", ["Todos"] + anos_disponiveis, key="hist_ano")
        with col3:
            filtro_mes = st.selectbox("Mês:", ["Todos"] + meses_disponiveis, key="hist_mes")

        filtro_data_especifica = st.text_input("Data específica (opcional - YYYYMMDD):", key="hist_data_especifica")
        filtro_op = st.selectbox("Operação (OP):", ["Todas"] + ops_disponiveis, key="hist_op")

        arquivos_filtrados = []
        for arquivo in todos_arquivos_info:
            match_modelo = (filtro_modelo == "Todos") or (arquivo["modelo"] == filtro_modelo)
            match_ano = (filtro_ano == "Todos") or (arquivo["ano"] == filtro_ano)
            match_mes = (filtro_mes == "Todos") or (arquivo["mes"] == filtro_mes)
            match_op = (filtro_op == "Todos") or (arquivo["operacao"] == filtro_op)

            match_data_especifica = True
            if filtro_data_especifica:
                try:
                    data_obj = datetime.strptime(filtro_data_especifica, "%Y%m%d").date()
                    match_data_especifica = (arquivo["data"] == data_obj)
                except ValueError:
                    st.warning("Formato de data específica inválido. Use YYYYMMDD.")
                    match_data_especifica = False

            if match_modelo and match_ano and match_mes and match_op and match_data_especifica:
                arquivos_filtrados.append(arquivo)

        if not arquivos_filtrados:
            st.info("Nenhum histórico encontrado com os filtros aplicados.")
        else:
            # Ordenar por data e hora (mais recente primeiro)
            arquivos_filtrados.sort(key=lambda x: (x["data"], x["hora"]), reverse=True)

            for arquivo in arquivos_filtrados:
                expander_title = (
                    f"{arquivo['modelo']} - Linha: {arquivo['linha']} - "
                    f"Data: {arquivo['data'].strftime('%d/%m/%Y')} - "
                    f"Hora: {arquivo['hora']} - Operação: {arquivo['operacao']}"
                )
                with st.expander(expander_title):
                    st.write(f"**Nome do Arquivo:** {arquivo['nome_arquivo']}")

                    df_exibir = carregar_csv_caminho(arquivo["caminho"])
                    if not df_exibir.empty:
                        st.dataframe(df_exibir, use_container_width=True)

                        # Botões de download
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            csv_data = df_exibir.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
                            st.download_button(
                                label="Baixar CSV",
                                data=csv_data,
                                file_name=f"{arquivo['nome_arquivo']}",
                                mime="text/csv",
                                key=f"dl_csv_{arquivo['nome_arquivo']}",
                            )
                        with col_dl2:
                            # Gerar PDF
                            buffer = BytesIO()
                            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
                            styles = getSampleStyleSheet()
                            elements = []

                            # Título do PDF
                            elements.append(Paragraph(f"Relatório de Teste - {arquivo['modelo']}", styles["h2"]))
                            elements.append(Spacer(1, 0.2 * cm))
                            elements.append(Paragraph(f"Operação: {arquivo['operacao']}", styles["h3"]))
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
