import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
import re

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
# from reportlab.lib.units import inch  # <-- REMOVIDO PARA EVITAR NameError

from io import BytesIO
import plotly.express as px

# -------------------------------------------------
# Configuração básica
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Teste de Máquinas Fromtherm")

# -------------------------------------------------
# CSS simples (mantém layout, não mexe em nada estrutural)
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* REMOÇÃO DEFINITIVA DO "0" TEIMOSO (abordagem mais agressiva e genérica) */
    /* Esconde o botão de menu do Streamlit, que geralmente contém o "0" */
    button[data-testid="stSidebarNavToggle"] {
        display: none !important;
    }
    /* Esconde o elemento que pode conter o "0" em alguns casos */
    span[data-testid="stDecoration"] {
        display: none !important;
    }
    /* Outras tentativas de esconder elementos que podem aparecer */
    summary {
        display: none !important;
    }
    div[data-testid="stAppViewContainer"] > div:first-child span {
        display: none !important;
    }

    /* Estilo dos cards */
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .ft-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd;
        animation: ft-pulse 1.5s ease-in-out infinite;
    }
    .ft-card-icon.red {
        color: #dc3545;
    }
    .ft-card-content {
        flex-grow: 1;
    }
    .ft-card-title {
        margin: 0;
        font-size: 0.9em;
        color: #6c757d;
        font-weight: 600;
    }
    .ft-card-value {
        margin: 0;
        font-size: 1.5em;
        font-weight: 800;
        color: #343a40;
    }
    @keyframes ft-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    /* Estilo para o cabeçalho principal */
    .st-emotion-cache-10q706c { /* Seletor específico para o cabeçalho do Streamlit */
        padding-top: 0rem;
    }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. CONFIGURAÇÃO DE DADOS
# -------------------------------------------------
# Caminho relativo para o Streamlit Cloud
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

@st.cache_data(ttl=5)
def buscar_arquivos():
    if not os.path.exists(DADOS_DIR):
        st.warning(f"Diretório de dados não encontrado: {DADOS_DIR}. Verifique a estrutura do repositório.")
        return []

    caminhos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    lista = []
    for c in caminhos:
        n = os.path.basename(c)
        parts = n.replace(".csv", "").split("_")
        if len(parts) >= 6:
            try:
                dt = datetime.strptime(parts[2], "%Y%m%d").date()
                lista.append({
                    "nome": n, "caminho": c, "data": dt,
                    "ano": str(dt.year), "mes": dt.strftime("%m"),
                    "data_f": dt.strftime("%d/%m/%Y"),
                    "hora": f"{parts[3][:2]}:{parts[3][2:]}",
                    "operacao": parts[4], "modelo": parts[5]
                })
            except ValueError:
                st.warning(f"Erro ao processar nome do arquivo CSV: {n}. Formato de data ou hora inválido.")
                continue
        else:
            st.warning(f"Nome de arquivo CSV inválido: {n}. Esperado pelo menos 6 partes separadas por '_'.")
    return sorted(lista, key=lambda x: (x['data'], x['hora']), reverse=True)

def carregar_csv(caminho):
    try:
        # Tenta ler com separador ';'
        df = pd.read_csv(caminho, sep=";", engine="python")
        # Se o número de colunas for muito baixo, tenta com ','
        if len(df.columns) < 5:
            df = pd.read_csv(caminho, sep=",", engine="python")

        # Define os nomes das colunas esperadas
        colunas_esperadas = ["Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]

        # Verifica se o número de colunas corresponde
        if len(df.columns) != len(colunas_esperadas):
            st.warning(f"Número de colunas no CSV '{os.path.basename(caminho)}' ({len(df.columns)}) não corresponde ao esperado ({len(colunas_esperadas)}).")
            # Tenta renomear as colunas existentes até onde for possível
            df.columns = colunas_esperadas[:len(df.columns)]
            # Adiciona colunas faltantes com NaN
            for col in colunas_esperadas[len(df.columns):]:
                df[col] = pd.NA
        else:
            df.columns = colunas_esperadas

        # Converte colunas numéricas, tratando erros
        for col in ["Ambiente", "Entrada", "Saída", "ΔT", "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento", "kW Consumo", "COP"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') # 'coerce' transforma erros em NaN

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o CSV '{os.path.basename(caminho)}': {e}")
        return pd.DataFrame()

def extrair_ultima_linha(df):
    if not df.empty:
        return df.iloc[-1].to_dict()
    return {}

# -------------------------------------------------
# 4. BARRA LATERAL (SIDEBAR) - SEM LOGO LOCAL
# -------------------------------------------------
arquivos_lista = buscar_arquivos()

with st.sidebar:
    st.markdown("---") # Linha divisória no lugar da logo
    st.subheader("FILTROS DE BUSCA")

    sel_modelo = st.selectbox("📦 Modelo", ["Todos"] + sorted(list({a['modelo'] for a in arquivos_lista})))
    sel_op = st.text_input("🔢 Operação (OP)", help="Digite o número da OP").strip() # .strip() para remover espaços
    sel_ano = st.selectbox("📅 Ano", ["Todos"] + sorted(list({a['ano'] for a in arquivos_lista}), reverse=True))
    sel_mes = st.selectbox("📆 Mês", ["Todos"] + sorted(list({a['mes'] for a in arquivos_lista})))

# Filtragem Dinâmica
filtrados = [a for a in arquivos_lista if
             (sel_modelo == "Todos" or a['modelo'] == sel_modelo) and
             (not sel_op or a['operacao'].lower() == sel_op.lower()) and # Filtra por OP
             (sel_ano == "Todos" or a['ano'] == sel_ano) and
             (sel_mes == "Todos" or a['mes'] == sel_mes)
            ]

# -------------------------------------------------
# 5. FUNÇÕES AUXILIARES PARA EXIBIÇÃO
# -------------------------------------------------
def mostra_valor(titulo, valor, unidade="", icone="bi bi-info-circle"):
    # Garante que o valor seja exibido como "N/D" se for NaN ou None
    if pd.isna(valor) or valor is None:
        valor_str = "N/D"
    elif isinstance(valor, (int, float)):
        valor_str = f"{valor:.2f}" # Formata para 2 casas decimais se for número
    else:
        valor_str = str(valor) # Converte para string se for outro tipo

    st.markdown(f"""
        <div class="ft-card">
            <i class="{icone} ft-card-icon"></i>
            <div class="ft-card-content">
                <p class="ft-card-title">{titulo}</p>
                <p class="ft-card-value">{valor_str} {unidade}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Função para criar PDF (sem 'inch' e com tratamento de valores)
def criar_pdf(df, nome_arquivo_original):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()

    # Estilo para o título do PDF
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=18, leading=22,
                              alignment=1, spaceAfter=12, fontName='Helvetica-Bold'))
    # Estilo para o cabeçalho da tabela
    styles.add(ParagraphStyle(name='TableHeaderStyle', fontSize=10, leading=12,
                              alignment=1, fontName='Helvetica-Bold', textColor=colors.white))
    # Estilo para o conteúdo da tabela
    styles.add(ParagraphStyle(name='TableContentStyle', fontSize=9, leading=10,
                              alignment=1, fontName='Helvetica'))

    elements = []

    # Título
    elements.append(Paragraph(f"Relatório de Dados - {nome_arquivo_original.replace('.csv', '')}", styles['TitleStyle']))
    elements.append(Spacer(1, 0.2 * 72)) # 0.2 polegadas = 0.2 * 72 pontos

    # Preparar dados para a tabela
    data = [
        [Paragraph(col, styles['TableHeaderStyle']) for col in df.columns]
    ]
    for _, row in df.iterrows():
        data.append([Paragraph(str(row[col]) if pd.notna(row[col]) else "N/D", styles['TableContentStyle']) for col in df.columns])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), # Cabeçalho azul escuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------------------------------
# 6. LAYOUT PRINCIPAL DO DASHBOARD
# -------------------------------------------------
st.markdown('<p class="main-header">Monitoramento de Máquinas Fromtherm</p>', unsafe_allow_html=True)

# Abas
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.subheader("Última Leitura Registrada")

    if arquivos_lista:
        ultimo_arquivo = arquivos_lista[0]['caminho']
        df_ultimo = carregar_csv(ultimo_arquivo)
        ultima_linha = extrair_ultima_linha(df_ultimo)

        col1, col2, col3, col4 = st.columns(4)
        with col1: mostra_valor("T-Ambiente", ultima_linha.get('Ambiente'), "°C", "bi bi-thermometer")
        with col2: mostra_valor("T-Entrada", ultima_linha.get('Entrada'), "°C", "bi bi-arrow-down-circle")
        with col3: mostra_valor("T-Saída", ultima_linha.get('Saída'), "°C", "bi bi-arrow-up-circle")
        with col4: mostra_valor("ΔT", ultima_linha.get('ΔT'), "°C", "bi bi-arrows-expand")

        col5, col6, col7, col8 = st.columns(4)
        with col5: mostra_valor("Tensão", ultima_linha.get('Tensão'), "V", "bi bi-lightning")
        with col6: mostra_valor("Corrente", ultima_linha.get('Corrente'), "A", "bi bi-lightning-charge")
        with col7: mostra_valor("Vazão", ultima_linha.get('Vazão'), "L/min", "bi bi-droplet")
        with col8: mostra_valor("COP", ultima_linha.get('COP'), "", "bi bi-award")

    else:
        st.info("Nenhum histórico encontrado para exibir a última leitura.")

    st.markdown("---")
    st.subheader("Históricos Disponíveis")

    if filtrados:
        for arq in filtrados:
            expander_label = f"**{arq['modelo']}** | OP: {arq['operacao']} | Data: {arq['data_f']} | Hora: {arq['hora']}"
            with st.expander(expander_label):
                df_exibir = carregar_csv(arq['caminho'])
                if not df_exibir.empty:
                    st.dataframe(df_exibir, use_container_width=True)

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        pdf_buffer = criar_pdf(df_exibir, arq['nome'])
                        st.download_button(
                            label="Baixar PDF",
                            data=pdf_buffer,
                            file_name=f"{arq['nome'].replace('.csv', '')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with col_dl2:
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            df_exibir.to_excel(writer, index=False, sheet_name='Dados')
                        excel_buffer.seek(0)
                        st.download_button(
                            label="Baixar Excel",
                            data=excel_buffer,
                            file_name=f"{arq['nome'].replace('.csv', '')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.warning(f"Não foi possível carregar os dados para {arq['nome']}.")
    else:
        st.info("Nenhum histórico corresponde aos filtros aplicados.")

with tab2:
    st.subheader("Crie Seu Gráfico Personalizado")
    if filtrados:
        modelos_graf = sorted(list({a['modelo'] for a in filtrados}))
        op_graf = sorted(list({a['operacao'] for a in filtrados}))
        datas_graf = sorted(list({a['data_f'] for a in filtrados}), reverse=True)

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1: modelo_graf = st.selectbox("Modelo", modelos_graf, key="modelo_graf")
        with col_g2: op_graf_sel = st.selectbox("Operação (OP)", op_graf, key="op_graf")
        with col_g3: data_graf = st.selectbox("Data", datas_graf, key="data_graf")

        # Encontrar o caminho do arquivo selecionado para o gráfico
        caminho_graf = next((a['caminho'] for a in filtrados if
                             a['modelo'] == modelo_graf and
                             a['operacao'] == op_graf_sel and
                             a['data_f'] == data_graf), None)

        if caminho_graf:
            df_graf = carregar_csv(caminho_graf)
            if not df_graf.empty:
                # Identificar colunas numéricas para o gráfico
                colunas_numericas = df_graf.select_dtypes(include=['number']).columns.tolist()
                if "Date" in colunas_numericas: colunas_numericas.remove("Date")
                if "Time" in colunas_numericas: colunas_numericas.remove("Time")

                if colunas_numericas:
                    variaveis_selecionadas = st.multiselect(
                        "Selecione as variáveis para o gráfico",
                        colunas_numericas,
                        default=colunas_numericas[:min(3, len(colunas_numericas))] # Seleciona até 3 por padrão
                    )

                    if variaveis_selecionadas:
                        df_plot = df_graf[['Date', 'Time'] + variaveis_selecionadas].copy()
                        df_plot['DateTime'] = pd.to_datetime(df_plot['Date'] + ' ' + df_plot['Time'], errors='coerce')
                        df_plot = df_plot.dropna(subset=['DateTime'])

                        df_melted = df_plot.melt(
                            id_vars=["DateTime"],
                            value_vars=variaveis_selecionadas,
                            var_name="Variável",
                            value_name="Valor",
                        )
                        fig = px.line(
                            df_melted,
                            x="DateTime",
                            y="Valor",
                            color="Variável",
                            title=f"Modelo {modelo_graf} | OP {op_graf_sel} | {data_graf}",
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
                            "- Use o botão de **fullscreen** no gráfico (canto superior direito do gráfico) para tela cheia.\n"
                            "- Use o ícone de **câmera** para baixar como imagem (PNG).\n"
                            "- A imagem pode ser enviada por WhatsApp, e-mail, etc., em PC ou celular."
                        )
                else:
                    st.info("Nenhuma variável numérica encontrada para gerar gráficos neste histórico.")
            else:
                st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados ou dados inválidos.")
        else:
            st.info("Selecione um Modelo, Operação e Data para gerar o gráfico.")
    else:
        st.info("Nenhum histórico disponível para gerar gráficos com os filtros aplicados.")