from flask import redirect, url_for, flash, request, jsonify, Blueprint
import threading, time, joblib, os, sys, random
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from loguru import logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'scraping1')))

from db import collection
from utils import build_user_document, extract_features
from utils_github import extract_email_from_github_profile
from blueprints.utils_bp import get_user_info_cached, get_followers_or_following, get_github_usernames_global
from scraping1.github_api import get_candidate_users_advanced, get_user_info
from scraping1.scoring import score_user
from scraping1.storage import save_user
from ml_model import NUM_FEATURES, CAT_FEATURES, TEXT_FEATURE
from config import (
    MY_CITY, NEARBY_CITIES, KEYWORDS_BIO, KEYWORDS_README,
    ITALIAN_LOCATIONS, N_USERS, REQUEST_DELAY, KEY_USERS, new_users_buffer, buffer_lock, scraping_in_progress
)

scraper_bp = Blueprint("scraper", __name__)

@scraper_bp.route("/run_scraper_async")
def run_scraper_async():
    global scraping_in_progress
    if scraping_in_progress:
        flash("Lo scraping è già in corso ⏳", "info")
        return redirect(url_for("main.index"))

    # Avvia thread background
    threading.Thread(target=_scraper_thread, daemon=True).start()
    flash("Scraping avviato! Gli utenti appariranno gradualmente 🔄", "success")
    return redirect(url_for("main.index"))

def _scraper_thread():
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

@scraper_bp.route("/scrape_with_ml", methods=["POST"])
def scrape_with_ml():
    try:
        requested_limit = int(request.args.get("limit", 5))
        uncertainty_range = float(request.args.get("uncertainty_range", 0.2))  # default più ampio
        logger.info(f"[ML-SCRAPE] Avvio scraping ML (limit={requested_limit}, uncertainty_range={uncertainty_range})")

        # ============================
        # Caricamento modello ML
        # ============================
        try:
            model = joblib.load("models/github_user_classifier.pkl")
            logger.info("✅ Modello ML caricato.")
        except FileNotFoundError:
            logger.error("❌ Modello ML non trovato.")
            return jsonify({"success": False, "error": "Modello ML non trovato. Effettua un training prima."}), 500
        except Exception as e:
            logger.error(f"❌ Errore caricamento modello ML: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

        # ============================
        # Raccolta candidati
        # ============================
        candidate_usernames = set()
        filtered_counts = {"public_repos": 0, "type": 0, "no_info": 0}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_followers_or_following, ku, typ)
                       for ku in KEY_USERS for typ in ["followers", "following"]]
            for future in as_completed(futures):
                try:
                    candidate_usernames.update(future.result())
                except Exception as exc:
                    logger.warning(f"Errore recupero candidati: {exc}")

        if len(candidate_usernames) < 100:
            logger.info("[ML-SCRAPE] Pochi candidati, aggiungo da scraping globale.")
            candidate_usernames.update(get_github_usernames_global(limit=500, since=0))

        existing = {u["username"] for u in collection.find(
            {"$or": [{"annotation": {"$exists": True}}, {"pred_prob": {"$exists": True}}]},
            {"username": 1}
        )}
        candidate_usernames = [u for u in candidate_usernames if u not in existing]

        if not candidate_usernames:
            logger.info("[ML-SCRAPE] Nessun nuovo candidato disponibile.")
            return jsonify({"success": False, "error": "Nessun nuovo candidato disponibile."}), 200

        random.shuffle(candidate_usernames)
        logger.info(f"[ML-SCRAPE] Totale candidati unici: {len(candidate_usernames)}")

        # ============================
        # Valutazione batch con ML
        # ============================
        batch_size = 50
        found_uncertain_users = []
        batches_processed = 0
        max_batches = 100
        total_users_evaluated = 0

        while len(found_uncertain_users) < requested_limit and candidate_usernames and batches_processed < max_batches:
            batches_processed += 1
            users_to_fetch = [candidate_usernames.pop(0) for _ in range(min(batch_size, len(candidate_usernames)))]
            if not users_to_fetch:
                break

            batch_user_docs = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_user = {executor.submit(get_user_info_cached, u): u for u in users_to_fetch}
                for future in as_completed(future_to_user):
                    username = future_to_user[future]
                    try:
                        info = future.result()
                        if not info:
                            filtered_counts["no_info"] += 1
                            logger.debug(f"[ML-SCRAPE] Utente {username} ignorato: nessuna info.")
                            continue
                        if info.get("public_repos", 0) < 5:
                            filtered_counts["public_repos"] += 1
                            logger.debug(f"[ML-SCRAPE] Utente {username} ignorato: public_repos < 5")
                            continue
                        if info.get("type") != "User":
                            filtered_counts["type"] += 1
                            logger.debug(f"[ML-SCRAPE] Utente {username} ignorato: type != User")
                            continue

                        doc = {
                            "username": username,
                            "followers": info.get("followers", 0),
                            "following": info.get("following", 0),
                            "public_repos": info.get("public_repos", 0),
                            "public_gists": info.get("public_gists", 0),
                            "bio": info.get("bio", ""),
                            "location": info.get("location", ""),
                            "company": info.get("company", ""),
                            "email_to_notify": extract_email_from_github_profile(username),
                            "github_url": info.get("html_url", f"https://github.com/{username}")
                        }
                        batch_user_docs.append(doc)
                    except Exception as exc:
                        logger.warning(f"Errore fetch info {username}: {exc}")

            if not batch_user_docs:
                continue

            df_batch = pd.DataFrame([extract_features(doc) for doc in batch_user_docs])
            for c in NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]:
                if c not in df_batch.columns:
                    df_batch[c] = "" if c in CAT_FEATURES + [TEXT_FEATURE] else 0
            df_batch = df_batch[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]]
            logger.debug(f"[ML-SCRAPE] Shape DataFrame batch: {df_batch.shape}, colonne: {df_batch.columns.tolist()}")

            # --- gestione robusta predict_proba ---
            probs_array = model.predict_proba(df_batch)
            logger.debug(f"[ML-SCRAPE] predict_proba shape: {probs_array.shape}")
            if probs_array.shape[1] == 1:
                probs = probs_array[:, 0] if model.classes_[0] == 1 else 1 - probs_array[:, 0]
            else:
                probs = probs_array[:, 1]

            # --- filtra solo utenti incerti ---
            for i, doc in enumerate(batch_user_docs):
                prob = float(probs[i])
                doc["pred_prob"] = round(prob, 3)
                doc["uncertainty_score"] = abs(prob - 0.5)
                total_users_evaluated += 1

                logger.debug(f"[ML-SCRAPE] Utente {doc['username']}, prob={prob:.3f}, uncertainty_score={doc['uncertainty_score']:.3f}")

                if 0.5 - uncertainty_range <= prob <= 0.5 + uncertainty_range:
                    collection.update_one({"username": doc["username"]}, {"$set": doc}, upsert=True)
                    found_uncertain_users.append(doc)
                    if len(found_uncertain_users) >= requested_limit:
                        break

            logger.info(f"[ML-SCRAPE] Batch {batches_processed} → trovati {len(found_uncertain_users)} incerti (target={requested_limit})")

        final_users_for_ui = found_uncertain_users[:requested_limit]
        logger.info(f"[ML-SCRAPE] Completato. Restituiti {len(final_users_for_ui)} utenti incerti. Totale utenti valutati: {total_users_evaluated}")
        logger.info(f"[ML-SCRAPE] Filtrati: {filtered_counts}")

        return jsonify({"success": True, "users": final_users_for_ui, "inserted": len(final_users_for_ui)}), 200

    except Exception as e:
        logger.exception("[ML-SCRAPE] Errore generale:")
        return jsonify({"success": False, "error": str(e)}), 500
