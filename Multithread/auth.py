from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
import threading
import urllib3
from urllib3.util import Retry
import time
import re

from config import CERT_PATH, DASH_URL, BASE_URL, USER, PASSWORD

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Evitar race condition das threads
login_lock = threading.Lock()
session = requests.Session()
# session.verify = CERT_PATH
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=12)
session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update({    
        'Referer': DASH_URL,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
})

def login():
    session.cookies.clear()
    for i in range(3):
        session.headers.update({
            'Referer': DASH_URL,})
        response = session.get(DASH_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        find_token = soup.find("input", {"name": "_form_token"})
        if not find_token:
            time.sleep(5)
        csrf_token = find_token.get("value")
        payload_login = {"username": USER, "password": PASSWORD, "_form_token": csrf_token}
        try:
            resp_post = session.post(DASH_URL, data=payload_login)
            soup_error = BeautifulSoup(resp_post.text, "html.parser")
            alerta = soup_error.find(class_=lambda x: x and ("alert" in x or "error"))
            alert = alerta.get_text(strip=True)
            if "Sign in" in alert or "Please Wait" in alert:
                return False
            if resp_post.status_code in [200, 201, 202, 302]:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    raise Exception("Falha no login após 3 tentativas.")

def action_token():
    for i in range(3):
        try:
            resp = session.get(BASE_URL)
            match = re.search(
                r'["\'](ey[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+)["\']',
                resp.text,
            )
            if match:
                new_token = match.group(1)
                session.headers.update({"X-Csrf-Token": new_token})
                return new_token
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)
    raise Exception("Falha ao obter token de ação após 3 tentativas.")