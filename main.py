import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.live import Live
from rich.console import Group
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich import print

from core.config import SOURCE_PATH, REMOTE_ROOT_TEMPLATE
from core.auth import login, action_token, session
from core.worker import calculate_remote_path, create_dir, file_exists, process_one_file


def upload():
    MED = input("Informe o número da medição: ")
    PATH_UPLOAD = input(
        "Informe o caminho com as pastas e arquivos que deseja enviar: "
    )
    # Adicionar a medição ao nome da pasta remota usando o template
    # REMOTE_ROOT_NAME = REMOTE_ROOT_TEMPLATE.replace("{MED}", MED)
    REMOTE_ROOT_NAME = REMOTE_ROOT_TEMPLATE
    token = action_token()

    print("=" * 100)
    print(f"[bold blue]Iniciando upload:[/bold blue]\n    [Origem] {PATH_UPLOAD}")
    print(f"    [Destino] {REMOTE_ROOT_NAME}")
    print("=" * 100)

    if SOURCE_PATH not in PATH_UPLOAD:
        print(
            "[bold yellow]ALERTA: A pasta alvo não parece estar dentro da pasta raiz![/bold yellow]"
        )
        continuar = input("Deseja continuar mesmo assim? (s/n): ")
        if continuar.lower() != "s":
            return

    dirs_to_process = [PATH_UPLOAD]

    while dirs_to_process:
        current_dir = dirs_to_process.pop(0)
        remote_path_dir = calculate_remote_path(current_dir, REMOTE_ROOT_NAME)

        print(f"[bold blue]Diretório remoto:[/bold blue] {remote_path_dir}")
        print(f"Status:", create_dir(remote_path_dir, token))

        file_in_folder = file_exists(remote_path_dir)

        try:
            folder_files = []
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        dirs_to_process.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        folder_files.append(
                            {
                                "name": entry.name,
                                "path": entry.path,
                                "mtime": entry.stat().st_mtime,
                            }
                        )

            if folder_files:
                total_files = len(folder_files)
                ign = 0
                upl = 0
                err = 0

                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    TextColumn(
                        "[yellow]Ignorados: {task.fields[ignored_files_count]}[/yellow]"
                    ),
                    TextColumn(
                        "[green]Enviados: {task.fields[uploaded_files_count]}[/green]"
                    ),
                    TextColumn("[red]Erros: {task.fields[error_files_count]}[/red]"),
                )

                task = progress.add_task(
                    f"[cyan]{current_dir}",
                    total=total_files,
                    ignored_files_count=0,
                    uploaded_files_count=0,
                    error_files_count=0,
                )

                status_texto = "[grey50]Iniciando leitura dos arquivos...[/grey50]"

                def gerar_painel():
                    """Monta o frame atual unindo o Painel de texto e a Barra"""
                    painel = Panel(
                        status_texto,
                        title="Último Processado",
                        border_style="cyan",
                        width=110,
                    )
                    return Group(painel, progress)

                with Live(gerar_painel(), refresh_per_second=15) as live:
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        futures = {}
                        for file in folder_files:
                            future = executor.submit(
                                process_one_file,
                                file["name"],
                                file["path"],
                                token,
                                file_in_folder,
                                remote_path_dir,
                                file["mtime"],
                            )
                            futures[future] = file["name"]

                        for future in as_completed(futures):
                            file_name = futures[future]
                            try:
                                result = future.result()
                                if result:
                                    upl += 1
                                    status_texto = f"[green]✅ Sucesso | Enviado:[/green] {file_name}"
                                else:
                                    ign += 1

                                progress.update(
                                    task,
                                    uploaded_files_count=upl,
                                    ignored_files_count=ign,
                                )

                            except Exception as e:
                                err += 1
                                status_texto = f"[bold red]✖ Erro no arquivo:[/bold red] {file_name} - {e}"
                                progress.update(task, error_files_count=err)

                            finally:
                                progress.advance(task)
                                live.update(gerar_painel())

                print("=" * 100)

        except PermissionError:
            print(f"[bold red]Permissão negada para acessar: {current_dir}[/bold red]")
            continue

    print("=" * 39, "Processo finalizado!", "=" * 39, "\n")


if __name__ == "__main__":
    try:
        print("=" * 100)
        print("[bold blue]Autenticando...[/bold blue]")
        if login():
            print(f"[bold green]Login bem-sucedido![/bold green]")
            print("=" * 100)
            upload()
        else:
            print("[red]Falha na autenticação. Verifique suas credenciais.[/red]")
            print("=" * 100)
    finally:
        session.close()
