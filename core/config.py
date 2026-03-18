import os
from dotenv import load_dotenv

load_dotenv()

LISTDIR_URL = os.getenv("LISTDIR_URL", "")
UPLOAD_URL = os.getenv("UPLOAD_URL", "")
DASH_URL = os.getenv("DASH_URL", "")
BASE_URL = os.getenv("BASE_URL", "")
ORIGIN = os.getenv("ORIGIN", "")

# O path raiz é o caminho local da primeira pasta antes do espelhamento com o sistema web
SOURCE_PATH = os.path.normpath(os.getenv("SOURCE_PATH", ""))

# Nome da primeira pasta no sistema web antes do espelhamento com o local
REMOTE_ROOT_TEMPLATE = os.getenv("REMOTE_ROOT_NAME", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_PATH = os.path.join(BASE_DIR, "certs", os.getenv("CERTIFICATE", ""))

USER = os.getenv("USER", "")
PASSWORD = os.getenv("PASSWORD", "")
