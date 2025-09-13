from pymongo import MongoClient
from dotenv import load_dotenv
import os

# ==============================================================
# Script di manutenzione: rimozione completa degli utenti salvati
# ==============================================================

# Caricamento variabili da file .env
load_dotenv()

# Connessione a MongoDB
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client["scraping-project"]
collection = db["users"]

# Eliminazione di tutti i documenti nella collezione
result = collection.delete_many({})
print(f"Tutti gli utenti rimossi: {result.deleted_count}")
