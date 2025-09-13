import time
from github_api import get_user_info, get_user_repos, get_repo_readme
from config import KEYWORDS_BIO, KEYWORDS_README, ITALIAN_LOCATIONS, NEARBY_CITIES, REQUEST_DELAY

def score_user(user_info, max_repos=5):
    """
    Restituisce uno score complessivo per un utente GitHub.
    Considera località, bio, followers/following e contenuto README.
    """
    if not user_info:
        return -999

    score = 0

    # -------- Località ----------
    location = (user_info.get("location") or "").lower()
    if any(city.lower() in location for city in NEARBY_CITIES):
        score += 15
    elif any(loc.lower() in location for loc in ITALIAN_LOCATIONS):
        score += 8
    else:
        score -= 5

    # -------- Bio ----------
    bio = (user_info.get("bio") or "").lower()
    bio_hits = sum(1 for kw in KEYWORDS_BIO if kw.lower() in bio)
    score += bio_hits * 3
    if not bio:
        score -= 2

    # -------- Followers / Following ----------
    followers = user_info.get("followers", 0)
    following = user_info.get("following", 0)
    
    if 50 <= followers <= 1000:
        score += 5
    elif followers < 20:
        score -= 3
    elif followers > 5000:
        score -= 5

    if 30 <= following <= 500:
        score += 3
    elif following < 5:
        score -= 3

    if following > 0:
        ratio = followers / following
        if 0.5 <= ratio <= 5:
            score += 4
        elif ratio < 0.2 or ratio > 10:
            score -= 4

    # -------- Repository & README ----------
    username = user_info.get("login")
    repos = get_user_repos(username, max_repos=max_repos)
    for repo in repos:
        readme = get_repo_readme(repo["full_name"]).lower()
        readme_hits = sum(1 for kw in KEYWORDS_README if kw.lower() in readme)
        score += readme_hits * 2
        time.sleep(REQUEST_DELAY)

    return score