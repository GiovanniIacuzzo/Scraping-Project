import re
import os

def extract_email_from_text(text):
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def read_html_template(filename):
    """
    Legge un template HTML dalla cartella 'templates' e lo restituisce.
    Ritorna una tupla: (contenuto, errore)
    """
    try:
        base_path = os.path.join(os.path.dirname(__file__), "..", "templates")
        path = os.path.join(base_path, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None
    except Exception as e:
        return None, str(e)