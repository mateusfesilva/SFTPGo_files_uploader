import socket
socket.setdefaulttimeout(300)

import os
import sys
import requests
import re
import time
import urllib3
import random
from urllib.parse import quote_plus
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from requests import Request
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_
import ssl

# Esse script serve para fazer o upload de pastas com arquivos diretamente para o servidor web via http.
# O caminho com as pastas (não é o caminho do arquivo) deverá ser informado e todas as pastas, subpastas e
# arquivos presentes serão criados no servidor.
# É necessário que a estrutura de pastas locais a partir da pasta raíz esteja espelhada com a estrutura do sistema
# ex: LOCAL: \\192.168.2.14\h\PROJETO_AERO_RS_2025\PROD_6_MDS\BLOCO_07S\FOLHAS
#     WEB: Medições Contrato 16-2025-MIDR - HIDRO SUL/Medição 07/Entregas Medicao 07/PROD_6_MDS/BLOCO_07S/FOLHAS
# IMPORTANTE: Se não for detectado que a pasta alvo está dentro do path raíz uma confirmação para continuar será solicitada
# para evitar que os arquivos sejam enviados para locais incorretos.

LISTDIR_URL = "https://files-snsh.mdr.gov.br/web/client/dirs"
UPLOAD_URL = "https://files-snsh.mdr.gov.br/web/client/file"
DASH_URL = "https://files-snsh.mdr.gov.br/web/client/login"
BASE_URL = "https://files-snsh.mdr.gov.br/web/client/files"
# O path raiz é o caminho local da primeira pasta antes do espelhamento com o sistema web
PATH_RAIZ = r"\\192.168.2.14\g\HIDROSUL\Entrega-Fev" # A partir disso o caminho é o mesmo que o do site (PROD_6_MDS/...)
MED = input("Informe o número da medição (ex: 08): ")
PATH_UPLOAD = input("Informe o caminho com as pastas e arquivos que deseja enviar: ")
# Nome da primeira pasta no sistema web antes do espelhamento com o local
REMOTE_ROOT_NAME = f"/Medições Contrato 16-2025-MIDR - HIDRO SUL/Medição {MED}/Entregas Medicao {MED}"

USUARIO = "natalia.andrioli"
SENHA = "9149Nati"

# class LegacyAdapter(HTTPAdapter):
#     def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
#         ctx = ssl_.create_urllib3_context(ciphers='DEFAULT:@SECLEVEL=0')

#         ctx.check_hostname = False
#         ctx.options |= 0x4
#         ctx.verify_mode = ssl.CERT_NONE
#         ctx.minimum_version = ssl.TLSVersion.TLSv1

#         try:
#             ctx.options |= ssl.OP_NO_COMPRESSION
#         except AttributeError:
#             pass

#         self.poolmanager = PoolManager(
#             num_pools=connections,
#             maxsize=maxsize,
#             block=block,
#             ssl_context=ctx
#         )

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def random_colour():
    r_colour = random.randrange(0, 2**24)
    hex_r_colour = hex(r_colour)
    colour = '#' + hex_r_colour[2:] 
    return colour

def login(form_token):
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
    resp = session.post(LISTDIR_URL, params=param)

    print(f"status: {resp.status_code}")
    print("="*100,'\n')


class FileWithProgress:
    def __init__(self, filename, pbar):
        self.fd = open(filename, 'rb')
        self.pbar = pbar
        self.total_size = os.path.getsize(filename)

    def read(self, size=-1):
        chunk = self.fd.read(size)
        self.pbar.update(len(chunk))
        return chunk

    def __len__(self):
        return self.total_size

    def close(self):
        self.fd.close()


def upload_arquivo(caminho_local, caminho_remoto, nome_arquivo, tamanho_em_bytes, mtime_local):
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'pt-PT,pt;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'close',
        'Expect': '100-continue',
        'Origin': 'https://files-snsh.mdr.gov.br',
        'Pragma': 'no-cache',
        'Referer': 'https://files-snsh.mdr.gov.br/web/client/files?path=%2FMedi%C3%A7%C3%B5es+Contrato+16-2025-MIDR+-+HIDRO+SUL%2FMedi%C3%A7%C3%A3o+07%2FEntregas+Medicao+07%2FPROD_3_NPC%2FBLOCO_10S%2FFOLHAS&_=1770237099',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        # 'X-CSRF-TOKEN': token_de_acao(),
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        # 'Cookie': 'jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiV2ViQ2xpZW50IiwiMTAuMjEzLjUxLjUxIl0sImV4cCI6MTc3MDIzODc3NSwiaWF0IjoxNzcwMjM2OTYxLCJqdGkiOiJkNjFxbzhiMzI3MXZxMnJubHYwMCIsIm5iZiI6MTc3MDIzNjk1MSwic3ViIjoiMTc2OTQ1ODk1NTUwOSIsInVzZXJuYW1lIjoibmF0YWxpYS5hbmRyaW9saSJ9.HKOWjTwyUHh5jlYozLQRhVowJ30eUb4_e1nT-ZtbL2I',
    }

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

    server_files = file_exists(LISTDIR_URL, caminho_remoto)
    codigo_tempo = int(time.time())
    # Modification time
    mtime_ms = int(mtime_local * 1000)
    headers.update({
        'X-SFTPGO-MTIME': str(mtime_ms)
    })

    for i in range(3):
        headers.update({
            'X-CSRF-TOKEN': token_de_acao()
        })

        if nome_arquivo in server_files and tamanho_em_bytes == server_files[nome_arquivo] or (nome_arquivo == "Thumbs.db"):
            # print(f"Arquivo {nome_arquivo} já existe em {caminho_remoto}.")
            # print("=" * 100)
            continue
        else:
            if nome_arquivo in server_files:
                print(f"Deletando arquivo: {nome_arquivo}")
                path_completo_delete = f"{caminho_remoto}/{nome_arquivo}"
                path_encoded_delete = quote_plus(path_completo_delete)
                url_delete = f"{LISTDIR_URL}?path={path_encoded_delete}"
                try:
                    r = requests.delete(url_delete, headers=headers)
                    print(f"status: {r.status_code}")
                    print("="*100)
                except Exception as e:
                    print(f"Erro ao deletar arquivo {nome_arquivo}: {e}")
            try:
                with open(caminho_local, 'rb') as f:

                    print(f'Arquivo: {nome_arquivo}')
                    print(f'Destino: {caminho_remoto}')
                    filesize = os.path.getsize(caminho_local)

                    path_completo = f"{caminho_remoto}/{nome_arquivo}"
                    path_encoded = quote_plus(path_completo)
                    url_upload = f"{UPLOAD_URL}?path={path_encoded}"
                    path_pasta_encoded = quote_plus(caminho_remoto)
                    referer_url = f"{BASE_URL}?path={path_pasta_encoded}&_={codigo_tempo}"

                    headers.update({
                        'Referer': referer_url,
                        'Content-Type' : 'application/octet-stream'
                    })

                    with tqdm(total=filesize, unit='B', unit_scale=True, unit_divisor=1024, desc=nome_arquivo, ncols=80, file=sys.stdout, miniters=1, colour=random_colour()) as pbar:

                        payload = FileWithProgress(caminho_local, pbar)
                        req = Request('POST', url_upload, headers=headers, data=payload, params={'mkdir_parents' : 'false'})
                        prepped = session.prepare_request(req)
                        # tqdm.write(f'URl do request: {prepped.url}')

                        resp = session.send(prepped, verify=False, timeout=(10, 3600))
                        payload.close()
                        res = str(resp.status_code)
                        if resp.status_code in [200, 201, 202]:
                            tqdm.write(f"status = {res}")
                            time.sleep(1)
                            break
                        elif resp.status_code == 409:
                            tqdm.write(f'Arquivo {nome_arquivo} já existe em {caminho_remoto}')
                            tqdm.write(res)
                            return False
                        else:
                            tqdm.write(f"Erro {res}")
                            t = []
                            if nome_arquivo not in t:
                                t.append(f"{nome_arquivo}, {caminho_remoto}, err: {res}\n") 
                                with open('log.txt', 'a') as log:
                                    log.writelines(t)
                            tqdm.write(resp.text)
                            time.sleep(5)       
                            


            except ConnectionError:
                print("Conexão interrompida. Tentando reconexão...")
                time.sleep(30)
                
            except TimeoutError:
                print("Tempo de conexão esgotado. Tentando novamente...")
                time.sleep(30)
            
            except requests.exceptions.ReadTimeout:
                session.close()
                time.sleep(15)
                login(token)
                token_de_acao()


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

        try:
            with os.scandir(pasta_atual) as entradas:
                for entrada in entradas:
                    
                    if entrada.is_dir(follow_symlinks=False):
                        pastas_para_processar.append(entrada.path)
                        
                    elif entrada.is_file(follow_symlinks=False):

                        tamanho_em_bytes = entrada.stat().st_size
                        caminho_completo_local = entrada.path
                        nome_arquivo = entrada.name
                        mtime_local = entrada.stat().st_mtime
                        
                        upload_arquivo(
                            caminho_completo_local, 
                            caminho_remoto_pasta,
                            nome_arquivo,
                            tamanho_em_bytes,
                            mtime_local
                        )
                        
                        
        except PermissionError:
            print(f"Aviso: O Windows negou permissão para ler a pasta {pasta_atual}")
            continue
        
    print('Processo finalizado.')
    

if __name__ == "__main__":
    login(token)
    token_de_acao()
    executar_upload_parcial()
