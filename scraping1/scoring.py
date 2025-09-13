import time
from github_api import get_user_info, get_user_repos, get_repo_readme
from config import KEYWORDS_BIO, KEYWORDS_README, ITALIAN_LOCATIONS, NEARBY_CITIES, REQUEST_DELAY

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

    followers, following = user_info.get("followers",0), user_info.get("following",0)
    if 10 <= followers <= 2000: score += 3
    elif followers > 5000: score -= 3
    elif followers < 5: score -= 2
    if 10 <= following <= 2000: score += 3
    elif following < 5: score -= 2
    if following > 0:
        ratio = followers / following
        if 0.3 <= ratio <= 3: score += 2
        elif ratio > 10 or ratio < 0.1: score -= 3

    repos = get_user_repos(username)[:5]
    for repo in repos:
        readme = get_repo_readme(repo["full_name"])
        if any(kw.lower() in readme.lower() for kw in KEYWORDS_README):
            score += 2
        time.sleep(REQUEST_DELAY)
    return score
