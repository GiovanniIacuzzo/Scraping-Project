from flask import Flask, render_template, redirect, url_for, flash, request
from pymongo import MongoClient
import requests
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os

# --- Carica variabili .env ---
load_dotenv()

# --- Flask ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- MongoDB ---
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["scraping-project"]
collection = db["users"]

# --- GitHub ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# --- Configurazione Email ---
app.config['MAIL_SERVER'] = os.getenv("EMAIL_HOST")
app.config['MAIL_PORT'] = int(os.getenv("EMAIL_PORT"))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASSWORD")

mail = Mail(app)

# --- Route Dashboard ---
@app.route("/")
def index():
    city_filter = request.args.get("city", "").strip()
    min_followers = int(request.args.get("min_followers", 0))
    keyword_filter = request.args.get("keyword", "").strip().lower()
    sort_by = request.args.get("sort_by", "score")
    sort_dir = -1  # discendente

    # Costruzione query MongoDB
    query = {}
    if city_filter:
        query["location"] = {"$regex": city_filter, "$options": "i"}
    if min_followers > 0:
        query["followers"] = {"$gte": min_followers}
    if keyword_filter:
        query["bio"] = {"$regex": keyword_filter, "$options": "i"}

    users = list(collection.find(query).sort(sort_by, sort_dir))
    return render_template("index.html", users=users, filters={
        "city": city_filter,
        "min_followers": min_followers,
        "keyword": keyword_filter,
        "sort_by": sort_by
    })

# --- Segui utente su GitHub ---
@app.route("/follow/<username>")
def follow_user(username):
    url = f"https://api.github.com/user/following/{username}"
    resp = requests.put(url, headers=HEADERS)

    if resp.status_code in [204, 200]:
        flash(f"Hai seguito {username} ✅", "success")
    else:
        flash(f"Errore nel seguire {username}: {resp.status_code}", "danger")

    return redirect(url_for("index"))

@app.route("/send_email/<username>")
def send_email(username):
    user = collection.find_one({"username": username})
    if not user:
        flash(f"Utente {username} non trovato ❌", "danger")
        return redirect(url_for("index"))

    recipient_email = user.get("email_to_notify")
    if not recipient_email:
        flash(f"L'utente {username} non ha un'email disponibile ❌", "warning")
        return redirect(url_for("index"))

    # Legge template HTML
    try:
        with open("email_message.html", "r", encoding="utf-8") as f:
            html_template = f.read()
    except Exception as e:
        flash(f"Errore lettura file email_message.html: {e}", "danger")
        return redirect(url_for("index"))

    # Sostituzioni dinamiche
    html_body = html_template.replace("{username}", username).replace(
        "{my_github}", os.getenv("MY_GITHUB_PROFILE", "https://github.com/GiovanniIacuzzo")
    )

    msg = Message(
        subject=f"Ciao {username}, voglio connettermi con te!",
        sender=os.getenv("EMAIL_USER"),
        recipients=[recipient_email],
        html=html_body
    )
    try:
        mail.send(msg)
        flash(f"Email inviata a {username} ✅", "success")
    except Exception as e:
        flash(f"Errore invio email: {e}", "danger")

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
