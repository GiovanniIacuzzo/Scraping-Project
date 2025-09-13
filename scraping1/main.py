from github_api import get_candidate_users, is_followed
from scoring import score_user
from storage import save_user
from config import N_USERS, REQUEST_DELAY
import time


def get_candidate_users_advanced(target_count):
    """
    Richiama utenti finché non si ottengono target_count utenti nuovi.
    """
    seen = set()
    valid_users = []

    while len(valid_users) < target_count:
        # Chiamata alla GitHub Search API
        candidate_users = get_candidate_users()
        for user in candidate_users:
            if user in seen:
                continue
            seen.add(user)
            if is_followed(user):
                print(f"{user} è già seguito, skip")
                continue
            valid_users.append(user)
            if len(valid_users) >= target_count:
                break
        time.sleep(REQUEST_DELAY)
    return valid_users

if __name__ == "__main__":
    candidate_users = get_candidate_users_advanced(N_USERS)
    scored_users = []

    for user in candidate_users:
        score = score_user(user)
        save_user({
            "username": user,
            "score": score
        })
        scored_users.append((user, score))
        print(f"Salvato {user} con punteggio {score}")

    scored_users.sort(key=lambda x: x[1], reverse=True)
    final_users = [user for user, score in scored_users]
    print("Utenti salvati e ordinati per rilevanza:", final_users)
