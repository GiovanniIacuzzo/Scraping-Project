import requests
import time
import base64
import re
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

# ==============================================================
# Funzioni di supporto
# ==============================================================

def parse_list(env_var):
    """Converte una stringa separata da virgole in lista."""
    return [item.strip() for item in os.getenv(env_var, "").split(",") if item.strip()]

# ==============================================================
# Caricamento configurazione da file .env
# ==============================================================
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", 1))
N_USERS = int(os.getenv("N_USERS", 10))

# MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["scraping-project"]
collection = db["users"]

# Keyword
KEYWORDS_BIO = parse_list("KEYWORDS_BIO")
KEYWORDS_README = parse_list("KEYWORDS_README")

# Località italiane
ITALIAN_LOCATIONS = parse_list("ITALIAN_LOCATIONS")
MY_CITY = os.getenv("MY_CITY")
NEARBY_CITIES = parse_list("NEARBY_CITIES")

# ==============================================================
# Setup session con retry/backoff
# ==============================================================

session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "PUT"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# ==============================================================
# Funzioni principali
# ==============================================================

def get_user_info(username):
    url = f"https://api.github.com/users/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Errore richiesta GitHub per {username}: {e}")
    return None

def get_user_repos(username):
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
    repos = []
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            for repo in resp.json():
                repos.append({
                    "name": repo["name"],
                    "language": repo["language"],
                    "full_name": repo["full_name"]
                })
    except requests.exceptions.RequestException as e:
        print(f"Errore richiesta repos per {username}: {e}")
    return repos

def get_repo_readme(full_name):
    url = f"https://api.github.com/repos/{full_name}/readme"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            content = resp.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="ignore")
    except requests.exceptions.RequestException as e:
        print(f"Errore richiesta README {full_name}: {e}")
    return ""

def extract_email_from_text(text):
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def extract_email_from_github_profile(username):
    url = f"https://github.com/{username}"
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # link mailto
        mail_link = soup.find("a", href=re.compile(r"^mailto:"))
        if mail_link:
            return mail_link.get("href").replace("mailto:", "").strip()
        # li con itemprop=email
        email_li = soup.find("li", itemprop="email")
        if email_li and "aria-label" in email_li.attrs:
            match = re.search(r"Email:\s*(.+)", email_li["aria-label"])
            if match:
                return match.group(1).strip()
    except Exception as e:
        print(f"Errore estrazione email profilo {username}: {e}")
        return None
    return None

def is_followed(username):
    url = f"https://api.github.com/user/following/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        return resp.status_code == 204
    except requests.exceptions.RequestException:
        return False

def score_user(username):
    user_info = get_user_info(username)
    if not user_info:
        return -999

    score = 0
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

    bio = user_info.get("bio", "")
    if bio and any(kw.lower() in bio.lower() for kw in KEYWORDS_BIO):
        score += 2
    elif not bio:
        score -= 1

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

    repos = get_user_repos(username)[:5]
    for repo in repos:
        readme = get_repo_readme(repo["full_name"])
        if any(kw.lower() in readme.lower() for kw in KEYWORDS_README):
            score += 2
        time.sleep(REQUEST_DELAY)

    return score

def get_candidate_users():
    candidates = []
    query = f"location:Italy followers:10..2000 language:Python"
    url = f"https://api.github.com/search/users?q={query}&per_page={N_USERS}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for u in items:
                candidates.append(u["login"])
    except requests.exceptions.RequestException as e:
        print(f"Errore ricerca utenti: {e}")
    return candidates

def save_user(username, score):
    user_info = get_user_info(username)
    if not user_info:
        return

    bio = user_info.get("bio", "")
    repos_info = get_user_repos(username)[:5]
    repos_data = []
    email_found = extract_email_from_text(bio)

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

    if not email_found:
        email_found = extract_email_from_github_profile(username)

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
        save_user(user, score)
        scored_users.append((user, score))
        print(f"Salvato {user} con punteggio {score}")

    scored_users.sort(key=lambda x: x[1], reverse=True)
    final_users = [user for user, score in scored_users[:N_USERS]]
    print("Utenti salvati e ordinati per rilevanza:", final_users)
