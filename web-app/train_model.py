import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

# --- 1. Carica dataset ---
dataset_path = "Dataset_init.csv"
model_path = "models/github_user_classifier_smote.pkl"
feature_importances_path = "models/feature_importances_smote.csv"

if not os.path.exists(dataset_path):
    raise FileNotFoundError(f"File {dataset_path} non trovato!")

print("Caricamento dataset...")
df = pd.read_csv(dataset_path)

# --- 2. Gestione valori mancanti ---
print("Gestione valori mancanti...")
numeric = ["followers", "following", "public_repos", "public_gists",
           "total_stars", "total_forks", "heuristic_score"]
categorical = ["company", "main_languages", "location"]
textual = "bio"

df[numeric] = df[numeric].fillna(0)
df[categorical] = df[categorical].fillna("")
df[textual] = df[textual].fillna("")

y = df["annotation"].astype(int)
X = df.drop(columns=["annotation", "username", "email", "created_at", "updated_at"], errors="ignore")

# --- 3. Preprocessing ---
preprocessor = ColumnTransformer(transformers=[
    ("num", StandardScaler(), numeric),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
    ("txt", TfidfVectorizer(max_features=300, stop_words="english"), textual)
], remainder="drop")

# --- 4. Split train/test ---
print("Split train/test...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# --- 5. Pipeline con SMOTE ---
pipeline = ImbPipeline(steps=[
    ("preprocessor", preprocessor),
    ("smote", SMOTE(random_state=42)),
    ("classifier", RandomForestClassifier(random_state=42, class_weight="balanced"))
])

# --- 6. Grid search parametri RandomForest ---
param_grid = {
    "classifier__n_estimators": [200, 300],
    "classifier__max_depth": [None, 10, 20],
    "classifier__min_samples_split": [2, 5],
    "classifier__min_samples_leaf": [1, 2],
}

print("Avvio GridSearchCV con SMOTE...")
grid = GridSearchCV(pipeline, param_grid, cv=5, scoring="f1", n_jobs=-1, verbose=2)
grid.fit(X_train, y_train)

best_model = grid.best_estimator_
print("Migliori parametri trovati:", grid.best_params_)

# --- 7. Valutazione su test set ---
y_pred = best_model.predict(X_test)
print("Valutazione modello ottimizzato con SMOTE:")
print(classification_report(y_test, y_pred))
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# --- 8. Salvataggio modello ---
os.makedirs("models", exist_ok=True)
joblib.dump(best_model, model_path)
print(f"Modello RandomForest + SMOTE salvato in {model_path}")

# --- 9. Salvataggio feature importances ---
try:
    clf = best_model.named_steps["classifier"]
    feature_names_num = numeric
    feature_names_cat = best_model.named_steps["preprocessor"].named_transformers_["cat"].get_feature_names_out(categorical)
    feature_names_txt = best_model.named_steps["preprocessor"].named_transformers_["txt"].get_feature_names_out()
    feature_names = list(feature_names_num) + list(feature_names_cat) + list(feature_names_txt)

    fi = pd.DataFrame({
        "feature": feature_names,
        "importance": clf.feature_importances_
    }).sort_values("importance", ascending=False)
    fi.to_csv(feature_importances_path, index=False)
    print(f"Feature importances salvate in {feature_importances_path}")
except Exception as e:
    print("Impossibile salvare feature importances:", e)
