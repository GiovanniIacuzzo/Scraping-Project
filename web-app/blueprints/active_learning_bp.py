from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from db import collection
from loguru import logger
from ml_model import train_model

active_learning_bp = Blueprint("active_learning", __name__)

# ==============================
# Endpoint per ottenere candidati all'active learning
# ==============================
@active_learning_bp.route("/active_learning_candidates", methods=["GET"])
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

# ==============================
# Endpoint per riaddestrare il modello ML
# ==============================
@active_learning_bp.route("/retrain_model")
def retrain_model():
    try:
        logger.info("[INFO] Avvio training modello...")
        model = train_model()
        if model:
            flash("Modello riaddestrato con successo ✅", "success")
            logger.info("[INFO] Training completato correttamente")
        else:
            flash("Nessun dato annotato, impossibile allenare ❌", "warning")
            logger.warning("[WARN] Nessun dato annotato disponibile per il training")
    except Exception as e:
        flash(f"Errore durante il training del modello ❌: {e}", "danger")
        logger.exception(f"[ERROR] Errore durante il training: {type(e)} {e}")
    return redirect(url_for("main.index"))

# ==============================
# Visualizzazione pagina Active Learning
# ==============================
@active_learning_bp.route("/active_learning")
def active_learning():
    return render_template("active_learning.html")

# ==============================
# Ricerca utenti per input (autocomplete o ricerca veloce)
# ==============================
@active_learning_bp.route("/search_users")
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

# ==============================
# Recupero batch di utenti per UI
# ==============================
@active_learning_bp.route("/get_users_batch")
def get_users_batch():
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 20))
    users = list(collection.find().skip(offset).limit(limit))
    for u in users:
        u["_id"] = str(u["_id"])  # serializzabile
    return jsonify(users)
