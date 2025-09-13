import requests, base64, time, re
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry
from config import HEADERS, REQUEST_DELAY

# Session con retry/backoff
session = requests.Session()
retry_strategy = Retry(
    total=5, backoff_factor=1,
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
    if not text: return None
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def extract_email_from_github_profile(username):
    # 1. prova via API (campo email pubblico)
    user_info = get_user_info(username)
    if user_info and user_info.get("email"):
        return user_info["email"]

    # 2. prova via README del repo più aggiornato
    repos = get_user_repos(username, max_repos=3)
    for repo in repos:
        readme = get_repo_readme(repo["full_name"])
        email = extract_email_from_text(readme)
        if email:
            return email

    # 3. fallback: regex sul profilo web (raramente funziona ormai)
    url = f"https://github.com/{username}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            match = re.search(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                response.text
            )
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
    except:
        return False

def get_candidate_users(n_users=50, keywords=None, location="Italy", language="Python", followers_range="10..2000"):
    """
    Restituisce utenti attinenti ai tuoi interessi.
    Evita account sospetti o vuoti.
    """
    candidates = []
    per_page = min(n_users, 30)
    page = 1

    while len(candidates) < n_users:
        q = f"location:{location} followers:{followers_range} language:{language}"
        if keywords:
            q += " " + " ".join([f"{kw} in:bio" for kw in keywords])
        url = f"https://api.github.com/search/users?q={q}&per_page={per_page}&page={page}"
        try:
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"[GitHub Search API] Status {resp.status_code}")
                break
            items = resp.json().get("items", [])
            if not items: break

            for u in items:
                username = u["login"]
                if is_followed(username):  # salta già seguiti
                    continue
                info = get_user_info(username)
                if not info:
                    continue
                # Filtri account sospetti
                followers = info.get("followers") or 0
                following = info.get("following") or 0
                if followers == 0 and following == 0:
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

def get_candidate_users_advanced(target_count):
    """
    Richiama utenti finché non si ottengono target_count utenti nuovi.
    """
    seen = set()
    valid_users = []

    while len(valid_users) < target_count:
        # Chiamata alla GitHub Search API
        candidate_users = get_candidate_users()
        for user in candidate_users:
            if user in seen:
                continue
            seen.add(user)
            if is_followed(user):
                print(f"{user} è già seguito, skip")
                continue
            valid_users.append(user)
            if len(valid_users) >= target_count:
                break
        time.sleep(REQUEST_DELAY)
    return valid_users