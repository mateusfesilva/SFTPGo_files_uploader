import os 
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, BarColumn, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from config import SOURCE_PATH, REMOTE_ROOT_TEMPLATE
from auth import login, action_token, session
from worker import calculate_remote_path, create_dir, file_exists, process_one_file
    
def upload():
    MED = input("Informe o número da medição: ")
    PATH_UPLOAD = input("Informe o caminho com as pastas e arquivos que deseja enviar: ")
    REMOTE_ROOT_NAME = REMOTE_ROOT_TEMPLATE.replace("{MED}", MED)
    token = action_token()

    
    print(f"\nIniciando upload:\n    [Origem] {PATH_UPLOAD}")
    print(f"    [Destino] {REMOTE_ROOT_NAME}")
    print("=" * 100)
    
    if SOURCE_PATH not in PATH_UPLOAD:
        print("ALERTA: A pasta alvo não parece estar dentro da pasta raiz!")
        continuar = input("Deseja continuar mesmo assim? (s/n): ")
        if continuar.lower() != 's':
            return
    
    dirs_to_process = [PATH_UPLOAD]
    
    while dirs_to_process:
        current_dir = dirs_to_process.pop(0)
        remote_path_dir = calculate_remote_path(current_dir, REMOTE_ROOT_NAME)
        print(remote_path_dir)
        print(f"Criando diretório remoto: {remote_path_dir}")
        print(f"Status:", create_dir(remote_path_dir, token))
        print("=" * 100)
        file_in_folder = file_exists(remote_path_dir) or {}
        
        try:
            folder_files = []
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        dirs_to_process.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        folder_files.append({
                            "name": entry.name,
                            "path": entry.path,
                            "mtime": entry.stat().st_mtime
                        })
            
            if folder_files:
                total_files = len(folder_files)
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                ) as progress: 
                    task = progress.add_task(
                        f"[cyan]Enviando arquivos em: {current_dir}", total=total_files
                    )
                                    
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
                                file["mtime"]
                            )
                            futures[future] = file["name"]
                            
                        for future in as_completed(futures):
                            file_name = futures[future]
                            try:
                                result = future.result()
                                if result:
                                    progress.console.print(f"[green]✔ Sucesso[/green] | {file_name} --> {result}")
                                else:
                                    progress.console.print(f"[yellow]⚠ Ignorado[/yellow] | {file_name}")
                            except Exception as e:
                                progress.console.print(f"[red]✖ Erro[/red] | {file_name}: {e}")
                            finally:
                                progress.advance(task)
                            
        except PermissionError:
            print(f"[red]Permissão negada para acessar: {current_dir}[/red]")
            continue
    
    print("\nProcesso finalizado!")
        
if __name__ == "__main__":
    try:
        print("=" * 100)
        print("Autenticando...")
        if login():
            print("Login bem-sucedido!")
            print("=" * 100)
            upload()    
        else:
            print("Falha na autenticação. Verifique suas credenciais.")
            print("=" * 100)
    finally:
        session.close()