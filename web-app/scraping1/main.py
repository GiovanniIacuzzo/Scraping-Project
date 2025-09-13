from github_api import (
    get_candidate_users_advanced,
    get_user_info,
    extract_email_from_github_profile
)
from scoring import score_user
from storage import save_user
from config import N_USERS, REQUEST_DELAY
import time

if __name__ == "__main__":
    # Ottieni utenti candidati
    candidate_users = get_candidate_users_advanced(N_USERS)
    scored_users = []

    for username in candidate_users:
        # Recupera info utente
        info = get_user_info(username)
        if not info:
            print(f"[WARNING] Impossibile recuperare info per {username}")
            continue

        # Calcola lo score passando user_info
        score = score_user(info)

        # Estrai email pubblica dal profilo GitHub
        email = extract_email_from_github_profile(username)

        # Prepara documento da salvare
        user_doc = {
            "username": username,
            "bio": info.get("bio") or "",
            "location": info.get("location") or "",
            "followers": info.get("followers") or 0,
            "following": info.get("following") or 0,
            "email_to_notify": email,
            "score": score
        }

        # Salva o aggiorna in MongoDB
        save_user(user_doc)

        scored_users.append((username, score))
        print(f"Salvato {username} con punteggio {score}")

        # Ritardo per evitare rate limit
        time.sleep(REQUEST_DELAY)

    # Ordina utenti per score decrescente
    scored_users.sort(key=lambda x: x[1], reverse=True)
    final_users = [user for user, score in scored_users]

    print("Utenti salvati e ordinati per rilevanza:", final_users)
