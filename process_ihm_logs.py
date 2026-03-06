import os
import subprocess
import datetime
import pandas as pd

# Caminho do repositório de LOGS (aquele que você já automatizou)
IHM_LOGS_REPO = r"C:\fromtherm_ihm_logs_repo"

# Subpasta dentro do repositório de logs onde estão os CSVs da IHM
IHM_LOGS_DIR = os.path.join(
    IHM_LOGS_REPO,
    "ihm_logs",
    "historico_L1",
    "IP_registro192.168.2.150",
    "datalog"
)

# Caminho do repositório fromtherm-dados (onde está este script)
DADOS_REPO = r"C:\fromtherm-dados"

# Arquivo consolidado que o Streamlit vai ler
OUTPUT_CSV = os.path.join(DADOS_REPO, "dados", "ihm_historico_L1.csv")


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(os.path.join(DADOS_REPO, "process_log.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_git_command(args, cwd):
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.stdout.strip():
            log(f"Git stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            log(f"Git stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERRO git ({' '.join(args)}): {e}")
        if e.stdout:
            log(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log(f"stderr: {e.stderr.strip()}")
        return False


def load_all_ihm_logs():
    if not os.path.exists(IHM_LOGS_DIR):
        log(f"Pasta de logs da IHM não encontrada: {IHM_LOGS_DIR}")
        return None

    all_rows = []
    for root, _, files in os.walk(IHM_LOGS_DIR):
        for file in files:
            if not file.lower().endswith(".csv"):
                continue
            full_path = os.path.join(root, file)
            try:
                # Alguns arquivos podem ter a primeira linha como cabeçalho Markdown (| --- | ...)
                # e separados por "|" - vamos tratar isso.
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]

                if not lines:
                    continue

                # Se a primeira linha começa com "|" vamos tratar como "tabela markdown"
                if lines[0].startswith("|"):
                    # Remove o primeiro e o último "|" e separa por "|"
                    header = [col.strip() for col in lines[0].strip("|").split("|")]
                    data_lines = lines[2:]  # pula linha de header e linha de "---"

                    records = []
                    for line in data_lines:
                        if not line.startswith("|"):
                            continue
                        cols = [c.strip() for c in line.strip("|").split("|")]
                        if len(cols) != len(header):
                            continue
                        records.append(cols)

                    if not records:
                        continue

                    df = pd.DataFrame(records, columns=header)
                else:
                    # fallback: tentar ler como CSV padrão separado por ";" ou ","
                    df = pd.read_csv(full_path)

                # Adiciona colunas de origem do arquivo (data do arquivo, nome, etc.)
                df["arquivo_origem"] = file
                all_rows.append(df)

                log(f"Lido com sucesso: {full_path} ({len(df)} linhas)")

            except Exception as e:
                log(f"Erro ao ler {full_path}: {e}")

    if not all_rows:
        log("Nenhum dado lido dos logs da IHM.")
        return None

    full_df = pd.concat(all_rows, ignore_index=True)

    # Exemplo de ajustes simples:
    # - Combinar Date + Time em uma coluna datetime
    if "Date" in full_df.columns and "Time" in full_df.columns:
        try:
            full_df["timestamp"] = pd.to_datetime(
                full_df["Date"].str.strip() + " " + full_df["Time"].str.strip(),
                format="%Y/%m/%d %H:%M:%S",
                errors="coerce",
            )
        except Exception as e:
            log(f"Erro ao converter timestamp: {e}")

    return full_df


def main():
    log("Iniciando processamento dos logs da IHM...")

    # Garante que temos a versão mais recente do repo de LOGS
    run_git_command(["git", "pull"], cwd=IHM_LOGS_REPO)

    df = load_all_ihm_logs()
    if df is None or df.empty:
        log("Nenhum dado para salvar. Fim do processamento.")
        return

    # Garante pasta 'dados' no repo fromtherm-dados
    os.makedirs(os.path.join(DADOS_REPO, "dados"), exist_ok=True)

    # Salva o consolidado
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    log(f"Arquivo consolidado salvo em: {OUTPUT_CSV} (linhas: {len(df)})")

    # Agora faz git add/commit/push no fromtherm-dados
    if not run_git_command(["git", "add", "dados/ihm_historico_L1.csv"], cwd=DADOS_REPO):
        log("Falha no git add.")
        return

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=DADOS_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    if not status:
        log("Sem mudanças para commit após git add.")
        return

    msg = "Atualizando dados IHM - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not run_git_command(["git", "commit", "-m", msg], cwd=DADOS_REPO):
        log("Falha no git commit.")
        return

    if not run_git_command(["git", "push", "origin", "main"], cwd=DADOS_REPO):
        log("Falha no git push (fromtherm-dados).")
        return

    log("Processamento concluído e dados enviados para fromtherm-dados com sucesso.")


if __name__ == "__main__":
    main()