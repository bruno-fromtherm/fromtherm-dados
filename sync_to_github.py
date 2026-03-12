import os
import shutil
import subprocess
import time
from datetime import datetime

# --- Configurações ---
# Pasta ONDE A IHM SALVA OS CSVs localmente.
# Esta é a pasta que a IHM preenche.
SOURCE_DIR = r"C:\FROMTHERM_IHM_UPLOADS\historico_L1\IP_registro192.168.2.150\datalog"

# Caminho COMPLETO para a pasta raiz do seu repositório Git local.
# Ex: C:\FROMTHERM_REPOS\fromtherm-dados
GIT_REPO_PATH = r"C:\FROMTHERM_REPOS\fromtherm-dados" # <-- VERIFIQUE E AJUSTE ESTE CAMINHO!

# Subpasta DENTRO do repositório Git onde os CSVs devem ser copiados.
# Esta é a pasta que seu Streamlit app está configurado para ler no GitHub.
DEST_SUBDIR_IN_REPO = r"dados_brutos\historico_L1\IP_registro192.168.2.150\datalog"

# Caminho completo para a pasta de destino dentro do repositório Git local.
DEST_DIR = os.path.join(GIT_REPO_PATH, DEST_SUBDIR_IN_REPO)

# Caminho para o arquivo de log do script (dentro do repositório Git)
SYNC_LOG_FILE = os.path.join(GIT_REPO_PATH, "sync_log.txt")

# --- Função para registrar mensagens ---
def log_message(message):
    """Escreve uma mensagem no console e no arquivo de log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    try:
        os.makedirs(os.path.dirname(SYNC_LOG_FILE), exist_ok=True)
        with open(SYNC_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"ERRO ao escrever no log: {e}")

# --- Função para executar comandos Git ---
def run_git_command(command, cwd):
    try:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True, encoding='utf-8')
        if result.stdout.strip():
            log_message(f"Git stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            log_message(f"Git stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"ERRO Git: Comando '{' '.join(command)}' falhou com código {e.returncode}.")
        if e.stdout:
            log_message(f"Git stdout (erro): {e.stdout.strip()}")
        if e.stderr:
            log_message(f"Git stderr (erro): {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        log_message("ERRO: Git não encontrado. Verifique se está instalado e no PATH.")
        return False
    except Exception as e:
        log_message(f"ERRO inesperado ao executar comando Git: {e}")
        return False

# --- Função principal de sincronização ---
def sync_files_to_github():
    log_message("Iniciando a sincronização de arquivos para o GitHub...")
    log_message(f"Origem dos CSVs (IHM): {SOURCE_DIR}")
    log_message(f"Destino no Repositório Git Local: {DEST_DIR}")
    log_message(f"Repositório Git Local: {GIT_REPO_PATH}")
if not os.path.exists(SOURCE_DIR):
    log_message(f"ERRO: Pasta de origem da IHM não encontrada: {SOURCE_DIR}. Verifique o caminho.")
    return

if not os.path.exists(GIT_REPO_PATH):
    log_message(f"ERRO: Pasta do repositório Git local não encontrada: {GIT_REPO_PATH}. Verifique o caminho.")
    return

# 1. Puxar as últimas alterações do GitHub para evitar conflitos
log_message("Executando git pull para atualizar o repositório local...")
if not run_git_command(["git", "pull", "origin", "main"], GIT_REPO_PATH): # Assumindo branch 'main'
    log_message("Falha no git pull. Verifique sua conexão e credenciais do Git.")
    # Continuar mesmo com erro de pull, mas é bom investigar
    # return

# 2. Criar o diretório de destino dentro do repositório Git se não existir
os.makedirs(DEST_DIR, exist_ok=True)

# 3. Copiar arquivos da origem para o destino no repositório Git
files_copied = 0
try:
    source_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.csv')]
    if not source_files:
        log_message(f"Nenhum arquivo CSV encontrado em {SOURCE_DIR}. Nenhuma ação de cópia necessária.")
    else:
        for filename in source_files:
            source_path = os.path.join(SOURCE_DIR, filename)
            dest_path = os.path.join(DEST_DIR, filename)

            # Copia o arquivo se ele for novo ou tiver sido modificado
            if not os.path.exists(dest_path) or \
               os.path.getmtime(source_path) &gt; os.path.getmtime(dest_path):
                shutil.copy2(source_path, dest_path)
                log_message(f"Copiado/Atualizado: {filename}")
                files_copied += 1
            # else:
            #     log_message(f"Arquivo inalterado: {filename}") # Descomente para ver todos os arquivos
except Exception as e:
    log_message(f"ERRO ao copiar arquivos de {SOURCE_DIR} para {DEST_DIR}: {e}")
    return

if files_copied == 0:
    log_message("Nenhum arquivo novo ou modificado para sincronizar com o GitHub.")
    log_message("Sincronização concluída.")
    return

# 4. Adicionar e commitar as alterações no Git
log_message(f"Adicionando {files_copied} arquivo(s) ao Git...")
if not run_git_command(["git", "add", DEST_DIR], GIT_REPO_PATH):
    log_message("Falha ao adicionar arquivos ao Git.")
    return

# Verificar se há alterações para commitar (ignora arquivos não rastreados que não estão em DEST_DIR)
status_output = subprocess.run(["git", "status", "--porcelain", DEST_DIR], cwd=GIT_REPO_PATH, capture_output=True, text=True, encoding='utf-8').stdout.strip()

if status_output:
    log_message("Alterações detectadas. Commitando...")
    commit_message = f"Auto-sync IHM logs: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({files_copied} files)"
    if not run_git_command(["git", "commit", "-m", commit_message], GIT_REPO_PATH):
        log_message("Falha ao commitar alterações.")
        return

    # 5. Fazer o push para o GitHub
    log_message("Executando git push...")
    if not run_git_command(["git", "push", "origin", "main"], GIT_REPO_PATH): # Assumindo branch 'main'
        log_message("Falha no git push. Verifique sua conexão e credenciais do Git.")
        return
    else:
        log_message("Sincronização com GitHub concluída com sucesso!")
else:
    log_message("Nenhuma alteração para commitar após a cópia dos arquivos (podem ser arquivos já commitados ou ignorados).")

log_message(f"Sincronização finalizada em {datetime.now()}")
if __name__ == "__main__":
    sync_files_to_github()