import os
import shutil
import subprocess
import datetime

# Caminhos principais
LOGS_REPO_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\fromtherm_ihm_logs_repo\ihm_logs"
DADOS_REPO_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\fromtherm-dados"

# Pasta onde vamos guardar os CSVs brutos (com subpastas, iguais ao logs_repo)
DADOS_BRUTOS_DIR = os.path.join(DADOS_REPO_DIR, "dados_brutos")

# Pasta que o dashboard Streamlit usa (apenas arquivos soltos, sem subpastas)
DADOS_DASHBOARD_DIR = os.path.join(DADOS_REPO_DIR, "dados")

# Arquivo de controle de CSVs já processados
PROCESSED_CSV_LOG = os.path.join(DADOS_REPO_DIR, "processed_csv.log")

def log_message(message: str):
    """Registra mensagens na tela e em um arquivo de log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    log_path = os.path.join(DADOS_REPO_DIR, "process_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_processed_csvs():
    """Retorna um conjunto com os caminhos completos dos CSVs já processados."""
    if not os.path.exists(PROCESSED_CSV_LOG):
        return set()
    with open(PROCESSED_CSV_LOG, "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

def add_processed_csv(path: str):
    """Adiciona um CSV ao arquivo de controle."""
    with open(PROCESSED_CSV_LOG, "a", encoding="utf-8") as f:
        f.write(path + "\n")

def run_git_command(args):
    """Executa comando git no repositório de dados."""
    try:
        result = subprocess.run(
            args,
            cwd=DADOS_REPO_DIR,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.stdout.strip():
            log_message(f"Git stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            log_message(f"Git stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"Erro Git: {e}")
        if e.stdout:
            log_message(f"Git stdout (erro): {e.stdout.strip()}")
        if e.stderr:
            log_message(f"Git stderr (erro): {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        log_message("Erro: Git não encontrado. Verifique se está instalado e no PATH.")
        return False

def process_ihm_logs():
    """
    Copia CSVs novos do repositório de logs (fromtherm_ihm_logs_repo\ihm_logs)
    para:
      - dados_brutos (mantendo subpastas)
      - dados (apenas arquivos soltos, para o dashboard)
    e faz git add/commit/push no repositório fromtherm-dados.
    """
    log_message("Iniciando processamento dos logs da IHM...")

    if not os.path.exists(LOGS_REPO_DIR):
        log_message(f"Erro: Pasta de logs não encontrada: {LOGS_REPO_DIR}")
        return

    os.makedirs(DADOS_BRUTOS_DIR, exist_ok=True)
    os.makedirs(DADOS_DASHBOARD_DIR, exist_ok=True)

    processed = get_processed_csvs()
    novos_csvs = []

    for root, _, files in os.walk(LOGS_REPO_DIR):
        for file in files:
            if not file.lower().endswith(".csv"):
                continue

            source_path = os.path.join(root, file)

            if source_path in processed:
                continue

            # Caminho relativo (para replicar estrutura em dados_brutos)
            relative = os.path.relpath(source_path, LOGS_REPO_DIR)
            dest_path_brutos = os.path.join(DADOS_BRUTOS_DIR, relative)

            try:
                # Copia para dados_brutos (mantendo subpastas)
                os.makedirs(os.path.dirname(dest_path_brutos), exist_ok=True)
                shutil.copy2(source_path, dest_path_brutos)
                log_message(f"Copiado para dados_brutos: {source_path} -> {dest_path_brutos}")

                # Copia também para a pasta 'dados' do dashboard (apenas o arquivo)
                dest_path_dashboard = os.path.join(DADOS_DASHBOARD_DIR, os.path.basename(source_path))
                shutil.copy2(source_path, dest_path_dashboard)
                log_message(f"Copiado para dados (dashboard): {source_path} -> {dest_path_dashboard}")

                novos_csvs.append(source_path)
                add_processed_csv(source_path)
            except Exception as e:
                log_message(f"Erro ao copiar {source_path}: {e}")

    if not novos_csvs:
        log_message("Nenhum novo CSV encontrado para processamento.")
        log_message("Processamento finalizado.")
        return

    log_message(f"{len(novos_csvs)} novo(s) CSV(s) copiado(s). Preparando git add/commit/push...")

    # git add .
    if not run_git_command(["git", "add", "."]):
        log_message("Falha no git add.")
        return

    # Verifica se há mudanças
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=DADOS_REPO_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8"
    ).stdout.strip()

    if not status:
        log_message("Sem mudanças para commit após git add.")
        log_message("Processamento finalizado.")
        return

    # git commit
    msg = "Atualizando dados IHM - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not run_git_command(["git", "commit", "-m", msg]):
        log_message("Falha no git commit.")
        return

    # git push origin main
    if not run_git_command(["git", "push", "origin", "main"]):
        log_message("Falha no git push. Verifique branch, conexão ou credenciais.")
        return

    log_message("Processamento concluído e dados enviados ao GitHub com sucesso.")

if __name__ == "__main__":
    process_ihm_logs()