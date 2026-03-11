import os
import shutil
import subprocess
from datetime import datetime
import time

# --- CONFIGURAÇÕES ---
# Pasta onde a IHM salva os CSVs (conforme sua foto)
PASTA_ORIGEM_CSVS = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\FROMTHERM_IHM_UPLOADS\historico_L1\IP_registro192.168.2.150\datalog"

# Pasta DENTRO DO SEU REPOSITÓRIO GIT onde os CSVs devem ser copiados
# Certifique-se de que esta pasta existe no seu repositório GitHub!
PASTA_DESTINO_REPOSITORIO = r"C:\FROMTHERM_REPOS\fromtherm-dados\dados_brutos\historico_L1\IP_registro192.168.2.150\datalog"

# Caminho raiz do seu repositório Git
REPOSITORIO_GIT_PATH = r"C:\FROMTHERM_REPOS\fromtherm-dados"

# --- FUNÇÃO DE SINCRONIZAÇÃO ---
def sincronizar_e_enviar_para_github():
    log_messages = []
    def log(message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"[{timestamp}] {message}"
        print(full_message)
        log_messages.append(full_message)

    log("Iniciando sincronização de CSVs...")

    # 1. Verificar e criar pastas se necessário
    if not os.path.exists(PASTA_ORIGEM_CSVS):
        log(f"Erro: Pasta de origem não encontrada: {PASTA_ORIGEM_CSVS}")
        return False
    if not os.path.exists(PASTA_DESTINO_REPOSITORIO):
        os.makedirs(PASTA_DESTINO_REPOSITORIO)
        log(f"Criada pasta de destino no repositório: {PASTA_DESTINO_REPOSITORIO}")

    novos_arquivos_copiados = 0
    for filename in os.listdir(PASTA_ORIGEM_CSVS):
        if filename.endswith(".csv"):
            src_path = os.path.join(PASTA_ORIGEM_CSVS, filename)
            dst_path = os.path.join(PASTA_DESTINO_REPOSITORIO, filename)

            # Copia apenas se o arquivo não existe no destino ou se o arquivo de origem é mais recente
            if not os.path.exists(dst_path) or os.path.getmtime(src_path) > os.path.getmtime(dst_path):
                try:
                    shutil.copy2(src_path, dst_path)
                    log(f"Copiado/Atualizado: {filename}")
                    novos_arquivos_copiados += 1
                except Exception as e:
                    log(f"Erro ao copiar {filename}: {e}")
                    # Tentar novamente após um pequeno atraso se for um erro de acesso
                    time.sleep(1)
                    try:
                        shutil.copy2(src_path, dst_path)
                        log(f"Copiado/Atualizado (tentativa 2): {filename}")
                        novos_arquivos_copiados += 1
                    except Exception as e2:
                        log(f"Erro persistente ao copiar {filename}: {e2}")


    if novos_arquivos_copiados == 0:
        log("Nenhum novo arquivo CSV para copiar ou atualizar.")
        return True # Não houve erro, apenas nada para copiar

    # 2. Executar comandos Git
    try:
        # Navegar para a pasta raiz do repositório
        os.chdir(REPOSITORIO_GIT_PATH)
        log(f"Navegado para: {os.getcwd()}")

        # Adicionar todas as mudanças (incluindo os novos CSVs)
        result_add = subprocess.run(["git", "add", "."], capture_output=True, text=True, check=True)
        log(f"Git add . executado. Saída: {result_add.stdout.strip()}")

        # Fazer commit
        commit_message = f"Atualizacao automatica de dados CSV - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        result_commit = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True, check=True)
        log(f"Git commit executado: '{commit_message}'. Saída: {result_commit.stdout.strip()}")

        # Enviar para o GitHub
        result_push = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, check=True) # Ou 'master' se for o caso
        log(f"Git push executado com sucesso! Saída: {result_push.stdout.strip()}")
        return True

    except subprocess.CalledProcessError as e:
        log(f"Erro ao executar comando Git: {e}")
        log(f"Saída do erro (stdout): {e.stdout.strip()}")
        log(f"Saída do erro (stderr): {e.stderr.strip()}")
        return False
    except Exception as e:
        log(f"Ocorreu um erro inesperado: {e}")
        return False

if __name__ == "__main__":
    sincronizar_e_enviar_para_github()