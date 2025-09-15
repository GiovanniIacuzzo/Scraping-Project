import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from db import collection

# Percorso modello
MODEL_PATH = "models/github_user_classifier.pkl"

# Configurazione feature
NUM_FEATURES = ["followers","following","public_repos","public_gists","total_stars","total_forks","heuristic_score"]
CAT_FEATURES = ["location","company","main_languages"]
TEXT_FEATURE = "bio"

# --- 1. Caricamento dataset dal DB ---
def get_dataset():
    users = list(collection.find({"annotation": {"$in": [0, 1]}}))  # solo etichettati
    if not users:
        return None, None
    df = pd.DataFrame(users)

    # Gestione valori mancanti
    for col in NUM_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    for col in CAT_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("unknown")
    if TEXT_FEATURE in df.columns:
        df[TEXT_FEATURE] = df[TEXT_FEATURE].fillna("")

    X = df[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]]
    y = df["annotation"]
    return X, y

# --- 2. Costruzione pipeline ---
def build_pipeline():
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
            ("text", TfidfVectorizer(max_features=300, stop_words="english"), TEXT_FEATURE)
        ]
    )
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=1,
            random_state=42,
            class_weight="balanced"
        ))
    ])
    return pipeline

# --- 3. Training modello e salvataggio ---
def train_model():
    X, y = get_dataset()
    if X is None or len(X) == 0:
        print("⚠️ Nessun dato etichettato disponibile per il training")
        return None
    pipeline = build_pipeline()
    pipeline.fit(X, y)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    print("✅ Training completato e modello salvato")
    return pipeline

# --- 4. Caricamento modello ---
def load_model():
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ Modello non trovato in {MODEL_PATH}")
        return None
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"❌ Errore caricamento modello: {e}")
        return None

# --- 5. Predizione probabilità ---
def predict_proba(users):
    model = load_model()
    if not model:
        return []
    df = pd.DataFrame(users)

    # Gestione valori mancanti
    for col in NUM_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    for col in CAT_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("unknown")
    if TEXT_FEATURE in df.columns:
        df[TEXT_FEATURE] = df[TEXT_FEATURE].fillna("")

    try:
        probs = model.predict_proba(df[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]])[:, 1]
    except Exception as e:
        print(f"❌ Errore predizione: {e}")
        return []
    return probs

# --- 6. Seleziona utenti più incerti ---
def query_uncertain(users, n=5):
    probs = predict_proba(users)
    if len(probs) == 0:
        return []
    users_with_score = [(user, abs(p - 0.5), p) for user, p in zip(users, probs)]
    users_with_score.sort(key=lambda x: x[1])  # più incerti prima
    return users_with_score[:n]
