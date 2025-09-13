import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
DEBUG_EMAIL = os.getenv("DEBUG_EMAIL")

session = requests.Session()

def is_followed(username):
    url = f"https://api.github.com/user/following/{username}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        return resp.status_code == 204
    except requests.exceptions.RequestException:
        return False

def follow_user_api(username):
    url = f"https://api.github.com/user/following/{username}"
    try:
        resp = session.put(url, headers=HEADERS)
        return resp.status_code in [204, 200]
    except requests.exceptions.RequestException:
        return False

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
    except Exception:
        return None
    return None
