from flask import Blueprint, render_template, request, send_from_directory
from db import collection
import os
from config import (
    DEBUG_EMAIL,
    MY_CITY,
    NEARBY_CITIES,
    KEYWORDS_BIO,
    KEYWORDS_README,
)

# Importa ma non chiamare fetch esterno a ogni render
def safe_email(username):
    # Temporaneamente ritorna una email finta per test
    return "test@example.com"

main_bp = Blueprint("main", __name__)

# ==============================================================
# Homepage con tabella utenti
# ==============================================================

@main_bp.route("/")
def index():
    city_filter = request.args.get("city", "").strip()
    min_followers = int(request.args.get("min_followers", 0))
    keyword_filter = request.args.get("keyword", "").strip().lower()
    sort_by = request.args.get("sort_by", "score")
    sort_dir = -1  # default: desc

    # Query semplificata per test
    query = {}
    if city_filter:
        query["location"] = {"$regex": city_filter, "$options": "i"}
    if min_followers > 0:
        query["followers"] = {"$gte": min_followers}
    if keyword_filter:
        query["bio"] = {"$regex": keyword_filter, "$options": "i"}

    # Recupero utenti dal DB (limit 20 per test rapido)
    users_cursor = collection.find(query).sort(sort_by, sort_dir).limit(20)
    users = []
    for u in users_cursor:
        users.append({
            "username": u.get("username", "—"),
            "bio": u.get("bio") or "—",
            "location": u.get("location") or "—",
            "followers": u.get("followers", 0),
            "following": u.get("following", 0),
            "email_to_notify": u.get("email_to_notify") or safe_email(u.get("username", "")),
            "github_url": u.get("github_url") or f"https://github.com/{u.get('username', '')}",
            "score": u.get("score", 0),
            "annotation": u.get("annotation", "")
        })

    print(f"Trovati {len(users)} utenti")  # debug

    return render_template(
        "index.html",
        users=users,
        filters={
            "city": city_filter,
            "min_followers": min_followers,
            "keyword": keyword_filter,
            "sort_by": sort_by,
        },
        debug_email=str(DEBUG_EMAIL).lower() == "true",
        MY_CITY=MY_CITY,
        NEARBY_CITIES=NEARBY_CITIES,
        KEYWORDS_BIO=KEYWORDS_BIO,
        KEYWORDS_README=KEYWORDS_README,
    )

# ==============================================================
# Favicon
# ==============================================================

@main_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(main_bp.root_path, "..", "static", "img"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon"
    )
