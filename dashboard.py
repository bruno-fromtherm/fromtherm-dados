import streamlit as st
import pandas as pd
import os

# Título do Dashboard
st.title("Dashboard de Histórico de Dados Fromtherm")

# Caminho para a pasta onde os arquivos CSV estão no repositório GitHub
# No Streamlit Share, o repositório é clonado, então o caminho é relativo à raiz do seu projeto.
# Ajuste este caminho se a estrutura do seu repositório for diferente.
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# --- Função para carregar e processar os dados ---
@st.cache_data
def load_data(file_path):
    """
    Carrega um arquivo CSV e tenta inferir o formato da data/hora.
    """
    try:
        df = pd.read_csv(file_path, sep=';', decimal=',') # Assumindo separador ';' e decimal ','
        # Tenta converter colunas que parecem ser de data/hora
        for col in df.columns:
            if 'data' in col.lower() or 'hora' in col.lower() or 'timestamp' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    pass # Se não conseguir converter, mantém o tipo original
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {file_path}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# --- Listar arquivos CSV ---
try:
    # Verifica se o diretório existe antes de tentar listar
    if os.path.exists(DATA_PATH):
        csv_files = [f for f in os.listdir(DATA_PATH) if f.endswith('.csv')]
        csv_files.sort(reverse=True) # Mostra os arquivos mais recentes primeiro
    else:
        st.warning(f"O diretório '{DATA_PATH}' não foi encontrado. Verifique o caminho no seu repositório.")
        csv_files = []

    if not csv_files:
        st.info("Nenhum arquivo CSV encontrado na pasta especificada.")
    else:
        # Seletor para escolher o arquivo
        selected_file = st.selectbox("Selecione um arquivo CSV para visualizar:", csv_files)

        if selected_file:
            file_path = os.path.join(DATA_PATH, selected_file)
            df = load_data(file_path)

            if not df.empty:
                st.subheader(f"Dados do arquivo: {selected_file}")
                st.write(df) # Exibe a tabela completa

                # Exemplo de visualização simples: gráfico de linha para as primeiras colunas numéricas
                numeric_cols = df.select_dtypes(include=['number']).columns
                if not numeric_cols.empty:
                    st.subheader("Gráfico de Linha (Primeiras Colunas Numéricas)")
                    # Tenta usar uma coluna de data/hora como índice, se houver
                    datetime_cols = df.select_dtypes(include=['datetime64']).columns
                    if not datetime_cols.empty:
                        df_plot = df.set_index(datetime_cols[0])
                    else:
                        df_plot = df.copy()

                    # Seleciona as primeiras 5 colunas numéricas para o gráfico, se houver
                    cols_to_plot = numeric_cols[:5]
                    if not cols_to_plot.empty:
                        st.line_chart(df_plot[cols_to_plot])
                    else:
                        st.info("Nenhuma coluna numérica para plotar.")
                else:
                    st.info("Nenhuma coluna numérica encontrada para gerar gráficos.")
            else:
                st.warning("Não foi possível carregar os dados do arquivo selecionado.")

except Exception as e:
    st.error(f"Ocorreu um erro inesperado: {e}")
    st.info("Por favor, verifique se a estrutura de pastas no seu GitHub corresponde ao 'DATA_PATH' no código.")
