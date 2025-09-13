import os
import re

def parse_list(env_var):
    """Converte una stringa separata da virgole in lista."""
    return [item.strip() for item in os.getenv(env_var, "").split(",") if item.strip()]

def extract_email_from_text(text):
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def read_html_template(path):
    """Legge un file HTML. Restituisce (contenuto, None) o (None, errore)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), None
    except Exception as e:
        return None, str(e)
