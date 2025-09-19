import os
import sys
import logging
from threading import Lock
from dotenv import load_dotenv
from flask_mail import Mail
from loguru import logger

# ==============================================================
# Carica variabili da .env
# ==============================================================
load_dotenv()

# ==============================================================
# Logging pulito
# ==============================================================
# Rimuove il default di loguru
logger.remove()
# Log principali della tua app su stdout
logger.add(sys.stdout, level="INFO", colorize=True)

# Riduce log troppo verbosi di smtplib (SMTP)
logging.getLogger("smtplib").setLevel(logging.WARNING)
# Riduce log troppo verbosi di pymongo (MongoDB)
logging.getLogger("pymongo").setLevel(logging.WARNING)

# ==============================================================
# Flask-Mail
# ==============================================================
mail = Mail()

# ==============================================================
# Configurazione Flask
# ==============================================================
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

MAIL_SETTINGS = {
    "MAIL_SERVER": os.getenv("EMAIL_HOST"),
    "MAIL_PORT": int(os.getenv("EMAIL_PORT", 587)),
    "MAIL_USE_TLS": True,
    "MAIL_USE_SSL": False,
    "MAIL_USERNAME": os.getenv("EMAIL_USER"),
    "MAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
}

# ==============================================================
# Variabili applicative
# ==============================================================
DEBUG_EMAIL = os.getenv("DEBUG_EMAIL")
DEBUG_EMAIL_MODE = os.getenv("DEBUG_EMAIL_MODE", "false")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

MY_CITY = os.getenv("MY_CITY", "Rome")
NEARBY_CITIES = os.getenv("NEARBY_CITIES", "").split(",")
KEYWORDS_BIO = os.getenv("KEYWORDS_BIO", "").split(",")
KEYWORDS_README = os.getenv("KEYWORDS_README", "").split(",")
ITALIAN_LOCATIONS = os.getenv("ITALIAN_LOCATIONS", "").split(",")

N_USERS = int(os.getenv("N_USERS", 10))
REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", 5))

GITHUB_API = "https://api.github.com"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
KEY_USERS = os.getenv("KEY_USERS", "").split(",")

# ==============================================================
# Variabili globali condivise
# ==============================================================
scraping_in_progress = False
new_users_buffer = []
buffer_lock = Lock()
