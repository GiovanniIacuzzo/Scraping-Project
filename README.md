# 🤖 GitHub Smart Follower Dashboard

Un progetto che unisce **analisi intelligente**, **automazione** e **design curato** 🚀

---

## 🌟 Cosa puoi fare

- Analizzare utenti GitHub con un punteggio basato su bio, location, repo e README  
- Salvare i dati su MongoDB in modo strutturato  
- Visualizzare e gestire tutto da una dashboard web moderna e responsive  
- Connetterti facilmente: seguire utenti e inviare email personalizzate  

---

## ✨ Funzionalità principali

| Funzionalità       | Descrizione                               | Emoji |
|-------------------|------------------------------------------|-------|
| Analisi utenti     | Scansione bio, location, repo, README    | 📊    |
| Scoring automatico | Classifica utenti per rilevanza          | 🧮    |
| Email integrate    | Invio diretto di email personalizzate    | 📧    |
| Database MongoDB   | Salvataggio persistente dei dati         | 💾    |
| Dashboard web      | Filtri, grafici, pulsanti azione         | 🌐    |
| Reset rapido       | Riparti da zero con un click             | 🔄    |

---

## 📦 Raccolta dati

Il sistema raccoglie dati da GitHub utilizzando:

- **GitHub API** per username, bio, location, repo, followers/following  
- **Parsing README e bio** degli utenti per keyword rilevanti  
- **Salvataggio su MongoDB** per garantire persistenza e facilità di interrogazione  

Ogni utente salvato contiene:

- `username`  
- `bio`  
- `location`  
- `followers / following`  
- `email` (quando disponibile)  
- `score` calcolato dal modello ML  

> ⚡ **Nota:** La raccolta dei dati è batch-based per ridurre il carico e velocizzare la dashboard.

---

## 🧠 Modello di Machine Learning

Per determinare la **rilevanza degli utenti**, viene utilizzato un modello ML classificatore:

- **Input del modello:** bio, README, location, numero di followers/following  
- **Output:** probabilità che un utente sia “interessante” per follow o contatto  
- **Tecnologia:** `scikit-learn` + pipeline customizzata  
- **Modello salvato:** `github_user_classifier.pkl` con configurazione in `github_user_classifier.csv`  

Il modello viene aggiornato periodicamente tramite l’interfaccia **Active Learning**, dove l’utente annota profili incerti per migliorare il classificatore.

---

## 🌐 Dashboard Web

- **Flask + Bootstrap** per interfaccia moderna  
- **Visualizzazione interattiva dei dati:** filtri per città, keyword, score  
- **Azioni rapide:**  
  - ➕ Segui su GitHub  
  - 📩 Invia email di presentazione  
- **Grafici con Plotly:** distribuzione followers, heatmap città, trend crescita database

---

## 📂 Struttura del progetto
```bash
├── 📁 web-app/
│   ├── 📁 models/
│   │   ├── 📄 github_user_classifier.csv
│   │   └── 📄 github_user_classifier.pkl
│   │
│   ├── 📁 scraping1/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 config.py
│   │   ├── 🐍 github_api.py
│   │   ├── 🐍 main.py
│   │   ├── 🐍 scoring.py
│   │   ├── 🐍 storage.py
│   │   └── 🐍 utils.py
│   │
│   ├── 📁 static/
│   │   └── 📁 img/
│   │       └── 🖼️ favicon.ico
│   │
│   ├── 📁 templates/
│   │   ├── 🌐 active_learning.html
│   │   ├── 🌐 config.html
│   │   ├── 🌐 email_message.html
│   │   ├── 🌐 index.html
│   │   ├── 🌐 manual_email.html
│   │   └── 🌐 my_profile.html
│   │
│   ├── 📄 Dataset_init.csv
│   │
│   ├── 🐍 __init__.py
│   ├── 🐍 app.py
│   ├── 🐍 db.py
│   ├── 🐍 ml_model.py
│   ├── 🐍 train_model.py
│   ├── 🐍 utils.py
│   └── 🐍 utils_github.py
│
├── 🔒 .env
│
├── 🚫 .gitignore
│
├── 📖 README.md
│
└── 📄 requirements.txt
```

---

## ⚙️ Requisiti

- **Python 3.9+**
- **MongoDB** installato in locale o in cloud (es. MongoDB Atlas)
- Un **token GitHub** con permessi `read:user` e `user:follow`
- Un **account email SMTP** (es. Gmail) per inviare email

---

## 📦 Configurazione

1. **Clona il progetto**
```bash
git clone https://github.com/tuo-username/scraping-project.git
cd scraping-project
```
Scaricare i requisiti da:

```bash
pip install -r requirements.txt
```

2. **Configura il file .env**
Crea un file .env nella root del progetto con:

```bash
# ================================
# GitHub / scraping
# ================================
GITHUB_TOKEN=il_tuo_token
GITHUB_API=https://api.github.com
MY_CITY=inserisci_una_città
NEARBY_CITIES=
KEYWORDS_BIO=le_tue_keywords_bio
KEYWORDS_README=le_tue_keywords_readme
ITALIAN_LOCATIONS=la_tua_location
N_USERS=numero_utenti
REQUEST_DELAY=1
seed=account_github_da_cui_partire # Consiglio il proprio

# ================================
# Flask
# ================================
FLASK_SECRET_KEY=la_mia_chiave_segreta

# ================================
# Email
# ================================
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=la_tua_mail
EMAIL_PASSWORD=la_tua_password_temp
MAIL_USE_TLS=True
MAIL_USE_SSL=False

# Modalità debug email
DEBUG_EMAIL_MODE=true
DEBUG_EMAIL=example@example.com

# ================================
# Configurazione profilo GitHub
# ================================
MY_GITHUB_PROFILE=il_mio_profilo_github_link
KEY_USERS=le_mie_key_users
```

3. **Configura il database Mongo**

Ricorda di scaricare MongoDB e crea una collezione:

```bash
mongosh
use scraping-project
```

Se desideri visualizzare le persone nel databse:
```bash
db.users.find().pretty()
```

4. **Lancia il progetto**

```bash
cd web-app
python app.py
```
vai al link: http://127.0.0.1:5050

---

