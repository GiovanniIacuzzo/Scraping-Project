import requests, base64, time, re, os
from requests.adapters import HTTPAdapter, Retry
from config import HEADERS, REQUEST_DELAY
from github import Github
import logging

# Session con retry/backoff
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
g = Github(GITHUB_TOKEN, per_page=20)

session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "PUT", "GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# ---------------- User Info ----------------
def get_user_info(username):
    url = f"https://api.github.com/users/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[GitHub API] Status {resp.status_code} for user {username}")
    except Exception as e:
        print(f"[GitHub API Error] {username}: {e}")
    return None

def get_user_repos(username, max_repos=5):
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page={max_repos}"
    repos = []
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            for r in resp.json():
                repos.append({
                    "name": r["name"],
                    "language": r["language"],
                    "full_name": r["full_name"],
                    "updated_at": r["updated_at"],
                    "stars": r["stargazers_count"],
                    "forks": r["forks_count"]
                })
    except Exception as e:
        print(f"[GitHub Repo Error] {username}: {e}")
    return repos

def get_repo_readme(full_name):
    url = f"https://api.github.com/repos/{full_name}/readme"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            content = resp.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[GitHub README Error] {full_name}: {e}")
    return ""

# ---------------- Email Extraction ----------------
def extract_email_from_text(text):
    if not text:
        return None
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def extract_email_from_github_profile(username):
    user_info = get_user_info(username)
    if user_info and user_info.get("email"):
        return user_info["email"]

    repos = get_user_repos(username, max_repos=3)
    for repo in repos:
        readme = get_repo_readme(repo["full_name"])
        email = extract_email_from_text(readme)
        if email:
            return email

    url = f"https://github.com/{username}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", response.text)
            if match:
                return match.group(0)
    except Exception as e:
        print(f"[Profile Scrape Error] {username}: {e}")

    return None

# ---------------- Candidate Users ----------------
def is_followed(username):
    url = f"https://api.github.com/user/following/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        return resp.status_code == 204
    except Exception:
        return False

def get_candidate_users(n_users=50, keywords=None, location="Italy", language="Python", followers_range="10..2000"):
    candidates = []
    per_page = min(n_users, 30)
    page = 1

    keywords = [kw.strip() for kw in (keywords or []) if kw.strip()]

    while len(candidates) < n_users:
        q = f"location:{location} followers:{followers_range} language:{language}"
        if keywords:
            q += " " + " ".join([f"{kw} in:bio" for kw in keywords])
        url = f"https://api.github.com/search/users?q={q}&per_page={per_page}&page={page}"
        print(f"[DEBUG] GitHub Search Query: {url}")  # per debug 422

        try:
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"[GitHub Search API] Status {resp.status_code}")
                break
            items = resp.json().get("items", [])
            if not items:
                break

            for u in items:
                username = u["login"]
                if is_followed(username):
                    continue
                info = get_user_info(username)
                if not info:
                    continue
                if info.get("followers", 0) == 0 and info.get("following", 0) == 0:
                    continue
                candidates.append(username)
                if len(candidates) >= n_users:
                    break
        except Exception as e:
            print(f"[GitHub Search API] Error: {e}")
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    return candidates[:n_users]

# =========================
# Funzione avanzata utenti senza duplicati DB
# =========================
def get_candidate_users_advanced(N, my_city, nearby_cities=None, keywords_bio=None, keywords_readme=None, locations=None):
    """
    Restituisce una lista di username candidati da GitHub.
    
    Params:
        N: numero totale di utenti da restituire
        my_city: città principale
        nearby_cities: lista di città vicine
        keywords_bio: lista di keyword per bio
        keywords_readme: lista di keyword per README
        locations: lista di località italiane accettate
    """
    users_collected = set()
    users_needed = N
    nearby_cities = nearby_cities or []
    keywords_bio = keywords_bio or []
    keywords_readme = keywords_readme or []
    locations = locations or []

    all_cities = [my_city] + nearby_cities

    for city in all_cities:
        if users_needed <= 0:
            break

        # Costruisci query bio e README in modo pulito
        bio_query = " ".join([f'in:bio "{kw.strip()}"' for kw in keywords_bio if kw.strip()])
        readme_query = " ".join([f'"{kw.strip()}"' for kw in keywords_readme if kw.strip()])
        
        for loc in locations:
            if users_needed <= 0:
                break

            query = f'location:{city} {bio_query} {readme_query} followers:10..2000 language:Python'
            logger.debug(f"[DEBUG] GitHub Search Query: {query}")

            try:
                result = g.search_users(query)
                for user in result:
                    if user.login not in users_collected:
                        users_collected.add(user.login)
                        users_needed -= 1
                        yield user.login
                        if users_needed <= 0:
                            break
                time.sleep(1)  # evita rate limit
            except Exception as e:
                logger.error(f"[ERROR] GitHub query fallita per city={city}, loc={loc}: {e}")
