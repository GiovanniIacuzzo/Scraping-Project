import requests, base64
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry
from config import HEADERS
import re

# Session con retry/backoff
session = requests.Session()
retry_strategy = Retry(
    total=5, backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "PUT"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def get_user_info(username):
    url = f"https://api.github.com/users/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[GitHub API Error] {username}: {e}")
    return None

def get_user_repos(username):
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
    repos = []
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            for r in resp.json():
                repos.append({"name": r["name"], "language": r["language"], "full_name": r["full_name"]})
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

def extract_email_from_github_profile(username):
    url = f"https://github.com/{username}"
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        mail_link = soup.find("a", href=re.compile(r"^mailto:"))
        if mail_link:
            return mail_link.get("href").replace("mailto:", "").strip()
        email_li = soup.find("li", itemprop="email")
        if email_li and "aria-label" in email_li.attrs:
            return email_li["aria-label"].replace("Email: ", "").strip()
    except Exception:
        return None

def get_candidate_users(per_page=30, location="Italy", followers_range="10..2000", language="Python"):
    """
    Restituisce una lista di username da GitHub Search API.
    """
    users = []
    query = f"location:{location} followers:{followers_range} language:{language}"
    url = f"https://api.github.com/search/users?q={query}&per_page={per_page}"

    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            users = [u["login"] for u in items]
        else:
            print(f"[GitHub Search API] Status {resp.status_code}")
    except Exception as e:
        print(f"[GitHub Search API] Errore ricerca utenti: {e}")

    return users

def is_followed(username):
    url = f"https://api.github.com/user/following/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        return resp.status_code == 204
    except requests.exceptions.RequestException:
        return False