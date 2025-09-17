from config import KEYWORDS_BIO, KEYWORDS_README, ITALIAN_LOCATIONS, NEARBY_CITIES, REQUEST_DELAY
from datetime import datetime, timezone
from .github_api import get_user_info, get_user_repos, get_repo_readme, extract_email_from_text
import time

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


def build_user_document(username, max_repos=5):
    """
    Costruisce un documento utente arricchito con:
    - Info profilo
    - Info repos
    - Keywords
    - Email estratte
    - Score euristico
    """
    info = get_user_info(username)
    if not info:
        return None

    # Profilo base
    user_doc = {
        "username": info.get("login"),
        "name": info.get("name"),
        "bio": info.get("bio"),
        "location": info.get("location"),
        "company": info.get("company"),
        "email_public": info.get("email"),
        "followers": info.get("followers", 0),
        "following": info.get("following", 0),
        "public_repos": info.get("public_repos", 0),
        "public_gists": info.get("public_gists", 0),
        "created_at": info.get("created_at"),
        "updated_at": info.get("updated_at"),
        "scraped_at": datetime.now(timezone.utc),  # coerente con timezone UTC
    }

    # Repos info
    repos = get_user_repos(username, max_repos=max_repos)
    total_stars = sum(r["stars"] for r in repos)
    total_forks = sum(r["forks"] for r in repos)
    main_languages = list({r["language"] for r in repos if r["language"]})

    last_commit_days = None
    if repos:
        updates = [r["updated_at"] for r in repos if r.get("updated_at")]
        if updates:
            latest_update = max(updates)
            latest_dt = datetime.fromisoformat(latest_update.replace("Z", "+00:00"))
            last_commit_days = (datetime.now(timezone.utc) - latest_dt).days

    user_doc.update({
        "n_repos_checked": len(repos),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "main_languages": main_languages,
        "last_commit_days": last_commit_days,
    })

    # Keywords check
    bio = (user_doc["bio"] or "").lower()
    user_doc["bio_keywords_hit"] = sum(1 for kw in KEYWORDS_BIO if kw.lower() in bio)

    readme_hits = 0
    sample_readme = ""
    for repo in repos:
        readme = get_repo_readme(repo["full_name"]).lower()
        if not sample_readme:  # salvo solo il primo README per esempio
            sample_readme = readme[:2000]
        readme_hits += sum(1 for kw in KEYWORDS_README if kw.lower() in readme)
        time.sleep(REQUEST_DELAY)
    user_doc["readme_keywords_hit"] = readme_hits
    user_doc["sample_readme"] = sample_readme

    # Email extraction
    email = None
    if sample_readme:
        email = extract_email_from_text(sample_readme)
    user_doc["email_extracted"] = email

    # Heuristic score
    user_doc["heuristic_score"] = score_user(info, max_repos=max_repos)

    return user_doc
