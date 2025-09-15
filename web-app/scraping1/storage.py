from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from datetime import datetime
from scraping1.scoring import build_user_document

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def save_user(user_doc):
    """Salva o aggiorna un utente in MongoDB"""
    collection.update_one({"username": user_doc["username"]}, {"$set": user_doc}, upsert=True)


def process_and_save_users(usernames):
    for username in usernames:
        user_doc = build_user_document(username)
        if user_doc:
            save_user(user_doc)
            print(f"[DB] Salvato {username}")
        else:
            print(f"[SKIP] Nessun dato per {username}")