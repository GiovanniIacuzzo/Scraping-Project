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

@scraper_bp.route("/scrape_with_ml", methods=["POST"])
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