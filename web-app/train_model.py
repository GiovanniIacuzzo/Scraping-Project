import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# --- 1. Carica dataset ---
df = pd.read_csv("Dataset_init.csv")

# Target e feature
y = df["annotation"].astype(int)  # Assicurati sia 0/1
X = df.drop(columns=["annotation", "username", "email", "created_at", "updated_at"], errors="ignore")

# --- 2. Definizione colonne ---
numeric = ["followers", "following", "public_repos", "public_gists",
           "total_stars", "total_forks", "heuristic_score"]
categorical = ["company", "main_languages", "location"]
textual = "bio"   # per semplicità prendiamo solo la bio

# --- 3. Preprocessing ---
preprocessor = ColumnTransformer(transformers=[
    ("num", StandardScaler(), numeric),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
    ("txt", TfidfVectorizer(max_features=300, stop_words="english"), textual)
], remainder="drop")

# --- 4. Pipeline modello ---
model = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=300,       # più alberi = più robusto
        max_depth=None,         # profondità illimitata
        random_state=42,
        class_weight="balanced" # bilancia le classi
    ))
])

# --- 5. Train/test split ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# --- 6. Training ---
model.fit(X_train, y_train)

# --- 7. Valutazione ---
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# --- 8. Salvataggio modello ---
joblib.dump(model, "models/github_user_classifier.pkl")
print("✅ Modello RandomForest salvato in models/github_user_classifier.pkl")
