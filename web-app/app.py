from io import BytesIO
import threading
import logging
from flask import Flask, render_template, redirect, send_file, url_for, flash, request, jsonify, Response, send_from_directory
import json
import requests, time, joblib
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import build_user_document, extract_features
from loguru import logger
import pandas as pd
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraping1')))
from dotenv import load_dotenv
from flask_mail import Mail, Message
from db import collection
from utils_github import follow_user_api, is_followed, extract_email_from_github_profile, get_my_followers, get_my_following
from scraping1.github_api import get_candidate_users_advanced, get_user_info
from scraping1.scoring import score_user, build_user_document
from scraping1.storage import save_user
from threading import Lock
from ml_model import query_uncertain, NUM_FEATURES, CAT_FEATURES, TEXT_FEATURE

new_users_buffer = []
buffer_lock = Lock()
# ==============================================================
# Config logging
# ==============================================================
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ==============================================================
# Carica variabili da .env
# ==============================================================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

# Configurazione Flask-Mail (opzionale)
app.config['MAIL_SERVER'] = os.getenv("EMAIL_HOST")
app.config['MAIL_PORT'] = int(os.getenv("EMAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASSWORD")
mail = Mail(app)

DEBUG_EMAIL = os.getenv("DEBUG_EMAIL")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# Parametri scraping presi dal .env
MY_CITY = os.getenv("MY_CITY", "Rome")
NEARBY_CITIES = os.getenv("NEARBY_CITIES", "").split(",")
KEYWORDS_BIO = os.getenv("KEYWORDS_BIO", "").split(",")
KEYWORDS_README = os.getenv("KEYWORDS_README", "").split(",")
ITALIAN_LOCATIONS = os.getenv("ITALIAN_LOCATIONS", "").split(",")
N_USERS = int(os.getenv("N_USERS", 10))
REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", 5))
GITHUB_API = "https://api.github.com"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
KEY_USERS = ["MorenoLaQuatra", "rennf93", "GiovanniIacuzzo"]

# ==============================================================
# Variabili globali
# ==============================================================
scraping_in_progress = False
new_users_buffer = []
buffer_lock = Lock()

# ==============================================================
# ROTTE
# ==============================================================

@app.route("/")
def index():
    city_filter = request.args.get("city", "").strip()
    min_followers = int(request.args.get("min_followers", 0))
    keyword_filter = request.args.get("keyword", "").strip().lower()
    sort_by = request.args.get("sort_by", "score")
    sort_dir = -1

    query = {}
    if city_filter:
        query["location"] = {"$regex": city_filter, "$options": "i"}
    if min_followers > 0:
        query["followers"] = {"$gte": min_followers}
    if keyword_filter:
        query["bio"] = {"$regex": keyword_filter, "$options": "i"}

    users_cursor = collection.find(query).sort(sort_by, sort_dir)
    users = []
    for u in users_cursor:
        u["bio"] = u.get("bio") or "—"
        u["location"] = u.get("location") or "—"
        u["followers"] = u.get("followers") or 0
        u["following"] = u.get("following") or 0
        u["email_to_notify"] = u.get("email_to_notify") or extract_email_from_github_profile(u["username"])
        u["github_url"] = u.get("github_url") or f"https://github.com/{u['username']}"
        users.append(u)

    return render_template(
        "index.html",
        users=users,
        filters={
            "city": city_filter,
            "min_followers": min_followers,
            "keyword": keyword_filter,
            "sort_by": sort_by
        },
        debug_email=str(DEBUG_EMAIL).lower() == "true",
        MY_CITY=MY_CITY,
        NEARBY_CITIES=NEARBY_CITIES,
        KEYWORDS_BIO=KEYWORDS_BIO,
        KEYWORDS_README=KEYWORDS_README
    )

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# --- Follow/Unfollow / Email --- #

@app.route("/follow/<username>")
def follow_user(username):
    if is_followed(username):
        flash(f"Hai già seguito {username} ✅", "info")
    elif follow_user_api(username):
        flash(f"Hai seguito {username} ✅", "success")
    else:
        flash(f"Errore nel seguire {username}", "danger")
    return redirect(url_for("index"))

@app.route("/send_email/<username>")
def send_email(username):
    if not app.config['MAIL_SERVER']:
        flash("Configurazione email mancante ❌", "warning")
        return redirect(url_for("index"))

    user = collection.find_one({"username": username})
    if not user:
        flash(f"Utente {username} non trovato ❌", "danger")
        return redirect(url_for("index"))

    recipient_email = user.get("email_to_notify")
    if str(DEBUG_EMAIL).lower() == "true":
        recipient_email = os.getenv("DEBUG_EMAIL")
    if not recipient_email:
        flash(f"Nessuna email disponibile per {username} ❌", "warning")
        return redirect(url_for("index"))

    try:
        from utils import read_html_template
        html_template, error = read_html_template("email_message.html")
        if not html_template:
            flash(f"Errore lettura template email: {error}", "danger")
            return redirect(url_for("index"))

        html_body = html_template.replace("{username}", username).replace(
            "{my_github}", os.getenv("MY_GITHUB_PROFILE", "https://github.com/GiovanniIacuzzo")
        )

        msg = Message(
            subject=f"[DEBUG] Test Email per {username}" if str(DEBUG_EMAIL).lower() == "true" else f"Ciao {username}, voglio connettermi con te!",
            sender=os.getenv("EMAIL_USER"),
            recipients=[recipient_email],
            html=html_body
        )

        logger.info(f"[MAIL] Inviando email a {recipient_email}")
        mail.send(msg)
        flash(f"Email inviata a {recipient_email} ✅", "success")
    except Exception as e:
        logger.error(f"[ERROR] Invio email fallito: {e}", exc_info=True)
        flash(f"Errore invio email: {e}", "danger")

    return redirect(url_for("index"))

@app.route("/my_profile")
def my_profile_view():
    # ===== Dati reali dei followers/following =====
    followers = get_my_followers()
    following = get_my_following()
    all_users = sorted(set(followers + following), key=lambda x: x.lower())
    users_status = [
        {"username": u, "is_follower": u in followers, "is_following": u in following} 
        for u in all_users
    ]

    # ===== Dati dei grafici (qui puoi sostituire con dati reali dal DB) =====
    followers_distribution = {
        "usernames": ["user1", "user2", "user3"],
        "followers": [10, 5, 15]
    }

    city_heatmap = {
        "cities": ["Roma", "Milano", "Torino"],
        "counts": [[5, 2, 3]]  # array 2D per heatmap
    }

    growth_trend = {
        "dates": ["2025-09-01", "2025-09-05", "2025-09-10"],
        "counts": [50, 75, 120]
    }

    return render_template(
        "my_profile.html",
        users=users_status,
        followers_distribution=json.dumps(followers_distribution),
        city_heatmap=json.dumps(city_heatmap),
        growth_trend=json.dumps(growth_trend)
    )

@app.route("/unfollow/<username>")
def unfollow_user(username):
    from utils_github import unfollow_user_api
    if unfollow_user_api(username):
        flash(f"Hai smesso di seguire {username} ✅", "success")
    else:
        flash(f"Errore nello smettere di seguire {username}", "danger")
    return redirect(url_for("my_profile"))

# --- Refresh DB --- #

@app.route("/refresh_db")
def refresh_db():
    try:
        result = collection.delete_many({})
        flash(f"Database svuotato: {result.deleted_count} utenti rimossi ✅", "success")
    except Exception as e:
        logger.error(f"[ERROR] Errore nel refresh del DB: {e}", exc_info=True)
        flash(f"Errore nel refresh del DB: {e}", "danger")
    return redirect(url_for("index"))

# ==============================================================
# Scraping asincrono
# ==============================================================

@app.route("/run_scraper_async")
def run_scraper_async():
    global scraping_in_progress
    if scraping_in_progress:
        flash("Lo scraping è già in corso ⏳", "info")
        return redirect(url_for("index"))

    scraping_in_progress = True
    threading.Thread(target=_scraper_thread, daemon=True).start()
    flash("Scraping avviato! Gli utenti appariranno gradualmente 🔄", "success")
    return redirect(url_for("index"))

def _scraper_thread():
    """
    Scraping avanzato e stabile degli utenti GitHub
    """
    global scraping_in_progress, new_users_buffer
    try:
        scraping_in_progress = True
        logger.info(f"[SCRAPER] Avvio scraping per {N_USERS} utenti")

        # --- Normalizza le keyword con virgolette per query pulite ---
        bio_keywords = [k.strip() for k in KEYWORDS_BIO if k.strip()]
        readme_keywords = [k.strip() for k in KEYWORDS_README if k.strip()]

        # --- Set unico di città: se NEARBY_CITIES vuoto cerca tutta Italia ---
        cities_to_search = [MY_CITY] + [c for c in NEARBY_CITIES if c.strip()]
        if not cities_to_search:
            cities_to_search = []  # vuoto significa senza filtro città

        collected_users = set()
        users_needed = N_USERS

        # Ricerca per città (o senza città) e keywords
        for loc in cities_to_search or [None]:  # None = ricerca senza location specifica
            if users_needed <= 0:
                break

            for bio_kw in bio_keywords:
                if users_needed <= 0:
                    break
                for readme_kw in readme_keywords:
                    if users_needed <= 0:
                        break

                    query_users = get_candidate_users_advanced(
                        target_count=users_needed,
                        location=loc,
                        keywords_bio=[bio_kw],
                        keywords_readme=[readme_kw],
                        locations=ITALIAN_LOCATIONS  # fallback locations
                    )

                    for username in query_users:
                        if username in collected_users:
                            continue
                        collected_users.add(username)

                        user_doc = build_user_document(username)
                        if not user_doc:
                            continue

                        user_doc["heuristic_score"] = score_user(get_user_info(username))
                        save_user(user_doc)

                        with buffer_lock:
                            new_users_buffer.append({
                                "username": user_doc["username"],
                                "bio": user_doc.get("bio", ""),
                                "location": user_doc.get("location", ""),
                                "followers": user_doc.get("followers", 0),
                                "following": user_doc.get("following", 0),
                                "email_to_notify": user_doc.get("email_extracted") or user_doc.get("email_public"),
                                "score": user_doc.get("heuristic_score", 0)
                            })

                        logger.info(f"[SCRAPER] Salvato {username} (score: {user_doc.get('heuristic_score')})")
                        users_needed -= 1
                        time.sleep(REQUEST_DELAY)

    except Exception as e:
        logger.error(f"[ERROR] Durante scraping: {e}", exc_info=True)
    finally:
        scraping_in_progress = False
        logger.info("[SCRAPER] Completato scraping")

@app.route("/get_new_users")
def get_new_users():
    global new_users_buffer
    with buffer_lock:
        users_to_send = new_users_buffer.copy()
        new_users_buffer.clear()
    return jsonify(users_to_send)

@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        updates = {
            "MY_CITY": request.form.get("MY_CITY", MY_CITY),
            "NEARBY_CITIES": request.form.get("NEARBY_CITIES", ",".join(NEARBY_CITIES)),
            "KEYWORDS_BIO": request.form.get("KEYWORDS_BIO", ",".join(KEYWORDS_BIO)),
            "KEYWORDS_README": request.form.get("KEYWORDS_README", ",".join(KEYWORDS_README)),
            "ITALIAN_LOCATIONS": request.form.get("ITALIAN_LOCATIONS", ",".join(ITALIAN_LOCATIONS)),
            "N_USERS": request.form.get("N_USERS", N_USERS)
        }

        # Aggiorna il file .env
        with open(".env", "r") as f:
            lines = f.readlines()
        with open(".env", "w") as f:
            for line in lines:
                key = line.split("=")[0]
                if key in updates:
                    f.write(f"{key}={updates[key]}\n")
                else:
                    f.write(line)

        flash("Configurazione aggiornata ✅. Riavvia l’app per applicare i cambiamenti.", "success")
        # ➡ Reindirizza direttamente alla dashboard
        return redirect(url_for("index"))

    return render_template("config.html",
                           MY_CITY=MY_CITY,
                           NEARBY_CITIES=",".join(NEARBY_CITIES),
                           KEYWORDS_BIO=",".join(KEYWORDS_BIO),
                           KEYWORDS_README=",".join(KEYWORDS_README),
                           ITALIAN_LOCATIONS=",".join(ITALIAN_LOCATIONS),
                           N_USERS=N_USERS)

# --- Invio email manuale --- #
@app.route("/manual_email", methods=["GET", "POST"])
def manual_email():
    if request.method == "POST":
        recipient_email = request.form.get("email")
        custom_message = request.form.get("message")

        if not recipient_email:
            flash("Inserisci un'email valida ❌", "danger")
            return redirect(url_for("manual_email"))

        try:
            # Leggi il template HTML predefinito
            from utils import read_html_template
            html_template, error = read_html_template("email_message.html")
            if not html_template:
                flash(f"Errore lettura template email: {error}", "danger")
                return redirect(url_for("manual_email"))

            # Usa messaggio custom se fornito, altrimenti template di default
            if custom_message:
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <body>
                <p>{custom_message}</p>
                </body>
                </html>
                """
            else:
                html_body = html_template.replace("{username}", "Ciao!").replace(
                    "{my_github}", os.getenv("MY_GITHUB_PROFILE", "https://github.com/GiovanniIacuzzo")
                )

            msg = Message(
                subject="Ciao, voglio connettermi con te!",
                sender=os.getenv("EMAIL_USER"),
                recipients=[recipient_email],
                html=html_body
            )

            if str(DEBUG_EMAIL).lower() == "true":
                # Override email in debug
                msg.recipients = [os.getenv("DEBUG_EMAIL")]

            mail.send(msg)
            flash(f"Email inviata a {recipient_email} ✅", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Errore invio email: {e}", "danger")
            return redirect(url_for("manual_email"))

    return render_template("manual_email.html")

@app.route("/save_annotation", methods=["POST"])
def save_annotation():
    data = request.get_json()
    username = data.get("username")
    annotation = data.get("annotation", "")

    if not username:
        return jsonify({"success": False, "error": "Username mancante"}), 400

    try:
        collection.update_one(
            {"username": username},
            {"$set": {"annotation": annotation}}
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"[ERROR] Salvataggio annotazione fallito: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/export_csv")
def export_csv():
    users_cursor = collection.find()
    
    # Nome colonne CSV
    fieldnames = [
        "username", "name", "bio", "location", "followers", "following",
        "email",  # colonna unica per email
        "annotation",  # aggiunta colonna annotazioni
        "heuristic_score", "public_repos", "public_gists", "company",
        "main_languages", "total_stars", "total_forks", "created_at", "updated_at"
    ]

    # Genera CSV in memoria
    def generate():
        yield ",".join(fieldnames) + "\n"
        for u in users_cursor:
            row = []

            # email unificata
            email = u.get("email_to_notify") or u.get("email_extracted") or u.get("email_public") or ""

            for f in fieldnames:
                if f == "email":
                    val = email
                elif f == "annotation":
                    val = u.get("annotation", "")
                else:
                    val = u.get(f, "")
                # Se è lista, convertila in stringa separata da ;
                if isinstance(val, list):
                    val = ";".join(map(str, val))
                # Escape delle virgole e ritorni a capo
                val = str(val).replace("\n", " ").replace("\r", " ").replace(",", ";")
                row.append(val)
            yield ",".join(row) + "\n"

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=utenti.csv"})

@app.route("/active_learning_candidates", methods=["GET"])
def active_learning_candidates():
    try:
        # Mostra tutti gli utenti senza annotazione
        users = list(collection.find({"annotation": {"$exists": False}}))
        # Ordina per pred_prob decrescente per priorità nella UI
        users.sort(key=lambda x: x.get("pred_prob", 0), reverse=True)
        # Converti in JSON
        result = [{
            "username": u["username"],
            "bio": u.get("bio", ""),
            "location": u.get("location", ""),
            "followers": u.get("followers", 0),
            "following": u.get("following", 0),
            "pred_prob": u.get("pred_prob", 0)
        } for u in users]
        return jsonify(result), 200
    except Exception as e:
        logger.exception("[ACTIVE-LEARNING] Errore caricamento candidati")
        return jsonify([]), 500

# --- Retrain Model --- #
@app.route("/retrain_model")
def retrain_model():
    try:
        from ml_model import train_model
        print("[INFO] Avvio training modello...")
        model = train_model()
        if model:
            flash("Modello riaddestrato con successo ✅", "success")
            print("[INFO] Training completato correttamente")
        else:
            flash("Nessun dato annotato, impossibile allenare ❌", "warning")
            print("[WARN] Nessun dato annotato disponibile per il training")
    except Exception as e:
        flash(f"Errore durante il training del modello ❌: {e}", "danger")
        print(f"[ERROR] Errore durante il training: {type(e)} {e}", exc_info=True)
    return redirect(url_for("index"))

@app.route("/active_learning")
def active_learning():
    return render_template("active_learning.html")

@app.route("/search_users")
def search_users():
    q = request.args.get("q", "")
    if not q:
        return jsonify([])
    # ricerca case-insensitive su città o username
    results = list(collection.find({"$or": [
        {"location": {"$regex": q, "$options": "i"}},
        {"username": {"$regex": q, "$options": "i"}}
    ]}).limit(10))
    
    # serializzazione ObjectId in stringa
    for r in results:
        r["_id"] = str(r["_id"])
    return jsonify(results)

@app.route("/export/<fmt>")
def export(fmt):
    users = list(collection.find({}))
    df = pd.DataFrame(users)
    if fmt == "csv":
        return df.to_csv(index=False), 200, {"Content-Disposition":"attachment; filename=users.csv"}
    elif fmt == "excel":
        out = BytesIO()
        df.to_excel(out, index=False)
        out.seek(0)
        return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="users.xlsx")
    elif fmt == "json":
        return jsonify(df.to_dict(orient="records"))
    else:
        return "Formato non supportato", 400
    
@app.route("/get_users_batch")
def get_users_batch():
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 20))
    users = list(collection.find().skip(offset).limit(limit))
    for u in users:
        u["_id"] = str(u["_id"])  # serializzabile
    return jsonify(users)

def get_github_usernames_global(limit=100, since=0):
    """
    Recupera una lista di username GitHub globali senza filtri.
    Usa l'endpoint https://api.github.com/users con paginazione.

    Args:
        limit (int): numero massimo di utenti da restituire
        since (int): ID utente da cui partire (per paginazione)

    Returns:
        list[str]: lista di username GitHub
    """
    usernames = []
    per_page = min(limit, 100)  # max consentito da GitHub

    logger.info(f"[SCRAPE-GLB] Avvio scraping globale utenti GitHub, limit={limit}, since={since}")

    try:
        while len(usernames) < limit:
            url = f"https://api.github.com/users?since={since}&per_page={per_page}"
            resp = requests.get(url, headers=HEADERS)

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

# ==============================================================
# Funzioni ausiliarie (potrebbero stare in un utils_github.py)
# ==============================================================
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
            time.sleep(0.2) # per rispettare i rate limit
        except requests.RequestException as e:
            logger.error(f"Request error for {username} {type}: {e}")
            break
    return users

# Funzione per ottenere info utente, con cache semplice in memoria
# Potresti voler implementare una cache più robusta (es. Redis o MongoDB)
_user_info_cache = {}
_cache_lock = Lock()

def get_user_info_cached(username):
    with _cache_lock:
        if username in _user_info_cache:
            return _user_info_cache[username]
    
    # Controlla prima nel DB se l'utente esiste e ha dati completi
    db_user = collection.find_one({"username": username, "bio": {"$exists": True}, "location": {"$exists": True}})
    if db_user:
        # Costruisci un dict simile a quello dell'API GitHub per coerenza
        cached_info = {
            "username": db_user["username"],
            "followers": db_user.get("followers", 0),
            "following": db_user.get("following", 0),
            "public_repos": db_user.get("public_repos", 0),
            "public_gists": db_user.get("public_gists", 0),
            "bio": db_user.get("bio", ""),
            "location": db_user.get("location", ""),
            "company": db_user.get("company", ""),
            # Altri campi che potrebbero servire al modello ML
        }
        with _cache_lock:
            _user_info_cache[username] = cached_info
        return cached_info

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
                _user_info_cache[username] = None # Cache this too to avoid repeated calls for non-existent users
            return None
        else:
            logger.warning(f"Failed to get user info for {username}: {resp.status_code} - {resp.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"Request error for user {username}: {e}")
        return None

# ==============================================================
# ROTTE (omesse per brevità, assumiamo siano le stesse)
# ==============================================================

# Questa è la funzione che hai già e che preleva utenti globali.
# Assicurati che sia definita altrove (es. utils_github.py) o qui.
def get_github_usernames_global(limit=100, since=0):
    """
    Recupera una lista di username GitHub globali senza filtri.
    Usa l'endpoint https://api.github.com/users con paginazione.

    Args:
        limit (int): numero massimo di utenti da restituire
        since (int): ID utente da cui partire (per paginazione)

    Returns:
        list[str]: lista di username GitHub
    """
    usernames = []
    per_page = min(limit, 100)  # max consentito da GitHub

    logger.info(f"[SCRAPE-GLB] Avvio scraping globale utenti GitHub, limit={limit}, since={since}")

    try:
        while len(usernames) < limit:
            url = f"https://api.github.com/users?since={since}&per_page={per_page}"
            resp = requests.get(url, headers=HEADERS)

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


@app.route("/scrape_with_ml", methods=["POST"])
def scrape_with_ml():
    try:
        requested_limit = int(request.args.get("limit", 5)) # Il limite richiesto dall'utente
        # La soglia di incertezza è per gli utenti che vogliamo ANNOTARE
        initial_uncertainty_range = float(request.args.get("uncertainty_range", 0.1)) 
        # Soglia per gli utenti che vogliamo considerare "promettenti" e proporre come "follow"
        promising_threshold = float(request.args.get("promising_threshold", 0.75)) # Nuova soglia per utenti "buoni"

        logger.info(f"[ML-SCRAPE] Avvio scraping attivo (limit={requested_limit}, uncertainty_range={initial_uncertainty_range}, promising_threshold={promising_threshold})")
        
        try:
            model = joblib.load("models/github_user_classifier.pkl")
            logger.info("Modello ML caricato.")
        except FileNotFoundError:
            logger.error("Modello ML non trovato! Assicurati che 'github_user_classifier.pkl' esista in 'models/'.")
            return jsonify({"success": False, "error": "Modello ML non trovato. Effettua un training prima."}), 500
        except Exception as e:
            logger.error(f"Errore caricamento modello ML: {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Errore caricamento modello ML: {str(e)}"}), 500

        # Liste per gli utenti trovati
        found_uncertain_users = [] # Utenti con probabilità ~0.5, buoni per l'annotazione
        found_promising_users = [] # Utenti con alta probabilità, buoni da seguire
        processed_usernames_this_run = set() # Per tenere traccia degli utenti processati in questa esecuzione

        # 1. Recupera candidati da varie fonti
        candidate_usernames = set()
        
        logger.info("[ML-SCRAPE] Raccolta candidati dai KEY_USERS (follower/following)...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_key_user = {executor.submit(get_followers_or_following, ku, type): (ku, type) 
                                  for ku in KEY_USERS for type in ["followers", "following"]}
            for future in as_completed(future_to_key_user):
                key_user, type = future_to_key_user[future]
                try:
                    usernames = future.result()
                    candidate_usernames.update(usernames)
                    logger.info(f"  Trovati {len(usernames)} {type} per {key_user}")
                except Exception as exc:
                    logger.error(f"  Errore nel recupero {type} per {key_user}: {exc}")

        # Aggiungi una fonte più ampia se i candidati sono pochi (aumentato il limite per un pool più grande)
        if len(candidate_usernames) < 100: # Aumentato il limite
            logger.info(f"[ML-SCRAPE] Candidati attuali insufficienti ({len(candidate_usernames)}). Aggiungo da scraping globale.")
            # Aumentiamo il limite per lo scraping globale per avere più varietà
            global_users = get_github_usernames_global(limit=500, since=0) 
            candidate_usernames.update(global_users)
            logger.info(f"[ML-SCRAPE] Totale candidati dopo globale: {len(candidate_usernames)}")
        
        # Filtra utenti già annotati o presenti nel DB
        # Escludi utenti che sono già stati annotati come "Non valido" (0) o "Promettente" (1)
        # E quelli che hanno già una predizione nel DB, per evitare di ricalcolare e riproporre.
        existing_annotated_usernames = {u["username"] for u in collection.find({"annotation": {"$exists": True}}, {"username": 1})}
        existing_predicted_usernames = {u["username"] for u in collection.find({"pred_prob": {"$exists": True}}, {"username": 1})}
        
        candidate_usernames = [u for u in candidate_usernames if u not in existing_annotated_usernames and u not in existing_predicted_usernames]

        if not candidate_usernames:
            logger.info("[ML-SCRAPE] Nessun nuovo candidato da valutare. Prova a svuotare il DB o a modificare i KEY_USERS.")
            return jsonify({"success": False, "error": "Nessun nuovo candidato trovato per la valutazione. Tutti gli utenti pertinenti sono già stati processati o annotati."}), 200

        # Rimescola i candidati per evitare bias nell'ordine e trovare più varietà
        import random
        random.shuffle(candidate_usernames)

        logger.info(f"[ML-SCRAPE] Inizio valutazione ML su {len(candidate_usernames)} candidati unici.")

        # 2. Valutazione ML per batch, cercando sia incerti che promettenti
        batch_size = 50 
        
        # Variabili per la strategia ibrida
        max_evaluation_batches = 100 # Limite per evitare loop infiniti se non si trovano utenti
        batches_processed = 0

        # Loop principale: continua a processare batch finché non raggiungiamo il limite richiesto
        # o esauriamo i candidati da valutare.
        while (len(found_uncertain_users) < requested_limit or len(found_promising_users) < requested_limit) \
              and candidate_usernames and batches_processed < max_evaluation_batches:
            
            batches_processed += 1
            batch_start_time = time.time()
            
            # Prepara gli utenti del batch per il fetching delle info
            users_to_fetch_info = []
            for _ in range(min(batch_size, len(candidate_usernames))):
                users_to_fetch_info.append(candidate_usernames.pop(0)) # Prende e rimuove dal set per evitare duplicati nel batch
            
            if not users_to_fetch_info:
                logger.info("[ML-SCRAPE] Esauriti i candidati nel pool. Fine ricerca.")
                break

            # Parallel fetch info utenti per il batch corrente
            batch_user_docs = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_user = {executor.submit(get_user_info_cached, u): u for u in users_to_fetch_info}
                for future in as_completed(future_to_user):
                    username = future_to_user[future]
                    processed_usernames_this_run.add(username) # Marca come processato
                    
                    try:
                        user_info = future.result()
                        # Filtro più robusto: almeno 5 repo pubblici E non bot/user bloccati (se l'API lo permette)
                        if not user_info or user_info.get("public_repos", 0) < 5 or user_info.get("type") != "User": 
                            logger.debug(f"  Skipping {username}: no info, few public repos, or not a regular user.")
                            continue
                        
                        doc = {
                            "username": username,
                            "followers": user_info.get("followers", 0),
                            "following": user_info.get("following", 0),
                            "public_repos": user_info.get("public_repos", 0),
                            "public_gists": user_info.get("public_gists", 0),
                            "bio": user_info.get("bio", ""),
                            "location": user_info.get("location", ""),
                            "company": user_info.get("company", ""),
                            "email_to_notify": extract_email_from_github_profile(username),
                            "github_url": user_info.get("html_url", f"https://github.com/{username}")
                        }
                        batch_user_docs.append(doc)
                    except Exception as exc:
                        logger.error(f"  Errore fetching info per {username}: {exc}")
            
            if not batch_user_docs:
                logger.info("[ML-SCRAPE] Nessun utente valido trovato nel batch attuale.")
                continue

            # Predizione ML per il batch
            df_batch_features = pd.DataFrame([extract_features(doc) for doc in batch_user_docs])
            
            for c in NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]:
                if c not in df_batch_features.columns:
                    df_batch_features[c] = "" if c in CAT_FEATURES + [TEXT_FEATURE] else 0
            df_batch_features = df_batch_features[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]]

            probabilities = model.predict_proba(df_batch_features)[:, 1]
            
            for i, user_doc in enumerate(batch_user_docs):
                prob = round(float(probabilities[i]), 3)
                user_doc["pred_prob"] = prob

                # Salva l'utente nel DB con la predizione (upsert)
                collection.update_one({"username": user_doc["username"]}, {"$set": user_doc}, upsert=True)
                
                # Valuta se l'utente è incerto o promettente
                lower_bound_uncertain = 0.5 - initial_uncertainty_range
                upper_bound_uncertain = 0.5 + initial_uncertainty_range

                if lower_bound_uncertain <= prob <= upper_bound_uncertain and len(found_uncertain_users) < requested_limit:
                    found_uncertain_users.append(user_doc)
                    logger.debug(f"  Trovato utente incerto: {user_doc['username']} (prob: {prob:.2f})")
                elif prob >= promising_threshold and len(found_promising_users) < requested_limit:
                    found_promising_users.append(user_doc)
                    logger.debug(f"  Trovato utente promettente: {user_doc['username']} (prob: {prob:.2f})")
            
            logger.info(f"[ML-SCRAPE] Batch took {time.time() - batch_start_time:.2f}s. Uncertain: {len(found_uncertain_users)}, Promising: {len(found_promising_users)}. Total candidates left: {len(candidate_usernames)}")
            
            # Se abbiamo trovato abbastanza utenti (incerti E/O promettenti)
            if len(found_uncertain_users) >= requested_limit and len(found_promising_users) >= requested_limit:
                break # Abbiamo abbastanza di entrambi, possiamo fermarci

        # 3. Costruisci la lista finale dando priorità agli incerti per l'Active Learning
        final_users_for_ui = []
        
        # Prima gli utenti incerti (che sono i più preziosi per l'Active Learning)
        # Li ordiniamo per probabilità più vicina a 0.5 (valore assoluto della differenza)
        found_uncertain_users.sort(key=lambda x: abs(x["pred_prob"] - 0.5))
        
        # Poi gli utenti promettenti, ordinati dalla probabilità più alta
        found_promising_users.sort(key=lambda x: x["pred_prob"], reverse=True)

        # Prendi una proporzione di incerti e poi riempi con i promettenti
        # Ad esempio, il 50% del limite richiesto come incerti, il resto come promettenti
        num_uncertain_to_take = min(requested_limit // 2, len(found_uncertain_users))
        num_promising_to_take = requested_limit - num_uncertain_to_take

        final_users_for_ui.extend(found_uncertain_users[:num_uncertain_to_take])
        
        # Aggiungi promettenti finché non raggiungi il limite o non ne hai più
        for user in found_promising_users:
            # Assicurati di non aggiungere duplicati (anche se i set iniziali dovrebbero averli filtrati)
            if user["username"] not in {u["username"] for u in final_users_for_ui}:
                final_users_for_ui.append(user)
            if len(final_users_for_ui) >= requested_limit:
                break
        
        # Se ancora non abbiamo raggiunto il limite, aggiungi altri incerti
        # (se non sono già stati aggiunti dalla prima selezione)
        if len(final_users_for_ui) < requested_limit:
            for user in found_uncertain_users[num_uncertain_to_take:]:
                if user["username"] not in {u["username"] for u in final_users_for_ui}:
                    final_users_for_ui.append(user)
                if len(final_users_for_ui) >= requested_limit:
                    break

        # Ultimo controllo per assicurarsi che la lista sia esattamente della dimensione richiesta
        final_users_for_ui = final_users_for_ui[:requested_limit]

        logger.info(f"[ML-SCRAPE] Scraping completato. Restituiti {len(final_users_for_ui)} utenti per l'annotazione (o follow).")
        return jsonify({"success": True, "users": final_users_for_ui, "inserted": len(final_users_for_ui)}), 200

    except Exception as e:
        logger.exception("[ML-SCRAPE] Errore generale durante lo scraping ML:")
        return jsonify({"success": False, "error": str(e)}), 500
    
# ==============================================================
# AVVIO FLASK
# ==============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)
