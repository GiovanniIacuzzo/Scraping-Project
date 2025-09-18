import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from db import collection

# ==============================================================
# Percorso modello
# ==============================================================
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "models", "github_user_classifier.pkl")

# ==============================================================
# Configurazione feature
# ==============================================================
NUM_FEATURES = ["followers","following","public_repos","public_gists","total_stars","total_forks","heuristic_score"]
CAT_FEATURES = ["location","company","main_languages"]
TEXT_FEATURE = "bio"

# ==============================================================
# 1. Caricamento dataset dal DB
# ==============================================================
def get_dataset():
    users = list(collection.find({"annotation": {"$in": [0, 1]}}))  # solo etichettati
    if not users:
        print("⚠️ Nessun dato annotato trovato nel DB")
        return None, None
    df = pd.DataFrame(users)

    # Determina quali colonne sono effettivamente presenti
    num_features_present = [c for c in NUM_FEATURES if c in df.columns]
    cat_features_present = [c for c in CAT_FEATURES if c in df.columns]
    text_feature_present = TEXT_FEATURE if TEXT_FEATURE in df.columns else None

    # Valori mancanti e conversione liste in stringhe
    for col in num_features_present:
        df[col] = df[col].fillna(0)
    for col in cat_features_present:
        df[col] = df[col].apply(lambda x: ";".join(x) if isinstance(x, list) else (x or "unknown"))
    if text_feature_present:
        df[text_feature_present] = df[text_feature_present].fillna("")

    features = num_features_present + cat_features_present
    if text_feature_present:
        features.append(text_feature_present)

    X = df[features]
    y = df["annotation"]
    return X, y

# ==============================================================
# 2. Costruzione pipeline
# ==============================================================
def build_pipeline():
    # Determina quali colonne sono presenti per costruire il preprocessor
    num_features_present = [c for c in NUM_FEATURES if c in collection.find_one() or False]
    cat_features_present = [c for c in CAT_FEATURES if c in collection.find_one() or False]
    text_feature_present = TEXT_FEATURE if TEXT_FEATURE in collection.find_one() else None

    transformers = []
    if num_features_present:
        transformers.append(("num", StandardScaler(), num_features_present))
    if cat_features_present:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat_features_present))
    if text_feature_present:
        transformers.append(("text", TfidfVectorizer(max_features=300, stop_words="english"), text_feature_present))

    preprocessor = ColumnTransformer(transformers=transformers)
    
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


# ==============================================================
# 3. Training modello e salvataggio
# ==============================================================
def train_model():
    X, y = get_dataset()
    if X is None or len(X) == 0:
        print("⚠️ Nessun dato annotato disponibile per il training")
        return None
    pipeline = build_pipeline()
    try:
        pipeline.fit(X, y)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
        print(f"✅ Training completato e modello salvato in {MODEL_PATH}")
        return pipeline
    except Exception as e:
        print(f"❌ Errore durante il training o salvataggio del modello: {type(e)} {e}")
        return None

# ==============================================================
# 4. Caricamento modello con logging dettagliato
# ==============================================================
def load_model():
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ Modello non trovato: {MODEL_PATH}")
        return None
    try:
        model = joblib.load(MODEL_PATH)
        print(f"✅ Modello caricato correttamente da {MODEL_PATH}")
        return model
    except Exception as e:
        print(f"❌ Errore caricamento modello: {type(e)} {e}")
        return None

# ==============================================================
# 5. Predizione probabilità
# ==============================================================
def predict_proba(users):
    model = load_model()
    if not model:
        print("⚠️ Nessun modello disponibile per predizione")
        return []

    df = pd.DataFrame(users)

    # Valori mancanti e conversione liste in stringhe
    for col in NUM_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    for col in CAT_FEATURES:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ";".join(x) if isinstance(x, list) else (x or "unknown"))
    if TEXT_FEATURE in df.columns:
        df[TEXT_FEATURE] = df[TEXT_FEATURE].fillna("")

    try:
        probs = model.predict_proba(df[NUM_FEATURES + CAT_FEATURES + [TEXT_FEATURE]])[:, 1]
        return probs
    except Exception as e:
        print(f"❌ Errore predizione: {type(e)} {e}")
        return []

# ==============================================================
# 6. Seleziona utenti più incerti
# ==============================================================
def query_uncertain(users, n=5):
    probs = predict_proba(users)
    if len(probs) == 0:
        return []
    users_with_score = [(user, abs(p - 0.5), p) for user, p in zip(users, probs)]
    users_with_score.sort(key=lambda x: x[1])  # più incerti prima
    return users_with_score[:n]
