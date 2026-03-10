import streamlit as st
import pandas as pd
import os
import re
import plotly.express as px
from io import BytesIO

# --- Configurações da Página Streamlit ---
st.set_page_config(layout="wide", page_title="Dashboard Fromtherm")

# Título Principal do Dashboard
st.title("Dashboard de Histórico de Dados Fromtherm")

# Caminho para a pasta onde os arquivos CSV estão no repositório GitHub
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# --- Função para parsear o nome do arquivo e extrair informações ---
def parse_filename(filename):
    # Novo padrão de nome: historico_L1_20260308_0939_OP987_FTA987BR.csv
    # Captura Ano, Mês, Dia, Hora, Modelo (OPXXX), e a Máquina (FTAXXXBR)
    match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d{3})_(FTA\d{3}BR)\.csv", filename)
    if match:
        year, month, day, time, modelo, maquina = match.groups()
        full_date = f"{day}/{month}/{year}"
        return {
            "filename": filename,
            "modelo": modelo,
            "maquina": maquina, # Adicionado campo para a máquina
            "ano": year,
            "mes": month,
            "dia": day,
            "data_completa": full_date,
            "hora": time,
            "operacao": f"{modelo}_{maquina}" # Combinando modelo e máquina para 'operacao'
        }
    return None

# --- Função para carregar e processar os dados (com tratamento aprimorado) ---
@st.cache_data
def load_data(file_path):
    try:
        # Ajustado para ler com separador de espaço (ou tab) e decimal '.'
        # O 'sep=r'\s+'' usa regex para um ou mais espaços/tabs como separador
        df = pd.read_csv(file_path, sep=r'\s+', decimal='.', encoding='utf-8')

        # Limpeza e conversão de tipos
        for col in df.columns:
            # Tentar converter para numérico (float)
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except ValueError:
                pass # Se não for numérico, mantém o tipo original

        # Combinar 'Date' e 'Time' em uma única coluna de datetime
        if 'Date' in df.columns and 'Time' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce', format='%Y/%m/%d %H:%M:%S')
            df = df.drop(columns=['Date', 'Time']) # Remove as colunas originais
            # Mover 'Timestamp' para o início do DataFrame
            cols = ['Timestamp'] + [col for col in df.columns if col != 'Timestamp']
            df = df[cols]

        # Renomear colunas para facilitar o uso (exemplo, ajuste conforme seus dados reais)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '', regex=False).str.replace('/', '', regex=False)

        return df
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo {file_path}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# --- Listar e parsear arquivos CSV ---
all_files_info = []
try:
    if os.path.exists(DATA_PATH):
        csv_filenames = [f for f in os.listdir(DATA_PATH) if f.endswith('.csv')]
        for filename in csv_filenames:
            info = parse_filename(filename)
            if info:
                all_files_info.append(info)
        all_files_info.sort(key=lambda x: x['filename'], reverse=True) # Ordena por nome (mais recente primeiro)
    else:
        st.warning(f"O diretório '{DATA_PATH}' não foi encontrado. Verifique o caminho no seu repositório.")
except Exception as e:
    st.error(f"Erro ao listar arquivos: {e}")

# Criar um DataFrame com as informações dos arquivos para facilitar a filtragem
files_df = pd.DataFrame(all_files_info)

# --- Sidebar para Filtros ---
st.sidebar.header("Filtros de Arquivos") # Título alterado

# Variável de estado para armazenar o arquivo selecionado para visualização
if 'selected_file_for_display' not in st.session_state:
    st.session_state.selected_file_for_display = None

if not files_df.empty:
    # Filtros dinâmicos
    modelos_unicos = sorted(files_df['modelo'].unique())
    maquinas_unicas = sorted(files_df['maquina'].unique())
    anos_unicos = sorted(files_df['ano'].unique(), reverse=True)
    meses_unicos = sorted(files_df['mes'].unique())
    dias_unicos = sorted(files_df['dia'].unique())

    selected_modelo = st.sidebar.selectbox("Modelo (ex: OP987):", ["Todos"] + modelos_unicos)
    selected_maquina = st.sidebar.selectbox("Máquina (ex: FTA987BR):", ["Todos"] + maquinas_unicas)
    selected_ano = st.sidebar.selectbox("Ano:", ["Todos"] + anos_unicos)
    selected_mes = st.sidebar.selectbox("Mês:", ["Todos"] + meses_unicos)
    selected_dia = st.sidebar.selectbox("Dia:", ["Todos"] + dias_unicos)

    # Aplicar filtros
    filtered_files_df = files_df.copy()
    if selected_modelo != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['modelo'] == selected_modelo]
    if selected_maquina != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['maquina'] == selected_maquina]
    if selected_ano != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['ano'] == selected_ano]
    if selected_mes != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['mes'] == selected_mes]
    if selected_dia != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['dia'] == selected_dia]

    # Exibir arquivos filtrados para seleção
    st.sidebar.markdown("---")
    st.sidebar.subheader("Arquivos Disponíveis")

    if not filtered_files_df.empty:
        for index, row in filtered_files_df.iterrows():
            display_text = f"{row['data_completa']} - {row['modelo']} - {row['maquina']}"
            if st.sidebar.button(display_text, key=row['filename']):
                st.session_state.selected_file_for_display = row['filename']
                st.rerun() # Força a atualização para mostrar o arquivo selecionado
    else:
        st.sidebar.info("Nenhum arquivo encontrado com os filtros selecionados.")
else:
    st.sidebar.info("Nenhum arquivo CSV encontrado na pasta especificada.")

# --- Conteúdo Principal do Dashboard ---
selected_filename = st.session_state.selected_file_for_display

if selected_filename:
    file_path = os.path.join(DATA_PATH, selected_filename)
    df = load_data(file_path)

    if not df.empty:
        st.subheader(f"Dados do arquivo: {selected_filename}")

        # --- Abas para organizar o conteúdo ---
        tab1, tab2 = st.tabs(["Visualização de Dados", "Crie Seu Gráfico"])

        with tab1:
            st.write("### Tabela Completa")
            st.dataframe(df, use_container_width=True) # Exibe a tabela completa

            # --- Botões de Download ---
            st.write("### Opções de Download")

            # Nome base para download
            parsed_info = parse_filename(selected_filename)
            if parsed_info:
                # Formato: Maquina_FTA987BR_OP987_08/03/2026_09:39hs
                display_name = f"Maquina_{parsed_info['maquina']}_{parsed_info['modelo']}_{parsed_info['data_completa']}_{parsed_info['hora']}hs"
            else:
                display_name = "Dados Fromtherm"

            # Download Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Dados')
            excel_buffer.seek(0)
            st.download_button(
                label="Baixar em Excel",
                data=excel_buffer,
                file_name=f"{display_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with tab2:
            st.write("### Crie Seu Gráfico")

            # Identificar colunas de data/hora e numéricas
            datetime_cols = ['timestamp'] if 'timestamp' in df.columns else []
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if 'timestamp' in numeric_cols: # Garante que timestamp não seja opção para eixo Y
                numeric_cols.remove('timestamp')

            if not datetime_cols:
                st.warning("Nenhuma coluna de data/hora ('Timestamp') encontrada para o eixo X do gráfico. Verifique o formato dos seus dados.")
                x_axis_options = df.columns.tolist() # Usa todas as colunas como opção
            else:
                x_axis_options = datetime_cols # Prefere 'Timestamp' para o eixo X

            if not numeric_cols:
                st.warning("Nenhuma coluna numérica encontrada para o eixo Y do gráfico. Verifique o tratamento dos dados.")
                st.info("Certifique-se de que os valores numéricos estão sendo lidos corretamente.")
            else:
                # Seletores para o gráfico
                st.write("Selecione as opções para o seu gráfico:")

                st.info(f"Modelo Selecionado: **{parsed_info['modelo']}** | Máquina Selecionada: **{parsed_info['maquina']}**")

                col_x, col_y = st.columns(2)
                with col_x:
                    x_axis = st.selectbox("Selecione a coluna para o Eixo X:", x_axis_options)
                with col_y:
                    y_axes = st.multiselect(
                        "Selecione as colunas para o Eixo Y (múltipla seleção):",
                        numeric_cols,
                        default=numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols # Seleciona as 2 primeiras por padrão
                    )

                if x_axis and y_axes:
                    st.write("---")
                    st.write("### Gráfico Gerado")

                    fig = px.line(df, x=x_axis, y=y_axes, title=f"Dados de {selected_filename}")
                    fig.update_layout(hovermode="x unified")

                    st.plotly_chart(fig, use_container_width=True)

                    st.info("O gráfico acima já possui funcionalidades de zoom, pan e download de imagem (câmera no canto superior direito) nativas do Plotly.")
                else:
                    st.warning("Selecione pelo menos uma coluna para o Eixo X e uma para o Eixo Y para gerar o gráfico.")
    else:
        st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo no menu lateral para começar.")
