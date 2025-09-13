import time
import threading
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraping1')))
from dotenv import load_dotenv
from flask_mail import Mail, Message
from .db import collection
from .utils_github import follow_user_api, is_followed, extract_email_from_github_profile
from .scraping1.config import N_USERS, REQUEST_DELAY
from .scraping1.github_api import get_candidate_users_advanced, get_user_info
from .scraping1.scoring import score_user
from .scraping1.storage import save_user

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Configurazione Flask-Mail
app.config['MAIL_SERVER'] = os.getenv("EMAIL_HOST")
app.config['MAIL_PORT'] = int(os.getenv("EMAIL_PORT"))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASSWORD")
mail = Mail(app)

DEBUG_EMAIL = os.getenv("DEBUG_EMAIL")

# ==============================================================
# Variabili globali per lo scraping asincrono
# ==============================================================
scraping_in_progress = False
new_users_buffer = []

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
        debug_email=str(DEBUG_EMAIL).lower() == "true"
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

        print(f"[DEBUG] Inviando email a {recipient_email}")
        mail.send(msg)
        flash(f"Email inviata a {recipient_email} ✅", "success")
    except Exception as e:
        print(f"[ERROR] Invio email fallito: {e}")
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
        print(f"[ERROR] Errore nel refresh del DB: {e}")
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
    threading.Thread(target=_scraper_thread).start()
    flash("Scraping avviato! Gli utenti appariranno gradualmente 🔄", "success")
    return redirect(url_for("index"))

def _scraper_thread():
    global scraping_in_progress, new_users_buffer
    try:
        candidate_users = get_candidate_users_advanced(N_USERS)
        for username in candidate_users:
            info = get_user_info(username)
            if not info:
                continue
            score = score_user(info)
            email = extract_email_from_github_profile(username)
            user_doc = {
                "username": username,
                "bio": info.get("bio") or "",
                "location": info.get("location") or "",
                "followers": info.get("followers") or 0,
                "following": info.get("following") or 0,
                "email_to_notify": email,
                "score": score
            }
            save_user(user_doc)
            new_users_buffer.append(user_doc)  # aggiunge utente al buffer
            time.sleep(REQUEST_DELAY)
    except Exception as e:
        print(f"[ERROR] Durante scraping: {e}")
    finally:
        scraping_in_progress = False

@app.route("/get_new_users")
def get_new_users():
    global new_users_buffer
    users_to_send = new_users_buffer.copy()
    new_users_buffer.clear()
    return jsonify(users_to_send)

# ==============================================================
# AVVIO FLASK
# ==============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)
