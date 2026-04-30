import os
import threading
import datetime
import time
import logging
from urllib.parse import quote_plus

from pathlib import Path

from requests.sessions import HTTPAdapter

from core.config import LISTDIR_URL, UPLOAD_URL, ORIGIN, BASE_URL, SOURCE_PATH, DASH_URL
from core.auth import session, login_lock, login, action_token

state_cond = threading.Condition()
active_uploads = 0
is_resetting = False
empty_files = []

def reset_session():
    global is_resetting
    with state_cond:
        if is_resetting:
            while is_resetting:
                state_cond.wait()
            return action_token()
        
        is_resetting = True
        if active_uploads > 0:
            print(f"\nWaiting for {active_uploads} active uploads to finish before resetting session...\n")
            while active_uploads > 0:
                state_cond.wait()
                
        success = False
        success_token = None
                
    try:
        session.close()
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=12)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        if login():
            success = True
            success_token = action_token()
            print("Session reset successfully.")
        else:
            print("Failed to reset session.")
            succes = False
    except Exception as e:
        print(f"Error during session reset: {str(e)}")
        success = False
        
    with state_cond:
        is_resetting = False
        state_cond.notify_all()
        
    return success_token if success else None
                                
                                
def logging_errors(file_name: str, attempt: int, stts: str):
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/upload_errors.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.error(f"Error uploading file {file_name} in attempt {attempt + 1}. Status code: {stts}.")


def calculate_remote_path(absoulte_file_path: Path, remote_root_name: str):
    relative_path = os.path.relpath(absoulte_file_path, SOURCE_PATH)    
    web_path = relative_path.replace("\\", "/")
    full_path = f"{remote_root_name}/{web_path}"
    return full_path.replace("//", "/")


def create_dir(remote_path: str, global_token: str):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                    "Referer": DASH_URL,
                    "X-CSRF-TOKEN": global_token,
                }
            )
            param = {"path": remote_path}
            with session.post(LISTDIR_URL, params=param, timeout=(10, 30)) as resp:
                if resp.status_code not in [201, 500]:
                    if attempt == 2:
                        raise Exception(f"Failed to create directory {remote_path} after {max_retries} attempts. Status code: {resp.status_code}")
                    with login_lock:
                        login()
                        global_token = action_token()
                    continue
                return resp.status_code, global_token
            
        except Exception as e:
            if attempt == 2:
                raise Exception(f"Failed to create directory {remote_path} after {max_retries} attempts. Error: {str(e)}")
            time.sleep(2**attempt)
    return resp.status_code, global_token


def file_exists(remote_path: str):
    for i in range(3):
        try:
            param = {"path": remote_path}
            with session.get(LISTDIR_URL, params=param, timeout=(10, 30)) as rp:
                if rp.status_code in [200, 201, 202]:
                    content = rp.json()
                    file_list = {item.get("name"): item.get("size") for item in content}
                    return file_list
        except Exception:
            time.sleep(5)
    return None


def process_one_file(
    file_name: str, local_data: Path, global_token: str, server_files: str, remote_path: str, mtime_local:float
):
    global active_uploads, is_resetting, empty_files
    local_size = os.path.getsize(local_data)
    max_retries = 3
    time_stamp = int(time.time())
    mtime_ms = int(mtime_local * 1000)
    kb_size = local_size / 1024
    remote_path_utf8 = remote_path.encode("utf-8", errors="replace").decode("utf-8")

    if (file_name in server_files and server_files[file_name] == local_size) or file_name == "Thumbs.db":
        return None

    for attempt in range(max_retries):
        with state_cond:
            while is_resetting:
                state_cond.wait()
            active_uploads += 1
        try:
            with open(local_data, "rb") as f:
                abs_path = f"{remote_path}/{file_name}"
                url_upload = f"{UPLOAD_URL}?path={quote_plus(abs_path)}"
                referer_url = (
                    f"{BASE_URL}?path={quote_plus(remote_path)}&_={time_stamp}"
                )
                local_headers = {
                    "Accept": "*/*",
                    "Accept-Language": "pt-PT,pt;q=0.9",
                    "Cache-Control": "no-cache",
                    "Expect": "100-continue",
                    "Origin": ORIGIN,
                    "Pragma": "no-cache",
                    "Referer": referer_url,
                    "Content-Type": "application/octet-stream",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "X-CSRF-TOKEN": global_token,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "X-SFTPGO-MTIME": str(mtime_ms),
                }

                with session.post(
                    url_upload,
                    headers=local_headers,
                    data=f,
                    timeout=(60, 3600),
                ) as resp:

                    if resp.status_code in [200, 202, 401, 403]:
                        print (f"Attempt {attempt + 1} for file {file_name} failed.")
                        raise Exception(f"Failed to upload {file_name}. Status code: {resp.status_code}")
                    elif resp.status_code == 201:
                        return f"Status: {resp.status_code}"
                    else:
                        resp.raise_for_status()

        except Exception as e:
            logging_errors(file_name, attempt, resp.status_code if 'resp' in locals() else 'No response')
        
        finally:
            with state_cond:
                active_uploads -= 1
                if active_uploads == 0 and is_resetting:
                    state_cond.notify_all()
            
            if attempt == 1:
                token = reset_session()
                if isinstance(token, str):
                    global_token = token
                    
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            else:
                raise Exception(f"Failed to upload {file_name} after {max_retries} attempts.")
        
                    
    raise Exception(f"Failed to upload {file_name} after {max_retries} attempts.")

