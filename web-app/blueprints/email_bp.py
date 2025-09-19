from flask import render_template, redirect, Blueprint, url_for, flash, request, current_app
from flask_mail import Message
from loguru import logger
import os, json

from db import collection
from utils_github import (
    get_my_followers, get_my_following
)
from config import DEBUG_EMAIL_MODE, DEBUG_EMAIL, mail

# ==============================================================
# Blueprint
# ==============================================================
email_bp = Blueprint("email", __name__)

# ==============================================================
# Invio email singolo utente
# ==============================================================
@email_bp.route("/send_email/<username>")
def send_email(username):
    if not current_app.config.get("MAIL_SERVER"):
        flash("Configurazione email mancante ❌", "warning")
        return redirect(url_for("main.index"))

    user = collection.find_one({"username": username})
    if not user:
        flash(f"Utente {username} non trovato ❌", "danger")
        return redirect(url_for("main.index"))

    recipient_email = user.get("email_to_notify")
    if str(DEBUG_EMAIL_MODE).lower() == "true":
        recipient_email = DEBUG_EMAIL
        logger.info(f"[DEBUG] Invio email di test a {DEBUG_EMAIL}")

    if not recipient_email:
        flash(f"Nessuna email disponibile per {username} ❌", "warning")
        return redirect(url_for("main.index"))

    try:
        from utils import read_html_template
        html_template, error = read_html_template("templates/email_message.html")
        if not html_template:
            flash(f"Errore lettura template email: {error}", "danger")
            return redirect(url_for("main.index"))

        html_body = html_template.replace("{username}", username).replace(
            "{my_github}", os.getenv("MY_GITHUB_PROFILE", "https://github.com/GiovanniIacuzzo")
        )

        subject = (
            f"[DEBUG] Test Email per {username}"
            if str(DEBUG_EMAIL_MODE).lower() == "true"
            else f"Ciao {username}, voglio connettermi con te!"
        )

        msg = Message(
            subject=subject,
            sender=os.getenv("EMAIL_USER"),
            recipients=[recipient_email],
            html=html_body,
        )

        mail.send(msg)
        flash(f"Email inviata a {recipient_email} ✅", "success")
    except Exception as e:
        logger.error(f"[ERROR] Invio email fallito: {e}", exc_info=True)
        flash(f"Errore invio email: {e}", "danger")

    return redirect(url_for("main.index"))

# ==============================================================
# Invio email manuale (form)
# ==============================================================
@email_bp.route("/manual_email", methods=["GET", "POST"])
def manual_email():
    if request.method == "POST":
        recipient_email = request.form.get("email")
        username = request.form.get("username")  # nuovo campo
        custom_message = request.form.get("message")

        if not recipient_email:
            flash("Inserisci un'email valida ❌", "danger")
            return redirect(url_for("email.manual_email"))

        # Se lo username è vuoto, fallback a "Ciao ciao"
        username_to_use = username.strip() if username and username.strip() else "Ciao ciao"

        try:
            from utils import read_html_template
            html_template, error = read_html_template("templates/email_message.html")
            if not html_template:
                flash(f"Errore lettura template email: {error}", "danger")
                return redirect(url_for("email.manual_email"))

            # Corpo dell'email
            if custom_message:
                html_body = f"""
                <!DOCTYPE html>
                <html><body><p>{custom_message}</p></body></html>
                """
            else:
                html_body = html_template.replace("{username}", username_to_use).replace(
                    "{my_github}", os.getenv("MY_GITHUB_PROFILE", "https://github.com/GiovanniIacuzzo")
                )

            msg = Message(
                subject=f"Ciao {username_to_use}, voglio connettermi con te!",
                sender=os.getenv("EMAIL_USER"),
                recipients=[recipient_email],
                html=html_body,
            )

            if str(DEBUG_EMAIL_MODE).lower() == "true":
                logger.info(f"[DEBUG] Invio email di test a {DEBUG_EMAIL}")
                msg.recipients = [DEBUG_EMAIL]

            mail.send(msg)
            flash(f"Email inviata a {recipient_email} ✅", "success")
            return redirect(url_for("email.manual_email"))

        except Exception as e:
            logger.error(f"[ERROR] Invio email manuale fallito: {e}", exc_info=True)
            flash(f"Errore invio email: {e}", "danger")
            return redirect(url_for("email.manual_email"))

    return render_template("manual_email.html")

# ==============================================================
# Profilo e DB
# ==============================================================
@email_bp.route("/my_profile")
def my_profile_view():
    followers = get_my_followers()
    following = get_my_following()
    all_users = sorted(set(followers + following), key=lambda x: x.lower())

    users_status = [
        {"username": u, "is_follower": u in followers, "is_following": u in following}
        for u in all_users
    ]

    followers_distribution = {
        "usernames": ["user1", "user2", "user3"],
        "followers": [10, 5, 15],
    }
    city_heatmap = {"cities": ["Roma", "Milano", "Torino"], "counts": [[5, 2, 3]]}
    growth_trend = {
        "dates": ["2025-09-01", "2025-09-05", "2025-09-10"],
        "counts": [50, 75, 120],
    }

    return render_template(
        "my_profile.html",
        users=users_status,
        followers_distribution=json.dumps(followers_distribution),
        city_heatmap=json.dumps(city_heatmap),
        growth_trend=json.dumps(growth_trend),
    )
