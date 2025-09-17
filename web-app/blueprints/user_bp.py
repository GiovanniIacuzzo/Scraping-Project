from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from db import collection
from loguru import logger
from config import MY_CITY, NEARBY_CITIES, KEYWORDS_BIO, KEYWORDS_README, ITALIAN_LOCATIONS, N_USERS
import threading
from utils_github import follow_user_api, is_followed, unfollow_user_api

user_bp = Blueprint("user", __name__)

# ==============================
# Buffer utenti nuovi (thread-safe)
# ==============================
new_users_buffer = []
buffer_lock = threading.Lock()

# ==============================
# Endpoint per recuperare nuovi utenti
# ==============================
@user_bp.route("/get_new_users")
def get_new_users():
    global new_users_buffer
    with buffer_lock:
        users_to_send = new_users_buffer.copy()
        new_users_buffer.clear()
    return jsonify(users_to_send)

# ==============================================================
# Follow / Unfollow
# ==============================================================
@user_bp.route("/follow/<username>")
def follow_user(username):
    if is_followed(username):
        flash(f"Hai già seguito {username} ✅", "info")
    elif follow_user_api(username):
        flash(f"Hai seguito {username} ✅", "success")
    else:
        flash(f"Errore nel seguire {username}", "danger")
    return redirect(url_for("main.index"))

@user_bp.route("/unfollow/<username>")
def unfollow_user(username):
    if unfollow_user_api(username):
        flash(f"Hai smesso di seguire {username} ✅", "success")
    else:
        flash(f"Errore nello smettere di seguire {username}", "danger")
    return redirect(url_for("email.my_profile_view"))

# ==============================
# Configurazione app
# ==============================
@user_bp.route("/config", methods=["GET", "POST"])
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
        try:
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
        except Exception as e:
            logger.error(f"[ERROR] Aggiornamento configurazione fallito: {e}", exc_info=True)
            flash(f"Errore aggiornamento configurazione: {e}", "danger")

        return redirect(url_for("index"))

    return render_template("config.html",
                           MY_CITY=MY_CITY,
                           NEARBY_CITIES=",".join(NEARBY_CITIES),
                           KEYWORDS_BIO=",".join(KEYWORDS_BIO),
                           KEYWORDS_README=",".join(KEYWORDS_README),
                           ITALIAN_LOCATIONS=",".join(ITALIAN_LOCATIONS),
                           N_USERS=N_USERS)

# ==============================
# Salvataggio annotazioni utenti
# ==============================
@user_bp.route("/save_annotation", methods=["POST"])
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

# ==============================
# Esportazione utenti in CSV
# ==============================
@user_bp.route("/export_csv")
def export_csv():
    users_cursor = collection.find()
    
    fieldnames = [
        "username", "name", "bio", "location", "followers", "following",
        "email", "annotation",
        "heuristic_score", "public_repos", "public_gists", "company",
        "main_languages", "total_stars", "total_forks", "created_at", "updated_at"
    ]

    def generate():
        yield ",".join(fieldnames) + "\n"
        for u in users_cursor:
            row = []
            email = u.get("email_to_notify") or u.get("email_extracted") or u.get("email_public") or ""
            for f in fieldnames:
                if f == "email":
                    val = email
                elif f == "annotation":
                    val = u.get("annotation", "")
                else:
                    val = u.get(f, "")
                if isinstance(val, list):
                    val = ";".join(map(str, val))
                val = str(val).replace("\n", " ").replace("\r", " ").replace(",", ";")
                row.append(val)
            yield ",".join(row) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=utenti.csv"}
    )
