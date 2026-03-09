import os
import shutil
import git
from datetime import datetime

# Diretório de origem onde os arquivos CSV da IHM são gerados
# Certifique-se de que este caminho está correto no seu sistema Windows
SOURCE_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\FROMTHERM_IHM_UPLOADS\historico_L1\IP_registro192.168.2.150\datalog"

# Diretório de destino dentro do repositório Git
DEST_DIR = "dados_brutos/historico_L1/IP_registro192.168.2.150/datalog"

# Caminho para o arquivo de log do script
SYNC_LOG_FILE = "sync_log.txt"

def log_message(message):
    """Escreve uma mensagem no console e no arquivo de log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(SYNC_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def sync_files_to_github():
    log_message("Iniciando a sincronização de arquivos para o GitHub...")

    try:
        # Inicializa o repositório Git
        repo = git.Repo('.')
        origin = repo.remotes.origin
        origin.pull()  # Puxa as últimas alterações do GitHub antes de começar

        # Cria o diretório de destino se não existir
        os.makedirs(DEST_DIR, exist_ok=True)

        # Lista os arquivos CSV no diretório de origem
        source_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.csv')]

        if not source_files:
            log_message(f"Nenhum arquivo CSV encontrado em {SOURCE_DIR}. Nenhuma ação necessária.")
            return

        files_copied = 0
        for filename in source_files:
            source_path = os.path.join(SOURCE_DIR, filename)
            dest_path = os.path.join(DEST_DIR, filename)

            # Copia o arquivo se ele for novo ou tiver sido modificado
            if not os.path.exists(dest_path) or \
               os.path.getmtime(source_path) > os.path.getmtime(dest_path):
                shutil.copy2(source_path, dest_path)
                log_message(f"Copiado/Atualizado: {filename}")
                files_copied += 1
            else:
                log_message(f"Arquivo inalterado: {filename}")

        if files_copied > 0:
            # Adiciona todos os arquivos copiados/modificados ao stage
            repo.git.add(DEST_DIR)

            # Verifica se há alterações para commitar
            if repo.is_dirty(untracked_files=True):
                commit_message = f"Sincronização automática: {files_copied} arquivos CSV atualizados."
                repo.index.commit(commit_message)
                log_message(f"Commit realizado: '{commit_message}'")

                # Faz o push para o GitHub
                origin.push()
                log_message("Push para o GitHub realizado com sucesso.")
            else:
                log_message("Nenhuma alteração para commitar após a cópia dos arquivos.")
        else:
            log_message("Nenhum arquivo novo ou modificado para sincronizar.")

    except git.exc.GitCommandError as e:
        log_message(f"Erro do Git: {e}")
    except Exception as e:
        log_message(f"Ocorreu um erro inesperado: {e}")

    log_message("Sincronização concluída.")

if __name__ == "__main__":
    sync_files_to_github()