import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from db import collection

MODEL_PATH = "models/github_user_classifier.pkl"

# Feature config
NUM_FEATURES = ["followers","following","public_repos","public_gists","total_stars","total_forks"]
CAT_FEATURES = ["location","company","main_languages"]
TEXT_FEATURE = "bio"

def get_dataset():
    users = list(collection.find({"annotation": {"$in": [0, 1]}}))  # solo etichettati
    if not users:
        return None, None
    df = pd.DataFrame(users)
    X = df[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]]
    y = df["annotation"]
    return X, y

def build_pipeline():
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
            ("text", TfidfVectorizer(max_features=100), TEXT_FEATURE)
        ]
    )
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("clf", RandomForestClassifier(random_state=42))
    ])
    return pipeline

def train_model():
    X, y = get_dataset()
    if X is None:
        return None
    pipeline = build_pipeline()
    pipeline.fit(X, y)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    return pipeline

def load_model():
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except:
        return None

def predict_proba(users):
    model = load_model()
    if not model:
        return []
    df = pd.DataFrame(users)
    return model.predict_proba(df[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]])[:, 1]

def query_uncertain(users, n=5):
    """Ritorna i n utenti più incerti (prob vicino a 0.5)"""
    probs = predict_proba(users)
    if len(probs) == 0:
        return []
    users_with_score = []
    for user, p in zip(users, probs):
        users_with_score.append((user, abs(p - 0.5), p))
    users_with_score.sort(key=lambda x: x[1])  # più incerti prima
    return users_with_score[:n]
