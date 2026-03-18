import os
import time
from urllib.parse import quote_plus

from config import LISTDIR_URL, UPLOAD_URL, ORIGIN, BASE_URL, SOURCE_PATH, DASH_URL
from auth import session, login_lock, login, action_token


def calculate_remote_path(absoulte_file_path, remote_root_name):
    relative_path = os.path.relpath(absoulte_file_path, SOURCE_PATH)
    web_path = relative_path.replace("\\", "/")
    full_path = f"{remote_root_name}/{web_path}"
    return full_path.replace("//", "/")


def create_dir(remote_path, global_token):
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Referer": DASH_URL,
            "X-CSRF-TOKEN": global_token,
        }
    )
    param = {"path": remote_path}
    resp = session.post(LISTDIR_URL, params=param, timeout=(10, 30))
    if resp.status_code not in [200, 201, 202]:
        raise Exception(
            f"Failed to create directory {remote_path}. Status code: {resp.status_code}"
        )
    return resp.status_code


def file_exists(remote_path):
    for i in range(3):
        try:
            param = {"path": remote_path}
            rp = session.get(LISTDIR_URL, params=param, timeout=(10, 30))
            if rp.status_code in [200, 201, 202]:
                content = rp.json()
                file_list = {
                    item.get("name"): item.get("size") for item in content.get("name")
                }
                return file_list
        except Exception:
            time.sleep(5)
    return None


def process_one_file(
    file_name, local_data, global_token, server_files, remote_path, mtime_local
):
    local_size = os.path.getsize(local_data)
    max_retries = 3
    time_stamp = int(time.time())
    mtime_ms = int(mtime_local * 1000)

    if file_name in server_files and server_files[file_name] == local_size:
        return None

    for attempt in range(max_retries):
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
                    "Connection": "close",
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

                resp = session.post(
                    url_upload,
                    headers=local_headers,
                    data=f,
                    timeout=(60, 3600),
                )

                if resp.status_code in [401, 403]:
                    with login_lock:
                        login()
                        global_token = action_token()
                    continue

                if resp.status_code in [200, 201, 202]:
                    return f"Status: {resp.status_code}"

                resp.raise_for_status()

        except Exception:
            pass

        if attempt < max_retries - 1:
            time.sleep(2**attempt)

    raise Exception(f"Failed to upload {file_name} after {max_retries} attempts.")
