import os
import subprocess
import datetime
import shutil
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
DADOS_REPO = r"C:\fromtherm-dados"  # ajuste se estiver em outro lugar

# Pasta de saída dos arquivos que o dashboard usa
DADOS_DIR = os.path.join(DADOS_REPO, "dados")

# (Opcional) arquivo consolidado - se ainda quiser manter
OUTPUT_CSV = os.path.join(DADOS_DIR, "ihm_historico_L1.csv")


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
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout:
            log(f"Git stdout: {result.stdout.strip()}")
        if result.stderr:
            log(f"Git stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERRO git ({' '.join(args)}): {e}")
        if e.stdout:
            log(f"stdout: {e.stdout}")
        if e.stderr:
            log(f"stderr: {e.stderr}")
        return False


def detectar_novos_arquivos_e_copiar():
    """
    Copia todos os CSV da pasta de logs (fromtherm-ihm-logs)
    para a pasta 'dados' do repo fromtherm-dados, mantendo os nomes.

    Também (opcional) monta um consolidado.
    """
    if not os.path.exists(IHM_LOGS_DIR):
        log(f"Pasta de logs IHM não encontrada: {IHM_LOGS_DIR}")
        return 0

    os.makedirs(DADOS_DIR, exist_ok=True)

    arquivos_logs = [
        os.path.join(IHM_LOGS_DIR, f)
        for f in os.listdir(IHM_LOGS_DIR)
        if f.lower().endswith(".csv")
    ]

    if not arquivos_logs:
        log("Nenhum arquivo CSV encontrado na pasta de logs IHM.")
        return 0

    linhas_total = 0
    df_consolidados = []

    for caminho_origem in arquivos_logs:
        nome = os.path.basename(caminho_origem)
        caminho_destino = os.path.join(DADOS_DIR, nome)

        # Copia os arquivos com mesmo nome para a pasta 'dados'
        shutil.copy2(caminho_origem, caminho_destino)
        log(f"Copiado para dashboard: {caminho_origem} -> {caminho_destino}")

        # (Opcional) também monta o consolidado em memória
        try:
            df_tmp = pd.read_csv(caminho_origem)
            df_consolidados.append(df_tmp)
            linhas_total += len(df_tmp)
        except Exception as e:
            log(f"Falha ao ler para consolidação: {caminho_origem} -> {e}")

    # (Opcional) salvar consolidado
    if df_consolidados:
        df_final = pd.concat(df_consolidados, ignore_index=True)
        df_final.to_csv(OUTPUT_CSV, index=False)
        log(f"Arquivo consolidado salvo em: {OUTPUT_CSV} (linhas: {len(df_final)})")

    return linhas_total


def main():
    log("Iniciando processamento dos logs da IHM (cópia para pasta 'dados')...")

    # Garantir que estamos com o repositório atualizado
    run_git_command(["git", "pull", "origin", "main"], cwd=DADOS_REPO)

    linhas = detectar_novos_arquivos_e_copiar()
    if linhas == 0:
        log("Nenhum arquivo processado/copiado. Nada a atualizar.")
        return

    # Adicionar tudo que mudou na pasta 'dados'
    if not run_git_command(["git", "add", "dados"], cwd=DADOS_REPO):
        log("Falha no git add (dados).")
        return

    msg = f"Atualizando dados IHM para dashboard - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if not run_git_command(["git", "commit", "-m", msg], cwd=DADOS_REPO):
        log("Falha no git commit.")
        return

    if not run_git_command(["git", "push", "origin", "main"], cwd=DADOS_REPO):
        log("Falha no git push (fromtherm-dados).")
        return

    log("Processamento concluído e dados enviados para fromtherm-dados com sucesso.")


if __name__ == "__main__":
    main()