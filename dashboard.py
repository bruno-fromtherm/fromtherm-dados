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
#  CSS GLOBAL (correção do "0" e estilo dos cards)
# =========================
st.markdown(
    """
    <style>
    /* REMOÇÃO FINAL DO "0" TEIMOSO (seletor específico para o botão de menu do Streamlit) */
    /* Este seletor mira no botão de menu que contém o "0" e o esconde */
    button[data-testid="stSidebarNavToggle"] {
        display: none !important;
    }
    /* Outras tentativas genéricas para garantir que nenhum span pequeno apareça */
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
DADOS_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"


# --- Função para listar arquivos CSV localmente ---
@st.cache_data(ttl=10)  # TTL curto para ver arquivos novos rapidamente
def listar_arquivos_csv():
    """
    Lista todos os arquivos .csv na pasta DADOS_DIR
    e extrai informações básicas do nome:
    historico_L1_20260303_2140_OP1234_FT185.csv
    Se a data não puder ser parseada, usa datetime.min.date() para evitar None.
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        linha = ""
        data = datetime.min.date() # Valor padrão para evitar None
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
            # Se houver erro, data já é datetime.min.date()
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
# Garante que 'data' sempre será um objeto date válido devido à correção em listar_arquivos_csv
arquivo_mais_recente = max(
    todos_arquivos_info,
    key=lambda x: (x["data"], x["hora"] or ""), # 'hora' pode ser string vazia, mas não None
)

# =====================================================
#  PAINEL: Última leitura registrada (cards com ícones)
# =====================================================
st.markdown("### Última Leitura Registrada")

try:
    df_recente = carregar_csv_caminho(arquivo_mais_recente["caminho"])
    ultima_linha = df_recente.iloc[-1] # Pega a última linha do arquivo mais recente

    # Mapeamento de meses para exibição
    mes_label_map = {
        1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
        5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
        9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
    }

    st.markdown(
        f"**Modelo:** {arquivo_mais_recente['modelo'] or 'N/D'} | "
        f"**OP:** {arquivo_mais_recente['operacao'] or 'N/D'} | "
        f"**Data:** {arquivo_mais_recente['data'].strftime('%d/%m/%Y')} | "
        f"**Hora:** {arquivo_mais_recente['hora'] or 'N/D'}"
    )

    st.markdown("---") # Separador visual

    col1, col2, col3 = st.columns(3)

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
              <i class="bi bi-arrow-up-circle ft-card-icon red"></i>
              <div class="ft-card-content">
                <p class="ft-card-title">T-Saída (°C)</p>
                <p class="ft-card-value">{ultima_linha['Saída']}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="ft-card">
              <i class="bi bi-arrow-down-up ft-card-icon"></i>
              <div class="ft-card-content">
                <p class="ft-card-title">DIF (ΔT) (°C)</p>
                <p class="ft-card-value">{ultima_linha['ΔT']}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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

    with col3:
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

except Exception as e:
    st.error(f"Não foi possível gerar o painel da última leitura: {e}")
    st.info("Verifique se o formato do CSV está conforme o padrão esperado e se há arquivos na pasta.")

st.markdown("---") # Separador visual

# =====================================================
#  ABAS: Históricos e Planilhas | Crie Seu Gráfico
# =====================================================
tab1, tab2 = st.tabs(["Históricos e Planilhas", "Crie Seu Gráfico"])

with tab1:
    st.markdown("### Históricos Disponíveis")

    # Mapeamento de meses para exibição
    mes_label_map = {
        1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
        5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
        9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
    }

    # Filtros
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

    with col_filtro1:
        modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"])))
        modelo_selecionado = st.selectbox(
            "Filtrar por Modelo:",
            ["Todos"] + modelos_disponiveis,
            key="filtro_modelo",
        )

    with col_filtro2:
        anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"])), reverse=True)
        ano_selecionado = st.selectbox(
            "Filtrar por Ano:",
            ["Todos"] + anos_disponiveis,
            key="filtro_ano",
        )

    with col_filtro3:
        # Filtra meses com base no modelo e ano selecionados
        arquivos_filtrados_para_mes = todos_arquivos_info
        if modelo_selecionado != "Todos":
            arquivos_filtrados_para_mes = [a for a in arquivos_filtrados_para_mes if a["modelo"] == modelo_selecionado]
        if ano_selecionado != "Todos":
            arquivos_filtrados_para_mes = [a for a in arquivos_filtrados_para_mes if a["ano"] == ano_selecionado]

        meses_disponiveis = sorted(list(set(a["mes"] for a in arquivos_filtrados_para_mes if a["mes"])))
        meses_labels = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis] if meses_disponiveis else ["Todos"]

        mes_selecionado_label = st.selectbox(
            "Filtrar por Mês:",
            meses_labels,
            key="filtro_mes",
        )
        mes_selecionado = None
        if mes_selecionado_label != "Todos":
            mes_selecionado = int(mes_selecionado_label.split(" ")[0])

    # Aplica os filtros
    arquivos_exibidos = todos_arquivos_info
    if modelo_selecionado != "Todos":
        arquivos_exibidos = [a for a in arquivos_exibidos if a["modelo"] == modelo_selecionado]
    if ano_selecionado != "Todos":
        arquivos_exibidos = [a for a in arquivos_exibidos if a["ano"] == ano_selecionado]
    if mes_selecionado is not None:
        arquivos_exibidos = [a for a in arquivos_exibidos if a["mes"] == mes_selecionado]

    # Ordena por data e hora (mais recente primeiro)
    arquivos_exibidos = sorted(
        arquivos_exibidos,
        key=lambda x: (x["data"], x["hora"] or ""),
        reverse=True,
    )

    if not arquivos_exibidos:
        st.info("Nenhum histórico encontrado com os filtros aplicados.")
    else:
        # Exibir e permitir download
        for arquivo in arquivos_exibidos:
            col_info, col_download = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f"**Modelo:** {arquivo['modelo'] or 'N/D'} | "
                    f"**OP:** {arquivo['operacao'] or 'N/D'} | "
                    f"**Data:** {arquivo['data'].strftime('%d/%m/%Y')} | "
                    f"**Hora:** {arquivo['hora'] or 'N/D'}"
                )
                st.markdown(f"Arquivo: `{arquivo['nome_arquivo']}`")
            with col_download:
                try:
                    df_preview = carregar_csv_caminho(arquivo["caminho"])
                    csv_data = df_preview.to_csv(index=False, sep=';').encode('utf-8')
                    st.download_button(
                        label="Baixar CSV",
                        data=csv_data,
                        file_name=f"{arquivo['nome_arquivo']}",
                        mime="text/csv",
                        key=f"download_{arquivo['nome_arquivo']}",
                    )
                except Exception as e:
                    st.error(f"Erro ao preparar download de {arquivo['nome_arquivo']}: {e}")
            st.markdown("---")

with tab2:
    st.markdown("### Crie Seu Gráfico Personalizado")

    # Mapeamento de meses para exibição
    mes_label_map = {
        1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
        5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
        9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
    }

    # Filtros para o gráfico
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