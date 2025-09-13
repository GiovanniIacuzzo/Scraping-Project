import time
from flask import Flask, render_template, redirect, url_for, flash, request
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraping1')))
from dotenv import load_dotenv
from flask_mail import Mail, Message
from db import collection
from utils_github import follow_user_api, is_followed, extract_email_from_github_profile
from scraping1.config import N_USERS, REQUEST_DELAY
from scraping1.github_api import get_candidate_users_advanced, get_user_info
from scraping1.scoring import score_user
from scraping1.storage import save_user

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

    # Filtro città
    if city_filter:
        query["location"] = {"$regex": city_filter, "$options": "i"}

    # Filtro min followers
    if min_followers > 0:
        query["followers"] = {"$gte": min_followers}

    # Filtro keyword bio
    if keyword_filter:
        query["bio"] = {"$regex": keyword_filter, "$options": "i"}

    # Recupera utenti dal DB ordinati
    users_cursor = collection.find(query).sort(sort_by, sort_dir)
    users = []

    for u in users_cursor:
        # Normalizza campi mancanti
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

    # Usa DEBUG_EMAIL se attivo
    recipient_email = user.get("email_to_notify")
    if str(DEBUG_EMAIL).lower() == "true":
        recipient_email = os.getenv("DEBUG_EMAIL")

    if not recipient_email:
        flash(f"Nessuna email disponibile per {username} ❌", "warning")
        return redirect(url_for("index"))

    try:
        from utils import read_html_template

        # Leggi template HTML
        html_template, error = read_html_template("email_message.html")
        if not html_template:
            flash(f"Errore lettura template email: {error}", "danger")
            return redirect(url_for("index"))

        html_body = html_template.replace("{username}", username).replace(
            "{my_github}", os.getenv("MY_GITHUB_PROFILE", "https://github.com/GiovanniIacuzzo")
        )

        # Prepara messaggio
        msg = Message(
            subject=f"[DEBUG] Test Email per {username}" if str(DEBUG_EMAIL).lower() == "true" else f"Ciao {username}, voglio connettermi con te!",
            sender=os.getenv("EMAIL_USER"),
            recipients=[recipient_email],
            html=html_body
        )

        # Debug: stampa info prima di inviare
        print(f"[DEBUG] Inviando email a {recipient_email} da {os.getenv('EMAIL_USER')} tramite {os.getenv('EMAIL_HOST')}:{os.getenv('EMAIL_PORT')}")

        # Invia
        mail.send(msg)

        flash(f"Email inviata a {recipient_email} ✅", "success")
        print(f"[SUCCESS] Email inviata a {recipient_email}")

    except Exception as e:
        # Mostra errore dettagliato in console
        print(f"[ERROR] Invio email fallito: {e}")
        flash(f"Errore invio email: {e}", "danger")

    return redirect(url_for("index"))

@app.route("/my_profile")
def my_profile():
    from utils_github import get_my_followers, get_my_following

    followers = get_my_followers()
    following = get_my_following()

    # Tutti gli username unici
    all_users = sorted(set(followers + following), key=lambda x: x.lower())

    # Creiamo struttura per template
    users_status = []
    for u in all_users:
        users_status.append({
            "username": u,
            "is_follower": u in followers,
            "is_following": u in following
        })

    return render_template("my_profile.html", users=users_status)

@app.route("/unfollow/<username>")
def unfollow_user(username):
    from utils_github import unfollow_user_api

    if unfollow_user_api(username):
        flash(f"Hai smesso di seguire {username} ✅", "success")
    else:
        flash(f"Errore nello smettere di seguire {username}", "danger")
    return redirect(url_for("my_profile"))

@app.route("/run_scraper")
def run_scraper():
    try:
        candidate_users = get_candidate_users_advanced(N_USERS)
        scored_users = []

        for username in candidate_users:
            info = get_user_info(username)
            if not info:
                print(f"[WARNING] Impossibile recuperare info per {username}")
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
            scored_users.append((username, score))
            print(f"Salvato {username} con punteggio {score}")

            time.sleep(REQUEST_DELAY)

        # Ordina per score
        scored_users.sort(key=lambda x: x[1], reverse=True)
        final_users = [user for user, score in scored_users]
        print("Utenti salvati e ordinati per rilevanza:", final_users)

        flash(f"Scraping completato: {len(scored_users)} utenti aggiornati ✅", "success")
    except Exception as e:
        print(f"[ERROR] Errore durante lo scraping: {e}")
        flash(f"Errore durante lo scraping: {e}", "danger")

    return redirect(url_for("index"))

# ==============================================================
# AVVIO FLASK
# ==============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)

