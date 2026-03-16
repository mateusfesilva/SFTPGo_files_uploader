import os
import re
import random
import time
import threading
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests 
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv
import urllib3

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env
LISTDIR_URL = os.getenv("LISTDIR_URL", "")
UPLOAD_URL = os.getenv("UPLOAD_URL", "")
DASH_URL = os.getenv("DASH_URL", "")
BASE_URL = os.getenv("BASE_URL", "")
# O path raiz é o caminho local da primeira pasta antes do espelhamento com o sistema web
PATH_RAIZ = r"E:\MATEUS\HIDROSUL_GOV" # A partir disso o caminho é o mesmo que o do site (PROD_6_MDS/...)
MED = input("Informe o número da medição (ex: 08): ")
PATH_UPLOAD = input("Informe o caminho com as pastas e arquivos que deseja enviar: ")
# Nome da primeira pasta no sistema web antes do espelhamento com o local
REMOTE_ROOT_NAME = f"/Medições Contrato 16-2025-MIDR - HIDRO SUL/Medição {MED}/Entregas Medicao {MED}"
USUARIO = os.getenv("USUARIO", "")
SENHA = os.getenv("SENHA", "")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
adapter = HTTPAdapter(max_retries=3)
session.mount('https://', adapter)
session.headers.update({
     'Referer': 'https://files-snsh.mdr.gov.br/web/client/login',
     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
})

# response=session.get(DASH_URL)
# soup = BeautifulSoup(response.text, 'html.parser')
# find_token = soup.find('input', {'name': '_form_token'})
# token = find_token.get('value')
login_lock = threading.Lock()

def random_colour():
    r_colour = random.randrange(0, 2**24)
    hex_r_colour = hex(r_colour)
    colour = '#' + hex_r_colour[2:] 
    return colour

def login():
    for i in range (3):
        global session
        if session is not None:
            session.close()
        
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=3)
        session.mount('https://', adapter)
        session.headers.update({
            'Referer': 'https://files-snsh.mdr.gov.br/web/client/login',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }) 
        response=session.get(DASH_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        find_token = soup.find('input', {'name': '_form_token'})
        token = find_token.get('value')   

        playload_login = {
            "username": USUARIO,
            "password": SENHA,
            "_form_token": token
        }
        time.sleep(1)
        print("=" * 100)
        print(playload_login)
        # print(session.headers)
        print("=" * 100)
        try:
            resp_post = session.post(DASH_URL, data=playload_login)
            print('code: ', resp_post.status_code)
            print("=" * 100)

            soup_error = BeautifulSoup(resp_post.text, 'html.parser')
            alerta = soup_error.find(class_=lambda x: x and ('alert' in x or 'error'))
            alert = alerta.get_text(strip=True)
            print('content: ', alert)
            
        except:
                print("Erro durante o login. Tentando novamente...")
                time.sleep(5)

        if resp_post.status_code in[202, 200, 302]:
            print('Login realizado\n')
            print("=" * 100)
            break

        else:
                print(f'Login não realizado: {resp_post.status_code} ({i+1})')


def calcular_caminho_remoto(caminho_arquivo_absoluto):
    """
    Calcula o caminho relativo à RAIZ DO PROJETO, não à pasta de upload.
    Isso mantém a estrutura de diretórios correta no servidor.
    """
    caminho_relativo = os.path.relpath(caminho_arquivo_absoluto, PATH_RAIZ)
    caminho_web = caminho_relativo.replace("\\", "/")
    full_path = f"{REMOTE_ROOT_NAME}/{caminho_web}"
    return full_path.replace("//", "/")


def token_de_acao():
    i = 0
    while i < 3:
        try:
            resp = session.get(BASE_URL)
            match = re.search(r'["\'](ey[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+)["\']', resp.text)
            if match:
                token_novo = match.group(1)
                session.headers.update({"X-Csrf-Token": token_novo})
                i = 5
                return token_novo

            else:
                print("Token de ação não encontrado.")
                i+=1
                time.sleep(5)
                
        except ConnectionError:
            print("Conexão interrompida. Tentando reconexão...")
            i+=1
            time.sleep(10)
            
        except TimeoutError:
            print("Tempo de conexão esgotado. Tentando novamente...")
            i+=1
            time.sleep(10)
        

def criar_pasta(caminho_remoto):
    print(f"Criando pasta {caminho_remoto} ")
    print(caminho_remoto)

    param = {
        "path": caminho_remoto
    }
    resp = session.post(LISTDIR_URL, params=param, timeout=(10, 30))

    print(f"status: {resp.status_code}")
    print("="*100,'\n')

        
def file_exists(LISTDIR_URL, caminho_remoto):
    i = 0
    while i < 3:
        param = {
            "path": caminho_remoto
        }

        try:
            file_list = {}
            rp = session.get(LISTDIR_URL, params=param)
            if rp.status_code in [200, 201, 202]:
                i = 5
                content = rp.json()
                for item in content:
                    name = item.get("name", "")
                    size = item.get("size", "")
                    if name and size is not None:
                        file_list[name] = size

            return file_list
        
        except requests.exceptions.RequestException as e:
            print(f"Erro: {e}")
            i+=1
            time.sleep(5)
            return None


def process_one_file(file_name, local_data, global_token, server_files, remote_path, mtime_local):
    local_size = os.path.getsize(local_data)
    max_retries = 3
    time_stamp = int(time.time())
    mtime_ms = int(mtime_local * 1000)
    
    if file_name in server_files and server_files[file_name] == local_size:
        return None
    
    for attempt in range(max_retries):
               
        try:
            with open(local_data, 'rb') as f:
                abs_path = f"{remote_path}/{file_name}"
                path_encoded = quote_plus(abs_path)
                url_upload = f"{UPLOAD_URL}?path={path_encoded}"
                folder_path_encoded = quote_plus(remote_path)
                referer_url = f"{BASE_URL}?path={folder_path_encoded}&_={time_stamp}"
                
                local_headers = {
                    'Accept': '*/*',
                    'Accept-Language': 'pt-PT,pt;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'close',
                    'Expect': '100-continue',
                    'Origin': 'https://files-snsh.mdr.gov.br',
                    'Pragma': 'no-cache',
                    'Referer': referer_url,
                    'Content-Type' : 'application/octet-stream',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'X-CSRF-TOKEN': global_token,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
                    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'X-SFTPGO-MTIME' : str(mtime_ms)
                }  
                
                resp = session.post(
                    url_upload,
                    data=f,
                    headers=local_headers,
                    verify=False,
                    timeout=(60,3600)
                )
            
            
            if resp.status_code in [401, 403]:
                print("Unauthorized. File: ", file_name, ". Status code: ", resp.status_code, ". Re-authenticating...")
                with login_lock:
                    login()
                    global_token = token_de_acao()
                
                raise Exception("Session renewed. Retrying...")
            
            if resp.status_code in [200, 201, 202]:
                return (f"status = {resp.status_code} - Uploaded {file_name}\n")

            resp.raise_for_status()
            
        except requests.exceptions.ConnectionError:
            print("Connection error. File: ", file_name, ". Retrying...")
            raise
            
        except requests.exceptions.Timeout:
            print("Timeout. File: ", file_name, ". Retrying...")
            raise
        
        except requests.exceptions.ReadTimeout:
            print("Read timeout. File: ", file_name, ". Retrying...")   
            raise
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return ("Failed to upload ", file_name, " after ", max_retries, " attempts.\n")


# def executar_upload_parcial():
#     print(f"Iniciando upload:\n    {PATH_UPLOAD}")
#     print(f"Mantendo estrutura relativa a:\n    {PATH_RAIZ}")
#     print("=" * 100)

#     if PATH_RAIZ not in PATH_UPLOAD:
#         print("ALERTA: A pasta alvo não parece estar dentro da pasta raiz!")
#         print("Isso pode criar pastas nos lugares errados do servidor.")
#         continuar = input("Deseja continuar mesmo assim? (s/n): ")
#         if continuar.lower() != 's':
#             return

#     for raiz_atual, subpastas, arquivos in os.walk(PATH_UPLOAD):

#         caminho_remoto_pasta = calcular_caminho_remoto(raiz_atual)
#         criar_pasta(caminho_remoto_pasta)

#         for arquivo in arquivos:
#             caminho_completo_local = os.path.join(raiz_atual, arquivo)

#             upload_arquivo(caminho_completo_local, caminho_remoto_pasta)

#     print('Processo finalizado.')

def executar_upload_parcial():
    print(f"Iniciando upload:\n    {PATH_UPLOAD}")
    print(f"Mantendo estrutura relativa a:\n    {PATH_RAIZ}")
    print("=" * 100)

    if PATH_RAIZ not in PATH_UPLOAD:
        print("ALERTA: A pasta alvo não parece estar dentro da pasta raiz!")
        print("Isso pode criar pastas nos lugares errados do servidor.")
        continuar = input("Deseja continuar mesmo assim? (s/n): ")
        if continuar.lower() != 's':
            return

    pastas_para_processar = [PATH_UPLOAD]

    while pastas_para_processar:
        pasta_atual = pastas_para_processar.pop()

        caminho_remoto_pasta = calcular_caminho_remoto(pasta_atual)
        criar_pasta(caminho_remoto_pasta)
        file_in_folder = file_exists(LISTDIR_URL, caminho_remoto_pasta)
        
        if file_in_folder is None:
            file_in_folder = {}
        
        try:
            folder_files = []
            with os.scandir(pasta_atual) as entradas:
                for entrada in entradas:
                    
                    if entrada.is_dir(follow_symlinks=False):
                        pastas_para_processar.append(entrada.path)
                        
                    elif entrada.is_file(follow_symlinks=False):

                        folder_files.append({
                            "name": entrada.name,
                            "path": entrada.path,
                            "mtime": entrada.stat().st_mtime
                        })

            if file_in_folder is not None:
                token = token_de_acao()    
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = {}
                    for file in folder_files:

                        future = executor.submit(
                            process_one_file,
                            file['name'],
                            file['path'],
                            token,
                            file_in_folder,
                            caminho_remoto_pasta,
                            file['mtime']
                        )
                        futures[future] = file['name']

                    for future in as_completed(futures):
                        name_file = futures[future]
                        try:
                            result = future.result()
                            if result:
                                print(f"[{name_file}] {result}")
                            
                        except Exception as e:
                            print(f"Error {name_file}: {e}")
                                       
        except PermissionError:
            print(f"Aviso: O Windows negou permissão para ler a pasta {pasta_atual}")
            continue
        
    print('Processo finalizado.')
    

if __name__ == "__main__":
    try:
        login()
        token_de_acao()
        executar_upload_parcial()
    finally:
        session.close()