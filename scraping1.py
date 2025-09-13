import requests
import time
import base64
import re
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

# ==============================================================
# Caricamento configurazione da file .env
# ==============================================================
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Parametri di configurazione
REQUEST_DELAY = 1   # intervallo (in secondi) tra richieste API per evitare rate limit
N_USERS = 10        # numero massimo di utenti da analizzare per query

# Connessione al database MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["scraping-project"]
collection = db["users"]

# Set di parole chiave per il matching semantico
KEYWORDS_BIO = ["machine learning", "deep learning", "python", "data science", "AI", "ML", "deep-learning", "analisi dati"]
KEYWORDS_README = ["machine learning", "deep learning", "computer vision", "data analysis", "neural network", "AI", "ML"]

# Geolocalizzazione: località italiane e città prioritarie
ITALIAN_LOCATIONS = ["Italy", "Italia", "Roma", "Milano", "Torino", "Napoli", "Firenze",
                     "Bologna", "Palermo", "Genova", "Verona", "Venezia", "Bari"]

MY_CITY = "Enna"
NEARBY_CITIES = ["Enna", "Caltanissetta", "Catania", "Palermo", "Messina"]

# ==============================================================
# Funzioni di supporto per interazione con API GitHub
# ==============================================================

def get_user_info(username):
    """Recupera i metadati di un utente GitHub (profilo, bio, followers, ecc.)."""
    url = f"https://api.github.com/users/{username}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    return None

def get_user_repos(username):
    """Recupera i repository pubblici più recenti di un utente GitHub."""
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
    repos = []
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        for repo in resp.json():
            repos.append({
                "name": repo["name"],
                "language": repo["language"],
                "full_name": repo["full_name"]
            })
    return repos

def get_repo_readme(full_name):
    """Scarica e decodifica il README di un repository (se disponibile)."""
    url = f"https://api.github.com/repos/{full_name}/readme"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        content = resp.json().get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    return ""

# ==============================================================
# Funzioni di elaborazione e scoring
# ==============================================================

def extract_email_from_text(text):
    """Estrae il primo indirizzo email da un testo tramite regex."""
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def is_followed(username):
    """Verifica se l'utente specificato è già seguito dall'account autenticato."""
    url = f"https://api.github.com/user/following/{username}"
    resp = requests.get(url, headers=HEADERS)
    return resp.status_code == 204  # 204 indica che l'utente è già seguito

def score_user(username):
    """
    Calcola un punteggio di rilevanza per un utente GitHub.
    Il punteggio considera:
      - posizione geografica (priorità città vicine)
      - presenza di keyword nella bio
      - numero di followers/following e loro rapporto
      - contenuti nei README dei repository
    """
    user_info = get_user_info(username)
    if not user_info:
        return -999  # penalità in caso di dati mancanti

    score = 0

    # Valutazione della location
    location = user_info.get("location", "")
    if location:
        if any(city.lower() in location.lower() for city in NEARBY_CITIES):
            score += 10
        elif any(loc.lower() in location.lower() for loc in ITALIAN_LOCATIONS):
            score += 5
        else:
            score -= 2
    else:
        score -= 1

    # Analisi bio
    bio = user_info.get("bio", "")
    if bio and any(kw.lower() in bio.lower() for kw in KEYWORDS_BIO):
        score += 2
    elif not bio:
        score -= 1

    # Analisi followers/following
    followers = user_info.get("followers", 0)
    following = user_info.get("following", 0)

    if 10 <= followers <= 2000:
        score += 3
    elif followers > 5000:
        score -= 3
    elif followers < 5:
        score -= 2

    if 10 <= following <= 2000:
        score += 3
    elif following < 5:
        score -= 2

    if following > 0:
        ratio = followers / following
        if 0.3 <= ratio <= 3:
            score += 2
        elif ratio > 10 or ratio < 0.1:
            score -= 3

    # Analisi semantica dei repository (README)
    repos = get_user_repos(username)[:5]
    for repo in repos:
        readme = get_repo_readme(repo["full_name"])
        if any(kw.lower() in readme.lower() for kw in KEYWORDS_README):
            score += 2
        time.sleep(REQUEST_DELAY)

    return score

def get_candidate_users():
    """Esegue una query su GitHub Search API per identificare potenziali candidati."""
    candidates = []
    query = f"location:Italy followers:10..2000 language:Python"
    url = f"https://api.github.com/search/users?q={query}&per_page={N_USERS}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        items = resp.json().get("items", [])
        for u in items:
            candidates.append(u["login"])
    return candidates

def save_user(username, score):
    """Salva (o aggiorna) un utente nel database MongoDB con tutti i dati rilevanti."""
    user_info = get_user_info(username)
    if not user_info:
        return

    bio = user_info.get("bio", "")
    repos_info = get_user_repos(username)[:5]
    repos_data = []
    email_found = extract_email_from_text(bio)

    # Analisi dei repository per arricchimento dati ed estrazione email
    for repo in repos_info:
        readme = get_repo_readme(repo["full_name"])
        repos_data.append({
            "name": repo["name"],
            "language": repo["language"],
            "readme": readme
        })
        if not email_found:
            email_found = extract_email_from_text(readme)
        time.sleep(REQUEST_DELAY)

    # Documento MongoDB
    user_doc = {
        "username": user_info["login"],
        "bio": bio,
        "location": user_info.get("location", ""),
        "followers": user_info.get("followers", 0),
        "following": user_info.get("following", 0),
        "languages": list(set([r["language"] for r in repos_data if r["language"]])),
        "repos": repos_data,
        "github_url": user_info.get("html_url"),
        "score": score,
        "email_to_notify": email_found,
        "last_checked": datetime.utcnow()
    }

    collection.update_one(
        {"username": user_doc["username"]},
        {"$set": user_doc},
        upsert=True
    )

# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":
    candidate_users = get_candidate_users()
    scored_users = []

    for user in candidate_users:
        if is_followed(user):
            print(f"{user} è già seguito, skip")
            continue

        score = score_user(user)
        scored_users.append((user, score))
        save_user(user, score)
        print(f"Salvato {user} con punteggio {score}")

    scored_users.sort(key=lambda x: x[1], reverse=True)
    final_users = [user for user, score in scored_users[:N_USERS]]
    print("Utenti salvati e ordinati per rilevanza:", final_users)
