import time
import threading
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, Response
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraping1')))
from dotenv import load_dotenv
from flask_mail import Mail, Message
from db import collection
from utils_github import follow_user_api, is_followed, extract_email_from_github_profile
from scraping1.github_api import get_candidate_users_advanced, get_user_info
from scraping1.scoring import score_user, build_user_document
from scraping1.storage import save_user
from threading import Lock
import csv

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

# Parametri scraping presi dal .env
MY_CITY = os.getenv("MY_CITY", "Rome")
NEARBY_CITIES = os.getenv("NEARBY_CITIES", "").split(",")
KEYWORDS_BIO = os.getenv("KEYWORDS_BIO", "").split(",")
KEYWORDS_README = os.getenv("KEYWORDS_README", "").split(",")
ITALIAN_LOCATIONS = os.getenv("ITALIAN_LOCATIONS", "").split(",")
N_USERS = int(os.getenv("N_USERS", 10))
REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", 5))

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
def my_profile():
    from utils_github import get_my_followers, get_my_following
    followers = get_my_followers()
    following = get_my_following()
    all_users = sorted(set(followers + following), key=lambda x: x.lower())
    users_status = [{"username": u, "is_follower": u in followers, "is_following": u in following} for u in all_users]
    return render_template("my_profile.html", users=users_status)

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
    global scraping_in_progress, new_users_buffer
    try:
        logger.info(f"[SCRAPER] Avvio scraping con {N_USERS} utenti")
        candidate_users = get_candidate_users_advanced(
            N_USERS,
            my_city=MY_CITY,
            nearby_cities=NEARBY_CITIES,
            keywords_bio=KEYWORDS_BIO,
            keywords_readme=KEYWORDS_README,
            locations=ITALIAN_LOCATIONS
        )
        for username in candidate_users:
            user_doc = build_user_document(username)
            if not user_doc:
                continue

            # calcolo dello score euristico
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

            logger.info(f"[SCRAPER] Salvato {username} con score {user_doc.get('heuristic_score')}")
            time.sleep(REQUEST_DELAY)

    except Exception as e:
        logger.error(f"[ERROR] Durante scraping: {e}", exc_info=True)
    finally:
        scraping_in_progress = False

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

# ==============================================================
# AVVIO FLASK
# ==============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)
