from flask import Flask
from blueprints.main_bp import main_bp
from blueprints.email_bp import email_bp
from blueprints.scraper_bp import scraper_bp
from blueprints.active_learning_bp import active_learning_bp
from blueprints.utils_bp import utils_bp
from blueprints.user_bp import user_bp
from config import mail, SECRET_KEY, MAIL_SETTINGS, logger

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Config mail
app.config.update(MAIL_SETTINGS)
mail.init_app(app)

# Registrazione blueprint
app.register_blueprint(main_bp)
app.register_blueprint(email_bp)
app.register_blueprint(scraper_bp)
app.register_blueprint(active_learning_bp)
app.register_blueprint(utils_bp)
app.register_blueprint(user_bp)

# Test connessione SMTP all'avvio
def test_smtp_connection():
    try:
        from smtplib import SMTP
        logger.info(f"[SMTP] Provo a connettermi a {MAIL_SETTINGS['MAIL_SERVER']}:{MAIL_SETTINGS['MAIL_PORT']}")
        smtp = SMTP(MAIL_SETTINGS["MAIL_SERVER"], MAIL_SETTINGS["MAIL_PORT"], timeout=10)
        if MAIL_SETTINGS["MAIL_USE_TLS"]:
            smtp.starttls()
            logger.info("[SMTP] TLS avviato")
        smtp.login(MAIL_SETTINGS["MAIL_USERNAME"], MAIL_SETTINGS["MAIL_PASSWORD"])
        logger.info("[SMTP] Login riuscito")
        smtp.quit()
    except Exception as e:
        logger.error(f"[SMTP] Connessione fallita: {e}")

if __name__ == "__main__":
    test_smtp_connection()
    app.run(host="0.0.0.0", port=5050, debug=True, use_reloader=False)
