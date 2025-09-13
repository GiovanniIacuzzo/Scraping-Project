import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", 1))
N_USERS = int(os.getenv("N_USERS", 20))

KEYWORDS_BIO = [k.strip() for k in os.getenv("KEYWORDS_BIO", "").split(",") if k.strip()]
KEYWORDS_README = [k.strip() for k in os.getenv("KEYWORDS_README", "").split(",") if k.strip()]

ITALIAN_LOCATIONS = [l.strip() for l in os.getenv("ITALIAN_LOCATIONS", "").split(",") if l.strip()]
NEARBY_CITIES = [c.strip() for c in os.getenv("NEARBY_CITIES", "").split(",") if c.strip()]
MY_CITY = os.getenv("MY_CITY")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "scraping-project"
COLLECTION_NAME = "users"
