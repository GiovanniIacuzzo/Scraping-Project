import os
import re
import requests

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Scraping-Project"
}

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

def build_user_document(username):
    """
    Ritorna un dict con info di un utente GitHub.
    Usa sia /users/{username} che /users/{username}/repos
    """
    base_url = f"https://api.github.com/users/{username}"

    # info profilo
    r = requests.get(base_url, headers=HEADERS)
    if r.status_code != 200:
        return None
    profile = r.json()

    # info repos
    r = requests.get(base_url + "/repos?per_page=100", headers=HEADERS)
    repos = r.json() if r.status_code == 200 else []

    languages = []
    for repo in repos:
        if repo.get("language"):
            languages.append(repo["language"])

    user_doc = {
        "username": profile.get("login"),
        "name": profile.get("name"),
        "company": profile.get("company"),
        "location": profile.get("location"),
        "bio": profile.get("bio"),
        "email_public": profile.get("email"),
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
        "public_repos": profile.get("public_repos", 0),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
        "main_languages": list(set(languages))
    }
    return user_doc

NUM_FEATURES = ["followers", "following", "public_repos"]
CAT_FEATURES = ["company", "location", "main_languages"]
TEXT_FEATURE = "bio"

def extract_features(user):
    """
    Converte un dizionario utente in un feature dict compatibile con il modello.
    """
    feat = {}

    # numeriche
    for col in NUM_FEATURES:
        val = user.get(col, 0)
        try:
            feat[col] = int(val) if val is not None else 0
        except Exception:
            feat[col] = 0

    # categoriche
    for col in CAT_FEATURES:
        val = user.get(col, "unknown")
        if isinstance(val, (list, tuple, set)):
            feat[col] = ", ".join(val) if val else "unknown"
        else:
            feat[col] = str(val) if val else "unknown"

    # testo
    bio = user.get(TEXT_FEATURE, "")
    feat[TEXT_FEATURE] = bio if bio else ""

    return feat