from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from datetime import datetime

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def save_user(user_doc):
    user_doc["last_checked"] = datetime.utcnow()
    collection.update_one({"username": user_doc["username"]}, {"$set": user_doc}, upsert=True)
