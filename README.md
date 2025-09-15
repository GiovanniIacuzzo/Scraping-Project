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

2. **Configura il file .env**
Crea un file .env nella root del progetto con:

```bash
# GitHub API
GITHUB_TOKEN=il_tuo_token_personale
MY_CITY=Città_vicina_a_te
REQUEST_DELAY=1
N_USERS=Numero_di_utenti_che_vuoi_seguire
seed=Tuo_NickName_GitHub

# MongoDB
MONGO_URI=mongodb://localhost:27017/

# Email SMTP
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=tuoaccount@gmail.com
EMAIL_PASSWORD=tuapassword

FLASK_SECRET_KEY=la_mia_chiave_segreta
```

3. **Configura il database Mongo**

Scarica MongoDB e crea una collezione:

```bash
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

