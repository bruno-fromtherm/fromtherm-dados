import streamlit as st
import pandas as pd
import os
import plotly.express as px
from fpdf import FPDF
import base64
from io import BytesIO

# --- CONFIGURAÇÕES ---
# Pasta onde os arquivos CSV estão localizados (relativo ao dashboard.py)
DADOS_DIR = "dados"

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def load_data(file_path):
    """Carrega dados de um arquivo CSV."""
    try:
        df = pd.read_csv(file_path, sep=';', decimal=',')
        # Tenta converter colunas de data/hora
        for col in df.columns:
            if 'data' in col.lower() or 'hora' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo {os.path.basename(file_path)}: {e}")
        return pd.DataFrame()

def get_csv_files(directory):
    """Retorna uma lista de caminhos completos para arquivos CSV em um diretório."""
    csv_files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(directory, file))
    return csv_files

def create_download_link(val, filename):
    b64 = base64.b64encode(val)  # val (bytes)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">Download {filename}</a>'

# --- LAYOUT DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Dashboard FROMTHERM IHM")

st.title("📊 Dashboard de Históricos FROMTHERM IHM")

# --- CARREGAR ARQUIVOS ---
csv_files = get_csv_files(DADOS_DIR)

if not csv_files:
    st.warning(f"Nenhum arquivo CSV encontrado na pasta '{DADOS_DIR}'. Por favor, adicione arquivos CSV para visualização.")
else:
    # Seleção de arquivo
    selected_file = st.selectbox("Selecione um arquivo CSV para analisar:", csv_files, format_func=os.path.basename)

    if selected_file:
        df = load_data(selected_file)

        if not df.empty:
            st.subheader(f"Visualizando: {os.path.basename(selected_file)}")
            st.dataframe(df)

            # --- FILTROS ---
            st.sidebar.header("Filtros")
            all_columns = df.columns.tolist()

            # Filtro de data (se houver colunas de data)
            date_cols = [col for col in all_columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            if date_cols:
                selected_date_col = st.sidebar.selectbox("Coluna de Data/Hora para filtrar:", date_cols)
                min_date = df[selected_date_col].min().to_pydatetime().date() if not df[selected_date_col].min() is pd.NaT else None
                max_date = df[selected_date_col].max().to_pydatetime().date() if not df[selected_date_col].max() is pd.NaT else None

                if min_date and max_date:
                    date_range = st.sidebar.slider(
                        "Selecione o intervalo de datas:",
                        min_value=min_date,
                        max_value=max_date,
                        value=(min_date, max_date)
                    )
                    df_filtered = df[(df[selected_date_col].dt.date >= date_range[0]) & (df[selected_date_col].dt.date <= date_range[1])]
                else:
                    df_filtered = df.copy()
            else:
                df_filtered = df.copy()

            # Filtro de texto/número para outras colunas
            st.sidebar.subheader("Filtros por Coluna")
            for col in all_columns:
                if col not in date_cols:
                    unique_values = df_filtered[col].unique()
                    if len(unique_values) < 50 and pd.api.types.is_string_dtype(df_filtered[col]): # Selectbox para poucas opções
                        selected_values = st.sidebar.multiselect(f"Filtrar {col}:", unique_values, default=unique_values)
                        df_filtered = df_filtered[df_filtered[col].isin(selected_values)]
                    elif pd.api.types.is_numeric_dtype(df_filtered[col]): # Slider para números
                        min_val, max_val = df_filtered[col].min(), df_filtered[col].max()
                        num_range = st.sidebar.slider(f"Filtrar {col}:", min_val, max_val, (min_val, max_val))
                        df_filtered = df_filtered[(df_filtered[col] >= num_range[0]) & (df_filtered[col] <= num_range[1])]
                    # Adicione mais tipos de filtro conforme necessário

            st.subheader("Dados Filtrados")
            st.dataframe(df_filtered)

            # --- EXPORTAR DADOS ---
            st.sidebar.subheader("Exportar Dados")

            # Exportar para CSV
            csv_export = df_filtered.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
            st.sidebar.download_button(
                label="Download CSV Filtrado",
                data=csv_export,
                file_name=f"historico_filtrado_{os.path.basename(selected_file)}",
                mime="text/csv",
            )

            # Exportar para Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Dados')
            excel_buffer.seek(0)
            st.sidebar.download_button(
                label="Download Excel Filtrado",
                data=excel_buffer,
                file_name=f"historico_filtrado_{os.path.basename(selected_file).replace('.csv', '.xlsx')}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            # Exportar para PDF
            if st.sidebar.button("Download PDF Filtrado"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=10)

                # Cabeçalho
                pdf.cell(200, 10, txt=f"Relatório de Histórico - {os.path.basename(selected_file)}", ln=True, align='C')
                pdf.ln(5)

                # Adicionar dados da tabela
                # Simplificado para caber na página, pode precisar de mais lógica para tabelas grandes
                col_widths = [pdf.w / (len(df_filtered.columns) + 1)] * len(df_filtered.columns) # Distribui larguras

                # Cabeçalhos da tabela
                for i, col in enumerate(df_filtered.columns):
                    pdf.cell(col_widths[i], 10, str(col), border=1, align='C')
                pdf.ln()

                # Linhas da tabela
                for index, row in df_filtered.iterrows():
                    for i, col in enumerate(df_filtered.columns):
                        cell_text = str(row[col])
                        # Limita o tamanho do texto para caber na célula
                        if len(cell_text) > 20: # Exemplo: limita a 20 caracteres
                            cell_text = cell_text[:17] + "..."
                        pdf.cell(col_widths[i], 10, cell_text, border=1)
                    pdf.ln()

                pdf_output = pdf.output(dest='S').encode('latin-1') # Use latin-1 para compatibilidade
                st.sidebar.markdown(create_download_link(pdf_output, f"historico_filtrado_{os.path.basename(selected_file).replace('.csv', '.pdf')}"), unsafe_allow_html=True)

            # --- CRIAR GRÁFICOS ---
            st.subheader("Criar Gráficos")

            numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
            if not numeric_cols:
                st.warning("Nenhuma coluna numérica encontrada para criar gráficos.")
            else:
                x_axis = st.selectbox("Selecione a coluna para o Eixo X:", all_columns)
                y_axis = st.selectbox("Selecione a coluna para o Eixo Y:", numeric_cols)
                chart_type = st.selectbox("Selecione o Tipo de Gráfico:", ["Linha", "Barra", "Dispersão"])

                if x_axis and y_axis:
                    if chart_type == "Linha":
                        fig = px.line(df_filtered, x=x_axis, y=y_axis, title=f"{y_axis} ao longo de {x_axis}")
                    elif chart_type == "Barra":
                        fig = px.bar(df_filtered, x=x_axis, y=y_axis, title=f"{y_axis} por {x_axis}")
                    elif chart_type == "Dispersão":
                        fig = px.scatter(df_filtered, x=x_axis, y=y_axis, title=f"Dispersão de {y_axis} vs {x_axis}")

                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("O arquivo CSV selecionado está vazio ou não pôde ser carregado corretamente.")