import requests
import time
from io import BytesIO
from threading import Lock
from flask import send_file, jsonify, Blueprint
import pandas as pd
from flask import flash, redirect, url_for
from loguru import logger
from db import collection
from config import HEADERS, GITHUB_API

utils_bp = Blueprint("utils", __name__)

# ==============================
# Export dei dati utenti
# ==============================
@utils_bp.route("/export/<fmt>")
def export(fmt):
    users = list(collection.find({}))
    df = pd.DataFrame(users)
    
    if fmt == "csv":
        return df.to_csv(index=False), 200, {
            "Content-Disposition": "attachment; filename=users.csv",
            "Content-Type": "text/csv"
        }
    elif fmt == "excel":
        out = BytesIO()
        df.to_excel(out, index=False)
        out.seek(0)
        return send_file(
            out,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="users.xlsx"
        )
    elif fmt == "json":
        return jsonify(df.to_dict(orient="records"))
    else:
        return "Formato non supportato", 400

# ==============================
# Scraping globale utenti GitHub
# ==============================
def get_github_usernames_global(limit=100, since=0):
    usernames = []
    per_page = min(limit, 100)  # max consentito da GitHub

    logger.info(f"[SCRAPE-GLB] Avvio scraping globale utenti GitHub, limit={limit}, since={since}")

    try:
        while len(usernames) < limit:
            url = f"{GITHUB_API}/users?since={since}&per_page={per_page}"
            resp = requests.get(url, headers=HEADERS, timeout=5)

            if resp.status_code != 200:
                logger.warning(f"[SCRAPE-GLB] Errore API GitHub status {resp.status_code}: {resp.text}")
                break

            data = resp.json()
            if not data:
                logger.info("[SCRAPE-GLB] Nessun utente restituito, fine paginazione")
                break

            for user in data:
                usernames.append(user["login"])
                since = user["id"]  # aggiorna l'ID per il prossimo batch
                if len(usernames) >= limit:
                    break

            time.sleep(0.5)  # evita rate limit

    except Exception as e:
        logger.error(f"[SCRAPE-GLB] Errore generale: {e}", exc_info=True)

    logger.info(f"[SCRAPE-GLB] Completato, raccolti {len(usernames)} username")
    return usernames

# ==============================
# Recupero followers o following
# ==============================
def get_followers_or_following(username, type="followers", per_page=50):
    users = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{username}/{type}?per_page={per_page}&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=5)
            if resp.status_code != 200:
                logger.warning(f"Failed to get {type} for {username}: {resp.status_code} - {resp.text}")
                break
            data = resp.json()
            if not data:
                break
            users.extend([u["login"] for u in data])
            if len(data) < per_page:
                break
            page += 1
            time.sleep(0.2)  # rispetta rate limit
        except requests.RequestException as e:
            logger.error(f"Request error for {username} {type}: {e}")
            break
    return users

# ==============================
# Cache semplice per info utente
# ==============================
_user_info_cache = {}
_cache_lock = Lock()

def get_user_info_cached(username):
    with _cache_lock:
        if username in _user_info_cache:
            return _user_info_cache[username]

    # Controlla DB
    db_user = collection.find_one(
        {"username": username, "bio": {"$exists": True}, "location": {"$exists": True}}
    )
    if db_user:
        cached_info = {
            "username": db_user["username"],
            "followers": db_user.get("followers", 0),
            "following": db_user.get("following", 0),
            "public_repos": db_user.get("public_repos", 0),
            "public_gists": db_user.get("public_gists", 0),
            "bio": db_user.get("bio", ""),
            "location": db_user.get("location", ""),
            "company": db_user.get("company", ""),
        }
        with _cache_lock:
            _user_info_cache[username] = cached_info
        return cached_info

    # Chiamata API GitHub
    url = f"{GITHUB_API}/users/{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            user_data = resp.json()
            with _cache_lock:
                _user_info_cache[username] = user_data
            return user_data
        elif resp.status_code == 404:
            logger.warning(f"User {username} not found on GitHub (404).")
            with _cache_lock:
                _user_info_cache[username] = None  # evita chiamate ripetute
            return None
        else:
            logger.warning(f"Failed to get user info for {username}: {resp.status_code} - {resp.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"Request error for user {username}: {e}")
        return None


@utils_bp.route("/refresh_db")
def refresh_db():
    try:
        result = collection.delete_many({})
        flash(f"Database svuotato: {result.deleted_count} utenti rimossi ✅", "success")
    except Exception as e:
        logger.error(f"[ERROR] Errore nel refresh del DB: {e}", exc_info=True)
        flash(f"Errore nel refresh del DB: {e}", "danger")
    return redirect(url_for("main.index"))