import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from io import BytesIO, StringIO
import plotly.express as px
import re

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
    e extrai informações básicas do nome.
    Tenta ser flexível com o padrão de nome.
    """
    if not os.path.exists(DADOS_DIR):
        return []

    arquivos = glob.glob(os.path.join(DADOS_DIR, "*.csv"))
    info_arquivos = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)

        # Padrão mais flexível para capturar OP e o final do nome
        # Ex: historico_L1_20260308_0939_OP987_FTA987BR.csv
        # Ex: historico_L1_20260306_1717_OP9090_FT55L.csv
        match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d+)_([a-zA-Z0-9]+)\.csv", nome)

        data, ano, mes, hora, operacao, modelo = None, None, None, None, "N/D", "N/D"

        if match:
            year_str, month_str, day_str, time_str, operacao, modelo = match.groups()

            try:
                data = datetime.strptime(f"{year_str}{month_str}{day_str}", "%Y%m%d").date()
                ano = int(year_str)
                mes = int(month_str)
                hora = f"{time_str[:2]}:{time_str[2:]}"
            except ValueError:
                pass # Se a conversão de data/hora falhar, mantém como None

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
        # Lendo o arquivo como texto para pré-processamento
        with open(caminho, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filtrar a linha '---' e remover espaços extras e o caractere '|'
        processed_lines = []
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith('|') and stripped_line.endswith('|'):
                # Ignora a linha de separação '---'
                if '---' in stripped_line:
                    continue
                # Remove o primeiro e último '|', e divide pelo '|' restante
                parts = [p.strip() for p in stripped_line[1:-1].split('|')]
                # Filtra partes vazias que podem surgir de múltiplos delimitadores
                cleaned_parts = [p for p in parts if p]
                processed_lines.append(','.join(cleaned_parts))
            else:
                # Se a linha não estiver no formato '| ... |', tenta adicionar como está
                processed_lines.append(stripped_line)

        # Converte a lista de linhas processadas em um objeto StringIO para o pandas ler
        data_io = StringIO('\n'.join(processed_lines))

        # Agora, o pandas pode ler com vírgula como separador
        df = pd.read_csv(data_io, sep=',', decimal='.', encoding='utf-8')

        # Limpeza de espaços nos nomes das colunas lidas
        df.columns = [col.strip() for col in df.columns]

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

        # Converter colunas numéricas (exceto DateTime)
        for col in df.columns:
            if col != 'DateTime': # Não tenta converter a coluna de data/hora
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except ValueError:
                    pass # Se não for numérico, mantém o tipo original

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

# Mapeamento de números de mês para nomes (para exibição nos filtros)
mes_label_map = {
    1: "01 Janeiro", 2: "02 Fevereiro", 3: "03 Março", 4: "04 Abril",
    5: "05 Maio", 6: "06 Junho", 7: "07 Julho", 8: "08 Agosto",
    9: "09 Setembro", 10: "10 Outubro", 11: "11 Novembro", 12: "12 Dezembro"
}

# Coleta de opções para os filtros (a partir de todos os arquivos)
modelos_disponiveis = sorted(list(set(a["modelo"] for a in todos_arquivos_info if a["modelo"] and a["modelo"] != "N/D")))
anos_disponiveis = sorted(list(set(a["ano"] for a in todos_arquivos_info if a["ano"] is not None)))
meses_disponiveis = sorted(list(set(a["mes"] for a in todos_arquivos_info if a["mes"] is not None)))
operacoes_disponiveis = sorted(list(set(a["operacao"] for a in todos_arquivos_info if a["operacao"] and a["operacao"] != "N/D")))

# Adiciona "Todos" como opção para os filtros
modelos_filtro = ["Todos"] + modelos_disponiveis
anos_filtro = ["Todos"] + anos_disponiveis
meses_filtro = ["Todos"] + [mes_label_map[m] for m in meses_disponiveis]
operacoes_filtro = ["Todos"] + operacoes_disponiveis

# Filtros na sidebar
st.sidebar.header("Filtros de Arquivos") # Título do filtro
selected_modelo = st.sidebar.selectbox("Modelo (ex: FTA987BR):", modelos_filtro)
selected_ano = st.sidebar.selectbox("Ano:", anos_filtro)
selected_mes_label = st.sidebar.selectbox("Mês:", meses_filtro)
selected_operacao = st.sidebar.selectbox("Operação (ex: OP987_FTA987BR):", operacoes_filtro)

# Converte o label do mês de volta para número
selected_mes = None
if selected_mes_label != "Todos":
    selected_mes = int(selected_mes_label.split(" ")[0])

# Aplica os filtros
arquivos_filtrados = [
    a for a in todos_arquivos_info
    if (selected_modelo == "Todos" or a["modelo"] == selected_modelo) and
       (selected_ano == "Todos" or a["ano"] == selected_ano) and
       (selected_mes is None or a["mes"] == selected_mes) and
       (selected_operacao == "Todos" or a["operacao"] == selected_operacao)
]

# =====================================================
#  ÁREA PRINCIPAL: Lista de Arquivos Disponíveis
# =====================================================
st.markdown("---") # Linha divisória
st.subheader("Arquivos Disponíveis")

if not arquivos_filtrados:
    st.info("Nenhum arquivo encontrado com os filtros selecionados.")
else:
    # Armazena o arquivo selecionado na session_state
    if 'selected_file_path' not in st.session_state:
        st.session_state.selected_file_path = None

    # Cria colunas para os botões para melhor organização visual
    cols_per_row = 3 # Quantos botões por linha
    cols = st.columns(cols_per_row)

    for i, arquivo in enumerate(arquivos_filtrados):
        with cols[i % cols_per_row]: # Distribui os botões nas colunas
            # Aqui está a mudança CRÍTICA:
            # Se as informações foram extraídas, usa-as. Caso contrário, usa o nome original do arquivo.
            if arquivo['modelo'] != "N/D" and arquivo['operacao'] != "N/D" and arquivo['data'] and arquivo['hora']:
                data_str = arquivo['data'].strftime('%d/%m/%Y')
                hora_str = arquivo['hora']
                display_name = f"{arquivo['modelo']} - {arquivo['operacao']} - {data_str} {hora_str}"
            else:
                # Se alguma informação estiver faltando, mostra o nome completo do arquivo
                display_name = arquivo['nome_arquivo']

            if st.button(display_name, key=f"file_button_{i}", use_container_width=True):
                st.session_state.selected_file_path = arquivo['caminho']
                st.rerun() # Força a atualização para mostrar o arquivo selecionado

# =====================================================
#  ÁREA PRINCIPAL: Exibição do arquivo selecionado
# =====================================================

if st.session_state.selected_file_path:
    selected_file_path = st.session_state.selected_file_path
    selected_filename = os.path.basename(selected_file_path)

    st.markdown("---") # Linha divisória
    st.subheader(f"Visualização de Dados: {selected_filename}")

    df_dados = carregar_csv_caminho(selected_file_path)

    if not df_dados.empty:
        st.dataframe(df_dados, use_container_width=True)

        # Botão de download do Excel para o arquivo selecionado
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_dados.to_excel(writer, index=False, sheet_name='Dados')

            # Ajusta a largura das colunas no Excel
            workbook = writer.book
            worksheet = writer.sheets['Dados']
            for col_idx, col_name in enumerate(df_dados.columns):
                if "kW" in col_name:
                    worksheet.set_column(col_idx, col_idx, 15)
                elif "Ambiente" in col_name or "Corrente" in col_name:
                    worksheet.set_column(col_idx, col_idx, 10)
                elif "Date" in col_name or "DateTime" in col_name:
                    worksheet.set_column(col_idx, col_idx, 18) # Mais largo para DateTime
                elif "Time" in col_name:
                    worksheet.set_column(col_idx, col_idx, 10)
                else:
                    worksheet.set_column(col_idx, col_idx, 12)

        output_excel.seek(0)

        # Gera o nome do arquivo para download
        parsed_info = next((a for a in todos_arquivos_info if a['caminho'] == selected_file_path), None)

        # Usa o nome original do arquivo se as informações parseadas não estiverem completas
        if parsed_info and parsed_info['modelo'] != "N/D" and parsed_info['operacao'] != "N/D" and parsed_info['data'] and parsed_info['hora']:
            data_nome = parsed_info['data'].strftime('%Y%m%d')
            hora_nome = parsed_info['hora'].replace(':', '')
            modelo_nome = parsed_info['modelo']
            operacao_nome = parsed_info['operacao']
            excel_file_name = f"Maquina_{modelo_nome}_{operacao_nome}_{data_nome}_{hora_nome}.xlsx"
        else:
            excel_file_name = selected_filename.replace('.csv', '.xlsx') # Usa o nome original do CSV, mas com extensão .xlsx

        st.download_button(
            label="Exportar para Excel",
            data=output_excel,
            file_name=excel_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"excel_download_{selected_filename}",
        )

        # --- Seção de Gráficos (reintroduzida aqui, mas pode ser movida para uma aba se preferir) ---
        st.markdown("---")
        st.subheader("Crie Seu Gráfico")

        # Usar o DataFrame do arquivo selecionado para gerar o gráfico
        df_graf = df_dados.copy()

        if not df_graf.empty and 'DateTime' in df_graf.columns:
            st.markdown("### Variáveis para o gráfico")

            # Usar os nomes de colunas do DataFrame carregado, exceto 'DateTime'
            variaveis_opcoes = [col for col in df_graf.columns if col != 'DateTime']

            vars_selecionadas = st.multiselect(
                "Selecione uma ou mais variáveis:",
                variaveis_opcoes,
                default=["Ambiente", "Entrada", "Saída"] if all(v in variaveis_opcoes for v in ["Ambiente", "Entrada", "Saída"]) else variaveis_opcoes[:3],
                key=f"graf_vars_{selected_filename}"
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
                    title=f"Gráfico - {selected_filename}",
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
            st.warning("Não há dados válidos ou coluna 'DateTime' para gerar o gráfico.")

    else:
        st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo na lista acima para visualizar os dados e gerar gráficos.")
