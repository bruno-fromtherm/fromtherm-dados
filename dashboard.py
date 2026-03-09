import streamlit as st
import pandas as pd
import os
import re # Para expressões regulares, útil para parsear nomes de arquivos
import plotly.express as px # Para gráficos interativos
from io import BytesIO # Para downloads de Excel

# --- Configurações da Página Streamlit ---
st.set_page_config(layout="wide", page_title="Dashboard Fromtherm")

# Título Principal do Dashboard
st.title("Dashboard de Histórico de Dados Fromtherm")

# Caminho para a pasta onde os arquivos CSV estão no repositório GitHub
DATA_PATH = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# --- Função para parsear o nome do arquivo e extrair informações ---
def parse_filename(filename):
    # Exemplo de nome: historico_L1_20260305_1848_OP555_195HH.csv
    match = re.match(r"historico_L1_(\d{4})(\d{2})(\d{2})_(\d{4})_(OP\d{3})_(\d{3}HH)\.csv", filename)
    if match:
        year, month, day, time, modelo, operacao = match.groups()
        full_date = f"{day}/{month}/{year}"
        return {
            "filename": filename,
            "modelo": modelo,
            "ano": year,
            "mes": month,
            "dia": day,
            "data_completa": full_date,
            "hora": time,
            "operacao": operacao # Adicionando a operação para o filtro
        }
    return None

# --- Função para carregar e processar os dados (com tratamento aprimorado) ---
@st.cache_data
def load_data(file_path):
    try:
        # Tenta ler o CSV com separador ';' e decimal ','
        df = pd.read_csv(file_path, sep=';', decimal=',', encoding='utf-8')

        # Limpeza e conversão de tipos
        for col in df.columns:
            # Remover aspas duplas de todas as colunas (se existirem)
            if df[col].dtype == 'object': # Se a coluna for de texto
                df[col] = df[col].astype(str).str.replace('"', '', regex=False)

            # Tentar converter para numérico (float)
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except ValueError:
                pass # Se não for numérico, mantém o tipo original

            # Tentar converter para datetime (para colunas de data/hora)
            if 'data' in col.lower() or 'hora' in col.lower() or 'timestamp' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce', format='%d/%m/%Y %H:%M:%S') # Ajuste o formato se necessário
                except Exception:
                    pass

        # Renomear colunas para facilitar o uso (exemplo, ajuste conforme seus dados reais)
        # st.write(df.columns) # Descomente para ver os nomes das colunas e ajustar
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '', regex=False)

        # Exemplo de renomeação específica se souber os nomes exatos
        # df = df.rename(columns={'coluna_antiga': 'coluna_nova'})

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

# --- Sidebar para Filtros e Seleção de Arquivos ---
st.sidebar.header("Filtros de Arquivos CSV")

if not files_df.empty:
    # Filtros dinâmicos
    modelos_unicos = sorted(files_df['modelo'].unique())
    anos_unicos = sorted(files_df['ano'].unique(), reverse=True)
    meses_unicos = sorted(files_df['mes'].unique())
    dias_unicos = sorted(files_df['dia'].unique())
    operacoes_unicas = sorted(files_df['operacao'].unique())

    selected_modelo = st.sidebar.selectbox("Filtrar por Modelo:", ["Todos"] + modelos_unicos)
    selected_ano = st.sidebar.selectbox("Filtrar por Ano:", ["Todos"] + anos_unicos)
    selected_mes = st.sidebar.selectbox("Filtrar por Mês:", ["Todos"] + meses_unicos)
    selected_dia = st.sidebar.selectbox("Filtrar por Dia:", ["Todos"] + dias_unicos)
    selected_operacao = st.sidebar.selectbox("Filtrar por Operação:", ["Todos"] + operacoes_unicas)

    # Aplicar filtros
    filtered_files_df = files_df.copy()
    if selected_modelo != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['modelo'] == selected_modelo]
    if selected_ano != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['ano'] == selected_ano]
    if selected_mes != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['mes'] == selected_mes]
    if selected_dia != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['dia'] == selected_dia]
    if selected_operacao != "Todos":
        filtered_files_df = filtered_files_df[filtered_files_df['operacao'] == selected_operacao]

    # Seletor final de arquivo após filtros
    if not filtered_files_df.empty:
        selected_filename = st.sidebar.selectbox(
            "Selecione um arquivo CSV para visualizar:",
            filtered_files_df['filename'].tolist(),
            format_func=lambda x: f"{parse_filename(x)['data_completa']} - {parse_filename(x)['modelo']} - {parse_filename(x)['operacao']}"
        )
    else:
        st.sidebar.info("Nenhum arquivo encontrado com os filtros selecionados.")
        selected_filename = None
else:
    st.sidebar.info("Nenhum arquivo CSV encontrado na pasta especificada.")
    selected_filename = None

# --- Conteúdo Principal do Dashboard ---
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
                download_base_name = f"Maquina_{parsed_info['modelo']}_{parsed_info['operacao']}_{parsed_info['data_completa'].replace('/', '')}_{parsed_info['hora']}"
                display_name = f"Maquina_{parsed_info['modelo']}_{parsed_info['operacao']}_{parsed_info['data_completa']}_{parsed_info['hora']}hs"
            else:
                download_base_name = "dados_fromtherm"
                display_name = "Dados Fromtherm"

            # Download PDF (usando pandas.to_html e uma biblioteca para PDF, ou um link para o Streamlit Docs)
            # Streamlit não tem um gerador de PDF nativo. Para PDF, geralmente se usa uma biblioteca como ReportLab ou FPDF,
            # ou se converte HTML para PDF. Isso é mais complexo para um dashboard simples.
            # Por enquanto, vamos focar em Excel e deixar o PDF como um próximo passo mais avançado.
            # st.button("Baixar em PDF (Funcionalidade em desenvolvimento)")

            # Download Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
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
            datetime_cols = df.select_dtypes(include=['datetime64']).columns
            numeric_cols = df.select_dtypes(include=['number']).columns

            if datetime_cols.empty:
                st.warning("Nenhuma coluna de data/hora encontrada para o eixo X do gráfico. Verifique o formato dos seus dados.")
                x_axis_options = df.columns.tolist() # Usa todas as colunas como opção
            else:
                x_axis_options = datetime_cols.tolist() # Prefere colunas de data/hora para o eixo X

            if numeric_cols.empty:
                st.warning("Nenhuma coluna numérica encontrada para o eixo Y do gráfico. Verifique o tratamento dos dados.")
                st.info("Certifique-se de que os valores numéricos não estão entre aspas duplas e que o separador decimal está correto.")
            else:
                # Seletores para o gráfico
                st.write("Selecione as opções para o seu gráfico:")

                # Selecionar Modelo e Operação (já filtrados pelo sidebar, mas podemos exibir aqui)
                st.info(f"Modelo Selecionado: **{parsed_info['modelo']}** | Operação Selecionada: **{parsed_info['operacao']}**")

                col_x, col_y = st.columns(2)
                with col_x:
                    x_axis = st.selectbox("Selecione a coluna para o Eixo X:", x_axis_options)
                with col_y:
                    y_axes = st.multiselect(
                        "Selecione as colunas para o Eixo Y (múltipla seleção):",
                        numeric_cols.tolist(),
                        default=numeric_cols.tolist()[:2] if len(numeric_cols) >= 2 else numeric_cols.tolist() # Seleciona as 2 primeiras por padrão
                    )

                if x_axis and y_axes:
                    st.write("---")
                    st.write("### Gráfico Gerado")

                    # Cria o gráfico de linha interativo com Plotly
                    fig = px.line(df, x=x_axis, y=y_axes, title=f"Dados de {selected_filename}")
                    fig.update_layout(hovermode="x unified") # Melhora a interatividade ao passar o mouse

                    # Exibe o gráfico
                    st.plotly_chart(fig, use_container_width=True)

                    # Funcionalidades adicionais do gráfico (download, expansão)
                    st.info("O gráfico acima já possui funcionalidades de zoom, pan e download de imagem (câmera no canto superior direito) nativas do Plotly.")
                    # Para expansão, o use_container_width=True já ajuda. Um botão de "tela cheia" seria mais complexo.

                    # Botão de compartilhamento via WhatsApp (exemplo, requer mais lógica para dados dinâmicos)
                    # st.button("Compartilhar Gráfico via WhatsApp (Funcionalidade em desenvolvimento)")

                else:
                    st.warning("Selecione pelo menos uma coluna para o Eixo X e uma para o Eixo Y para gerar o gráfico.")
    else:
        st.warning("Não foi possível carregar ou processar os dados do arquivo selecionado. Verifique o formato do CSV.")
else:
    st.info("Por favor, selecione um arquivo CSV no menu lateral para começar.")
