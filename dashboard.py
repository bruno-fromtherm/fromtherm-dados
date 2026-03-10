import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
# from reportlab.lib.pagesizes import A4, landscape # Comentado, pois a função PDF não está definida
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle # Comentado
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # Comentado
# from reportlab.lib import colors # Comentado
from io import BytesIO
import plotly.express as px
import re # Importar re para expressões regulares

# --- Configuração básica da página ---
st.set_page_config(layout="wide", page_title="Máquina de Teste Fromtherm")

# =========================
#  CSS GLOBAL (fundo + correção do "0")
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

    /* Esconder qualquer pequeno span/ícone no topo esquerdo
       que esteja causando o "0" indesejado */
    div[data-testid="stAppViewContainer"] > div:first-child span {
        font-size: 0px !important;
        color: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Logo e cabeçalho na barra lateral ---
LOGO_URL = "https://fromtherm.com.br/wp-content/uploads/2023/07/logo-fromtherm-1.png"
st.sidebar.image(LOGO_URL, use_column_width=True)
st.sidebar.title("FromTherm")

# --- Título principal da página ---
st.title("Máquina de Teste Fromtherm")

# --- Pasta onde ficam os arquivos de histórico ---
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_20260308_0939_OP987_FTA987BR.csv
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        # Ajustado para o novo padrão de nome de arquivo
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d{3})_(FTA\d{3}BR)\.csv", nome)

        if match:
            year_str, month_str, day_str, time_str, operacao, modelo = match.groups()

            try:
                data = datetime.strptime(f"{year_str}{month_str}{day_str}", "%Y%m%d").date()
                ano = int(year_str)
                mes = int(month_str)
                hora = f"{time_str[:2]}:{time_str[2:]}"
            except ValueError:
                data, ano, mes, hora = None, None, None, None
        else:
            data, ano, mes, hora, operacao, modelo = None, None, None, None, "N/D", "N/D"

        info_arquivos.append(
            {
                "nome_arquivo": nome,
                "caminho": caminho,
                "linha": "L1", # Hardcoded como L1, ajuste se for dinâmico
                "data": data,
                "ano": ano,
                "mes": mes,
                "hora": hora,
                "operacao": operacao,
                "modelo": modelo,
            }
        )

    return info_arquivos


# --- Função para carregar um CSV e processar (com tratamento aprimorado) ---
@st.cache_data(ttl=600) # Cache por 10 minutos
def carregar_csv_caminho(caminho: str) -> pd.DataFrame:
    try:
        # Ajustado para ler com separador de espaço/tab e decimal '.'
        # O 'sep=r'\s+'' usa regex para um ou mais espaços/tabs como separador
        df = pd.read_csv(caminho, sep=r'\s+', decimal='.', encoding='utf-8')

        # Limpeza e conversão de tipos
        for col in df.columns:
            # Tentar converter para numérico (float)
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except ValueError:
                pass # Se não for numérico, mantém o tipo original

        # Renomear colunas para o padrão esperado no dashboard
        # Certifique-se que esta lista de colunas corresponde EXATAMENTE ao seu CSV
        expected_columns = [
            "Date", "Time", "Ambiente", "Entrada", "Saída", "ΔT",
            "Tensão", "Corrente", "kcal/h", "Vazão", "kW Aquecimento",
            "kW Consumo", "COP"
        ]
        # Verifica se o número de colunas corresponde antes de renomear
        if len(df.columns) == len(expected_columns):
            df.columns = expected_columns
        else:
            st.warning(f"O número de colunas no arquivo {os.path.basename(caminho)} ({len(df.columns)}) não corresponde ao esperado ({len(expected_columns)}). As colunas podem estar incorretas.")
            # Tenta renomear as que batem, ou deixa como está se for muito diferente
            # Ou você pode adicionar uma lógica mais robusta aqui.

        # Combinar 'Date' e 'Time' em uma única coluna de datetime
        if 'Date' in df.columns and 'Time' in df.columns:
            # Ajuste o formato da data para 'YYYY/MM/DD' conforme o CSV
            df['DateTime'] = pd.to_datetime(
                df['Date'].astype(str) + ' ' + df['Time'].astype(str),
                errors='coerce',
                format='%Y/%m/%d %H:%M:%S' # Formato exato do seu CSV
            )
            df = df.drop(columns=['Date', 'Time']) # Remove as colunas originais
            # Mover 'DateTime' para o início do DataFrame
            cols = ['DateTime'] + [col for col in df.columns if col != 'DateTime']
            df = df[cols]

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo {caminho}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro


# --- Carregar lista de arquivos ---
todos_arquivos_info = listar_arquivos_csv()

if not todos_arquivos_info:
    st.warning(f"Nenhum arquivo .csv de histórico encontrado na pasta '{DADOS_DIR}'.")
    st.info("Verifique se os arquivos .csv foram sincronizados corretamente para o GitHub.")
    st.stop()

# --- Determinar o arquivo mais recente (por data + hora) ---
# Garante que 'data' e 'hora' não sejam None para a comparação
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

# CSS + Bootstrap Icons para cards bonitos com animação nos ícones
st.markdown(
    """
    <style>
    .ft-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        border-left: 4px solid #0d6efd;
    }
    .ft-card-icon {
        font-size: 26px;
        margin-right: 10px;
        color: #0d6efd;
        animation: ft-pulse 1.5s ease-in-out infinite;
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

    @keyframes ft-pulse {
        0%   { transform: scale(1);   opacity: 0.9; }
        50%  { transform: scale(1.10); opacity: 1; }
        100% { transform: scale(1);   opacity: 0.9; }
    }
    </style>

    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    """,
    unsafe_allow_html=True,
)

try:
    df_ultimo = carregar_csv_caminho(arquivo_mais_recente["caminho"])

    if not df_ultimo.empty:
        ultima_linha = df_ultimo.iloc[-1]

        modelo_info = arquivo_mais_recente["modelo"] or "N/D"
        op_info = arquivo_mais_recente["operacao"] or "N/D"
        data_info = arquivo_mais_recente["data"].strftime("%d/%m/%Y") if arquivo_mais_recente["data"] else "N/D"
        ano_info = arquivo_mais_recente["ano"] or "N/D"
        hora_info = arquivo_mais_recente["hora"] or "N/D"

        # Cabeçalho com informações do teste
        st.markdown(
            f"**Modelo:** {modelo_info} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Operação (OP):** {op_info} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Data:** {data_info} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Ano:** {ano_info} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"**Hora:** {hora_info}",
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        # Coluna 1: temperaturas
        with col1:
            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-thermometer-half ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">T-Ambiente (°C)</p>
                    <p class="ft-card-value">{ultima_linha['Ambiente']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-arrow-down-circle ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">T-Entrada (°C)</p>
                    <p class="ft-card-value">{ultima_linha['Entrada']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-arrow-up-circle ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">T-Saída (°C)</p>
                    <p class="ft-card-value">{ultima_linha['Saída']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-plus-slash-minus ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">DIF (ΔT) (°C)</p>
                    <p class="ft-card-value">{ultima_linha['ΔT']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Coluna 2: elétrica + vazão
        with col2:
            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-lightning-charge ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">Tensão (V)</p>
                    <p class="ft-card-value">{ultima_linha['Tensão']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-lightning ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">Corrente (A)</p>
                    <p class="ft-card-value">{ultima_linha['Corrente']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-fire ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">kcal/h</p>
                    <p class="ft-card-value">{ultima_linha['kcal/h']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-droplet ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">Vazão</p>
                    <p class="ft-card-value">{ultima_linha['Vazão']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Coluna 3: potências e COP
        with col3:
            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-sun ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">kW Aquecimento</p>
                    <p class="ft-card-value">{ultima_linha['kW Aquecimento']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-plug ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">kW Consumo</p>
                    <p class="ft-card-value">{ultima_linha['kW Consumo']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="ft-card">
                  <i class="bi bi-speedometer2 ft-card-icon"></i>
                  <div class="ft-card-content">
                    <p class="ft-card-title">COP</p>
                    <p class="ft-card-value">{ultima_linha['COP']}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.warning("Não foi possível carregar os dados da última leitura. Verifique o arquivo CSV.")

except Exception as e:
    st.error(f"Não foi possível gerar o painel da última leitura: {e}")
    st.info("Verifique se o formato do CSV está conforme o padrão esperado.")


# --- TABS PRINCIPAIS ---
tab_hist, tab_graf = st.tabs(["📄 Históricos e Planilhas", "📊 Crie Seu Gráfico"])


# =========================
#  TAB 1 - HISTÓRICOS
# =========================
with tab_hist:
    st.sidebar.header("Filtros - Históricos")

    modelos_disponiveis = sorted({a["modelo"] for a in todos_arquivos_info if a["modelo"]})
    anos_disponiveis = sorted({a["ano"] for a in todos_arquivos_info if a["ano"]})
    meses_disponiveis = sorted({a["mes"] for a in todos_arquivos_info if a["mes"]})
    datas_disponiveis = sorted(
        {a["data"] for a in todos_arquivos_info if a["data"]},
        reverse=True,
    )
    ops_disponiveis = sorted({a["operacao"] for a in todos_arquivos_info if a["operacao"]})

    modelo_selecionado = st.sidebar.selectbox(
        "Modelo:",
        ["Todos"] + modelos_disponiveis,
        key="hist_modelo",
    )

    ano_selecionado = st.sidebar.selectbox(
        "Ano:",
        ["Todos"] + anos_disponiveis if anos_disponiveis else ["Todos"],
        key="hist_ano",
    )

    mes_label_map = {
        1: "01 - Jan", 2: "02 - Fev", 3: "03 - Mar", 4: "04 - Abr",
        5: "05 - Mai", 6: "06 - Jun", 7: "07 - Jul", 8: "08 - Ago",
        9: "09 - Set", 10: "10 - Out", 11: "11 - Nov", 12: "12 - Dez",
    }

    meses_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis] if meses_disponiveis else ["Todos"]
    mes_selecionado_label = st.sidebar.selectbox(
        "Mês:",
        meses_labels,
        key="hist_mes",
    )
    mes_selecionado = None
    if mes_selecionado_label != "Todos":
        mes_selecionado = int(mes_selecionado_label.split(" ")[0])

    data_selecionada = st.sidebar.date_input(
        "Data específica (opcional):",
        value=None,
        min_value=min(datas_disponiveis) if datas_disponiveis else None,
        max_value=max(datas_disponiveis) if datas_disponiveis else None,
        key="hist_data",
    )

    operacao_selecionada = st.sidebar.selectbox(
        "Operação (OP):",
        ["Todas"] + ops_disponiveis,
        key="hist_op",
    )

    # Aplicar filtros em cadeia
    arquivos_filtrados = todos_arquivos_info

    if modelo_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["modelo"] == modelo_selecionado]

    if ano_selecionado != "Todos":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["ano"] == ano_selecionado]

    if mes_selecionado is not None:
        arquivos_filtrados = [a for a in arquivos_filtrados if a["mes"] == mes_selecionado]

    if data_selecionada:
        arquivos_filtrados = [a for a in arquivos_filtrados if a["data"] == data_selecionada]

    if operacao_selecionada != "Todas":
        arquivos_filtrados = [a for a in arquivos_filtrados if a["operacao"] == operacao_selecionada]

    arquivos_filtrados = sorted(
        arquivos_filtrados,
        key=lambda x: (x["data"] if x["data"] else datetime.min.date(), x["hora"] or ""),
        reverse=True,
    )

    st.markdown("### Históricos Disponíveis")

    if not arquivos_filtrados:
        st.info("Nenhum arquivo encontrado com os filtros selecionados.")
    else:
        for i, arquivo in enumerate(arquivos_filtrados):
            with st.expander(
                f"{arquivo['modelo']} - Linha: {arquivo['linha']} - Data: {arquivo['data'].strftime('%d/%m/%Y')} - "
                f"Hora: {arquivo['hora']} - Operação: {arquivo['operacao']}"
            ):
                try:
                    df_dados = carregar_csv_caminho(arquivo["caminho"])

                    if not df_dados.empty:
                        st.dataframe(df_dados, use_container_width=True)

                        data_nome = arquivo["data"].strftime("%d-%m-%Y") if arquivo["data"] else "data"
                        hora_nome = (arquivo["hora"] or "hora").replace(":", "-")

                        output_excel = BytesIO()
                        with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
                            df_dados.to_excel(writer, index=False, sheet_name="Dados")
                            workbook = writer.book
                            worksheet = writer.sheets["Dados"]

                            title_format = workbook.add_format(
                                {
                                    "bold": True,
                                    "font_size": 14,
                                    "font_color": "white",
                                    "align": "center",
                                    "valign": "vcenter",
                                    "bg_color": "#003366",
                                }
                            )
                            header_info_label = workbook.add_format(
                                {
                                    "bold": True,
                                    "font_color": "black",
                                    "align": "left",
                                }
                            )
                            header_info_value = workbook.add_format(
                                {"font_size": 11, "font_color": "black", "align": "left"}
                            )
                            header_data_format = workbook.add_format(
                                {
                                    "bold": True,
                                    "font_color": "white",
                                    "bg_color": "#003366",
                                    "border": 1,
                                    "align": "center",
                                }
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
                                elif "Date" in col_name: # Coluna 'Date' não existe mais após a conversão para 'DateTime'
                                    worksheet.set_column(col_idx, col_idx, 10)
                                elif "Time" in col_name: # Coluna 'Time' não existe mais
                                    worksheet.set_column(col_idx, col_idx, 8)
                                elif "DateTime" in col_name: # Adicionado para a nova coluna de data/hora
                                    worksheet.set_column(col_idx, col_idx, 18)
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

                        # PDF - Mantenha comentado se não tiver a função criar_pdf_paisagem definida
                        # pdf_buffer = BytesIO()
                        # pdf_buffer = criar_pdf_paisagem(df_dados, arquivo)
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
                    else:
                        st.warning(f"Não foi possível exibir dados para o arquivo '{arquivo['nome_arquivo']}'.")

                except Exception as e:
                    st.error(f"Erro ao carregar ou exibir o arquivo '{arquivo['nome_arquivo']}': {e}")
                    st.info("Verifique se o arquivo CSV está no formato correto (separado por espaços e decimal ponto).")


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
            df_graf = carregar_csv_caminho(arquivo_escolhido["caminho"])

            if not df_graf.empty:
                # A coluna 'DateTime' já deve estar criada e formatada por carregar_csv_caminho
                # Certifique-se que o nome da coluna de tempo é 'DateTime' para o gráfico
                if 'DateTime' not in df_graf.columns:
                    st.error("Coluna 'DateTime' não encontrada no DataFrame para o gráfico. Verifique a função de carregamento.")
                else:
                    st.markdown("### Variáveis para o gráfico")

                    # Usar os nomes de colunas do DataFrame carregado, exceto 'DateTime'
                    variaveis_opcoes = [col for col in df_graf.columns if col != 'DateTime']

                    vars_selecionadas = st.multiselect(
                        "Selecione uma ou mais variáveis:",
                        variaveis_opcoes,
                        default=["Ambiente", "Entrada", "Saída"] if all(v in variaveis_opcoes for v in ["Ambiente", "Entrada", "Saída"]) else variaveis_opcoes[:3],
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
            else:
                st.warning(f"Não foi possível carregar dados para o gráfico do arquivo '{arquivo_escolhido['nome_arquivo']}'.")

        except Exception as e:
            st.error(f"Erro ao carregar dados para o gráfico: {e}")
            st.info("Verifique se o arquivo CSV está no formato correto.")
