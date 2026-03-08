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

# Função para listar arquivos CSV e extrair informações
@st.cache_data(ttl=3600) # Cache para evitar reprocessar a cada execução
def listar_arquivos_csv(pasta_dados="dados"):
    arquivos_info = []
    # Padrão regex para extrair informações do nome do arquivo
    # Ex: historico_L1_FTA987BR_20260308_0939_OP987.csv
    # Grupo 1: Modelo (FTA987BR)
    # Grupo 2: Ano (2026)
    # Grupo 3: Mês (03)
    # Grupo 4: Dia (08)
    # Grupo 5: Hora (0939)
    # Grupo 6: Operação (OP987)
    padrao_nome_arquivo = re.compile(
        r"historico_L\d+_([A-Z0-9]+)_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)\.csv",
        re.IGNORECASE
    )

    for root, _, files in os.walk(pasta_dados):
        for nome_arquivo in files:
            if nome_arquivo.endswith(".csv"):
                match = padrao_nome_arquivo.match(nome_arquivo)
                if match:
                    modelo, ano_str, mes_str, dia_str, hora_str, operacao = match.groups()

                    try:
                        ano = int(ano_str)
                        mes = int(mes_str)
                        dia = int(dia_str)
                        # Garante que a hora tem 4 dígitos antes de fatiar
                        hora_str_padded = hora_str.zfill(4) 
                        hora = f"{hora_str_padded[:2]}:{hora_str_padded[2:]}"
                        data_completa = datetime(ano, mes, dia, int(hora_str_padded[:2]), int(hora_str_padded[2:]))
                    except ValueError:
                        # Se a conversão falhar, usa valores padrão ou N/D
                        ano, mes, dia = 0, 0, 0
                        hora = "N/D"
                        data_completa = datetime.min # Data mínima para ordenação

                    arquivos_info.append(
                        {
                            "nome_arquivo": nome_arquivo,
                            "caminho": os.path.join(root, nome_arquivo),
                            "modelo": modelo,
                            "ano": ano,
                            "mes": mes,
                            "dia": dia,
                            "hora": hora,
                            "operacao": operacao,
                            "data_completa": data_completa,
                        }
                    )
                else:
                    # Lidar com arquivos que não seguem o padrão esperado
                    arquivos_info.append(
                        {
                            "nome_arquivo": nome_arquivo,
                            "caminho": os.path.join(root, nome_arquivo),
                            "modelo": "N/D",
                            "ano": 0,
                            "mes": 0,
                            "dia": 0,
                            "hora": "N/D",
                            "operacao": "N/D",
                            "data_completa": datetime.min,
                        }
                    )
    # Ordena os arquivos pelo modelo, ano, mês, dia e hora (mais recente primeiro)
    arquivos_info.sort(key=lambda x: (x["modelo"], x["data_completa"]), reverse=True)
    return arquivos_info

# Função para carregar um arquivo CSV e padronizar as colunas
@st.cache_data(ttl=3600)
def carregar_csv_caminho(caminho_arquivo):
    colunas_esperadas = [
        "Date", "Time", "Ambiente", "Entrada", "Saída", "DeltaT", "Tensao",
        "Corrente", "Kcal_h", "Vazao", "KWAquecimento", "KWConsumo", "COP"
    ]

    try:
        # Tenta ler o CSV, assumindo que pode não ter cabeçalho ou ter nomes diferentes
        df = pd.read_csv(caminho_arquivo, header=None, sep=';', decimal=',') # Ajustado para ; e ,

        # Se o CSV tiver menos colunas que o esperado, preenche com NaN
        if df.shape[1] < len(colunas_esperadas):
            for i in range(df.shape[1], len(colunas_esperadas)):
                df[i] = pd.NA # Adiciona colunas faltantes com NA

        # Renomeia as colunas para os nomes esperados
        df.columns = colunas_esperadas[:df.shape[1]] # Garante que não tenta renomear mais colunas do que existem

        # Converte colunas numéricas, tratando erros
        for col in colunas_esperadas[2:]: # A partir de Ambiente
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo CSV '{os.path.basename(caminho_arquivo)}': {e}")
        return pd.DataFrame(columns=colunas_esperadas) # Retorna DataFrame vazio com colunas esperadas

# Função para criar um card de métrica
def metric_card(title, value, unit="", icon="bi-thermometer-half", is_red=False):
    value_str = f"{value:.2f}".replace('.', ',') if isinstance(value, (int, float)) else str(value)
    icon_class = f"ft-card-icon {'red' if is_red else ''}"
    value_class = f"ft-card-value {'red' if is_red else ''}"

    st.markdown(
        f"""
        <div class="ft-card">
            <i class="{icon} {icon_class}"></i>
            <div class="ft-card-content">
                <div class="ft-card-title">{title}</div>
                <div class="{value_class}">{value_str} {unit}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Função para gerar PDF
def gerar_pdf(df, ultima_leitura_info, nome_arquivo_base):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para o título do PDF
    style_title = ParagraphStyle(
        'TitleStyle',
        parent=styles['h1'],
        fontSize=18,
        alignment=1, # Centro
        spaceAfter=14,
        textColor=colors.HexColor('#0d6efd')
    )

    # Estilo para subtítulos
    style_subtitle = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['h2'],
        fontSize=12,
        alignment=0, # Esquerda
        spaceAfter=8,
        textColor=colors.HexColor('#343a40')
    )

    elements = []

    # Título
    elements.append(Paragraph("Relatório de Teste de Máquinas Fromtherm", style_title))
    elements.append(Spacer(1, 0.5 * cm))

    # Informações da última leitura
    elements.append(Paragraph("<b>Informações do Teste:</b>", style_subtitle))
    elements.append(Paragraph(f"<b>Modelo:</b> {ultima_leitura_info.get('modelo', 'N/D')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Operação:</b> {ultima_leitura_info.get('operacao', 'N/D')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Data:</b> {ultima_leitura_info.get('data', 'N/D')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Hora:</b> {ultima_leitura_info.get('hora', 'N/D')}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))

    # Tabela de dados
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)

    # Estilo da tabela
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# =========================
#  INÍCIO DO APP STREAMLIT
# =========================

st.title("Dashboard de Teste de Máquinas Fromtherm")

# Logo da Fromtherm (substitua pelo caminho real da sua imagem)
# st.image("caminho/para/sua/logo_fromtherm.png", width=200) # Descomente e ajuste o caminho se tiver uma logo

# Carrega todos os arquivos CSV disponíveis
todos_arquivos_info = listar_arquivos_csv()

# --- Dashboards de Última Leitura ---
st.markdown("## Última Leitura Registrada")

if todos_arquivos_info:
    # Pega o arquivo mais recente (já ordenado por data_completa, reverse=True)
    arquivo_mais_recente = todos_arquivos_info[0]
    df_ultima_leitura = carregar_csv_caminho(arquivo_mais_recente["caminho"])

    if not df_ultima_leitura.empty:
        ultima_linha = df_ultima_leitura.iloc[-1]

        # Informações do teste para exibir acima dos cards
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px; padding: 10px; border-radius: 8px; background-color: #e9f5ff; border: 1px solid #b3e0ff;">
                <p style="font-size: 1.1em; font-weight: bold; color: #0d6efd; margin: 0;">
                    Modelo: {arquivo_mais_recente.get('modelo', 'N/D')} | 
                    OP: {arquivo_mais_recente.get('operacao', 'N/D')} | 
                    Data: {arquivo_mais_recente.get('dia', 'N/D')}/{arquivo_mais_recente.get('mes', 'N/D')}/{arquivo_mais_recente.get('ano', 'N/D')} | 
                    Hora: {arquivo_mais_recente.get('hora', 'N/D')}
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Cria os cards de métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("T-Ambiente", ultima_linha.get("Ambiente", "N/D"), "°C", "bi-thermometer-half")
            metric_card("T-Entrada", ultima_linha.get("Entrada", "N/D"), "°C", "bi-arrow-down-circle")
        with col2:
            metric_card("T-Saída", ultima_linha.get("Saída", "N/D"), "°C", "bi-arrow-up-circle", is_red=True)
            metric_card("DIF", ultima_linha.get("DeltaT", "N/D"), "°C", "bi-arrow-down-up")
        with col3:
            metric_card("Tensão", ultima_linha.get("Tensao", "N/D"), "V", "bi-lightning-charge")
            metric_card("Corrente", ultima_linha.get("Corrente", "N/D"), "A", "bi-lightning")
        with col4:
            metric_card("kcal/h", ultima_linha.get("Kcal_h", "N/D"), "", "bi-fire")
            metric_card("Vazão", ultima_linha.get("Vazao", "N/D"), "L/h", "bi-water")

        col5, col6 = st.columns(2)
        with col5:
            metric_card("kW Aquecimento", ultima_linha.get("KWAquecimento", "N/D"), "kW", "bi-thermometer-sun")
        with col6:
            metric_card("kW Consumo", ultima_linha.get("KWConsumo", "N/D"), "kW", "bi-plug")

        # COP separado
        st.markdown("<div style='display: flex; justify-content: center; margin-top: 10px;'>", unsafe_allow_html=True)
        metric_card("COP", ultima_linha.get("COP", "N/D"), "", "bi-award")
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("Não foi possível carregar a última leitura do arquivo mais recente ou o arquivo está vazio.")
else:
    st.info("Nenhum arquivo CSV encontrado na pasta 'dados'.")

st.markdown("---")

# --- Abas para Históricos e Gráficos ---
tab1, tab2 = st.tabs(["Históricos Disponíveis", "Crie Seu Gráfico"])

with tab1:
    st.header("Históricos de Testes")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo CSV encontrado para exibir históricos.")
    else:
        # Filtros para os históricos
        st.markdown("### Filtros de Arquivos")
        col_filt1, col_filt2, col_filt3, col_filt4 = st.columns(4)

        with col_filt1:
            modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))
            filtro_modelo = st.selectbox("Modelo:", ["Todos"] + modelos_disponiveis, key="filtro_modelo")

        with col_filt2:
            anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"] != 0)), reverse=True)
            filtro_ano = st.selectbox("Ano:", ["Todos"] + anos_disponiveis, key="filtro_ano")

        with col_filt3:
            meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"] != 0)))
            meses_labels = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
            filtro_mes_label = st.selectbox(
                "Mês:", 
                ["Todos"] + [meses_labels[m] for m in meses_disponiveis], 
                key="filtro_mes"
            )
            filtro_mes = next((m for m, label in meses_labels.items() if label == filtro_mes_label), None) if filtro_mes_label != "Todos" else None

        with col_filt4:
            datas_disponiveis = sorted(list(set(f"{a['dia']:02d}/{a['mes']:02d}/{a['ano']}" for a in todos_arquivos_info if a["dia"] != 0)), reverse=True)
            filtro_data = st.selectbox("Data:", ["Todas"] + datas_disponiveis, key="filtro_data")

        arquivos_filtrados = []
        for arquivo in todos_arquivos_info:
            match_modelo = (filtro_modelo == "Todos" or arquivo["modelo"] == filtro_modelo)
            match_ano = (filtro_ano == "Todos" or arquivo["ano"] == filtro_ano)
            match_mes = (filtro_mes is None or arquivo["mes"] == filtro_mes)
            match_data = (filtro_data == "Todas" or f"{arquivo['dia']:02d}/{arquivo['mes']:02d}/{arquivo['ano']}" == filtro_data)

            if match_modelo and match_ano and match_mes and match_data:
                arquivos_filtrados.append(arquivo)

        if arquivos_filtrados:
            st.markdown("### Arquivos Encontrados")
            for arquivo in arquivos_filtrados:
                col_arq1, col_arq2, col_arq3 = st.columns([0.6, 0.2, 0.2])
                with col_arq1:
                    st.markdown(f"**{arquivo['modelo']}** | OP: {arquivo['operacao']} | Data: {arquivo['dia']:02d}/{arquivo['mes']:02d}/{arquivo['ano']} | Hora: {arquivo['hora']}")
                with col_arq2:
                    if st.button(f"Ver Detalhes {arquivo['nome_arquivo']}", key=f"detalhes_{arquivo['nome_arquivo']}"):
                        st.session_state["arquivo_selecionado_detalhes"] = arquivo["caminho"]
                        st.session_state["arquivo_selecionado_info"] = arquivo
                with col_arq3:
                    df_para_pdf = carregar_csv_caminho(arquivo["caminho"])
                    if not df_para_pdf.empty:
                        # Formata o nome do arquivo PDF/Excel
                        nome_base_formatado = (
                            f"Maquina_{arquivo['modelo']}_OP{arquivo['operacao']}_"
                            f"{arquivo['dia']:02d}/{arquivo['mes']:02d}/{arquivo['ano']}_"
                            f"{arquivo['hora'].replace(':', '')}hs"
                        )
                        pdf_buffer = gerar_pdf(df_para_pdf, arquivo, nome_base_formatado)
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=f"{nome_base_formatado}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{arquivo['nome_arquivo']}"
                        )
        else:
            st.info("Nenhum arquivo encontrado com os filtros aplicados.")

        if "arquivo_selecionado_detalhes" in st.session_state and st.session_state["arquivo_selecionado_detalhes"]:
            st.markdown("---")
            st.subheader(f"Detalhes do Arquivo: {st.session_state['arquivo_selecionado_info']['nome_arquivo']}")
            df_detalhes = carregar_csv_caminho(st.session_state["arquivo_selecionado_detalhes"])
            if not df_detalhes.empty:
                st.dataframe(df_detalhes, use_container_width=True)
            else:
                st.warning("Não foi possível carregar os detalhes deste arquivo.")

with tab2:
    st.header("Crie Seu Gráfico")

    if not todos_arquivos_info:
        st.info("Nenhum arquivo CSV encontrado para criar gráficos.")
    else:
        # Filtros para o gráfico
        st.markdown("### Selecione os Dados para o Gráfico")
        col_graf1, col_graf2, col_graf3, col_graf4 = st.columns(4)

        modelos_disponiveis_graf = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] != "N/D")))

        with col_graf1:
            modelo_graf = st.selectbox(
                "Modelo:",
                modelos_disponiveis_graf if modelos_disponiveis_graf else ["Nenhum Modelo disponível"],
                key="graf_modelo",
            )

        arquivos_por_modelo = [a for a in todos_arquivos_info if a["modelo"] == modelo_graf]
        anos_disponiveis_graf = sorted(list(set(a["ano"] for a in arquivos_por_modelo if a["ano"] != 0)), reverse=True)

        with col_graf2:
            ano_graf = st.selectbox(
                "Ano:",
                anos_disponiveis_graf if anos_disponiveis_graf else [datetime.now().year],
                key="graf_ano",
            )

        arquivos_por_modelo_ano = [a for a in arquivos_por_modelo if a["ano"] == ano_graf]
        meses_disponiveis_graf = sorted(list(set(a["mes"] for a in arquivos_por_modelo_ano if a["mes"] != 0)))
        meses_labels_graf = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }

        with col_graf3:
            mes_graf_label = st.selectbox(
                "Mês:",
                ["Todos"] + [meses_labels_graf[m] for m in meses_disponiveis_graf],
                key="graf_mes",
            )
            mes_graf = next((m for m, label in meses_labels_graf.items() if label == mes_graf_label), None) if mes_graf_label != "Todos" else None

        with col_graf4:
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