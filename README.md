<h1 align="center" style="font-size: 3rem; font-weight: 600; letter-spacing: 1px;">
GitScore Dashboard
</h1>

<p align="center">
  This is the **Italian version by default**. Switch to:  
  <a href="README_En.md">🇬🇧 English</a>
</p>

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-black)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20%7C%20Local-green)](https://www.mongodb.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML%20Pipeline-orange)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

Trasforma i dati di GitHub in informazioni utili, automatizza le tue azioni quotidiane e gestisci tutto con una dashboard elegante e intuitiva.

---

## 🛠️ Tech Stack

- 🐍 **Python 3.9+**
- ⚡ **Flask** (framework web)
- 🍃 **MongoDB** (storage)
- 🤖 **scikit-learn + imbalanced-learn** (machine learning)
- 📦 **pandas + joblib** (gestione dati e modelli)
- 🎨 **Bootstrap + Plotly** (UI e grafici interattivi)
- 📝 **loguru** (logging avanzato)

---

## 🌟 Cosa puoi fare

- Analizzare utenti GitHub con un punteggio basato su bio, location, repo e README  
- Salvare i dati su MongoDB in modo strutturato  
- Visualizzare e gestire tutto da una dashboard web moderna e responsive  
- Connetterti facilmente: seguire utenti e inviare email personalizzate  

---

## ✨ Funzionalità principali

| 📊 **Analisi utenti**        | 🧮 **Scoring automatico**     |
|------------------------------|-------------------------------|
| Scansione di bio, location, repo e README | Classificazione utenti per rilevanza |

| 📧 **Email integrate**       | 💾 **Database MongoDB**       |
|------------------------------|-------------------------------|
| Invio diretto di email personalizzate | Salvataggio persistente dei dati |

| 🌐 **Dashboard web**         | 🔄 **Reset rapido**           |
|------------------------------|-------------------------------|
| Filtri, grafici e pulsanti azione | Riparti da zero con un click |

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
├── 📁 web-app/   # Contiene tutta la logica e i componenti della web application Flask
│   │
│   ├── 📁 blueprints/               # Moduli di Flask per organizzare le diverse sezioni dell'app
│   │   ├── 🐍 active_learning_bp.py # Gestisce le rotte e la logica per la sezione di Active Learning del modello ML
│   │   ├── 🐍 email_bp.py           # Gestisce l'invio di email personalizzate agli utenti
│   │   ├── 🐍 main_bp.py            # Definisce le rotte principali della dashboard (home, statistiche)
│   │   ├── 🐍 scraper_bp.py         # Contiene le rotte per avviare e gestire lo scraping dei dati
│   │   ├── 🐍 user_bp.py            # Gestisce la visualizzazione e le azioni sugli utenti (es. follow)
│   │   └── 🐍 utils_bp.py           # Utility e funzioni di supporto usate dalle blueprint
│   │
│   ├── 📁 models/                   # Contiene i modelli di dati (es. definizioni delle classi per il database)
│   │   └── 🐍 user_model.py         # Esempio: modello di dati per la collezione 'users' di MongoDB
│   │
│   ├── 📁 scraping1/                # Modulo Python per la logica di scraping e analisi
│   │   ├── 🐍 __init__.py           # Inizializzazione del modulo Python
│   │   ├── 🐍 config.py             # Configurazioni specifiche per il modulo di scraping
│   │   ├── 🐍 github_api.py         # Funzioni per interagire con l'API di GitHub
│   │   ├── 🐍 main.py               # Punto di ingresso principale per l'esecuzione dello scraping
│   │   ├── 🐍 scoring.py            # Logica per il calcolo del punteggio di rilevanza degli utenti
│   │   ├── 🐍 storage.py            # Funzioni per salvare e recuperare dati da MongoDB
│   │   └── 🐍 utils.py              # Utility varie per lo scraping (es. parsing README)
│   │
│   ├── 📁 static/                   # Contiene i file statici serviti dalla web app (CSS, JS, immagini)
│   │   ├── 📁 css/                  # Fogli di stile CSS
│   │   │   └── 🎨 style.css         # Stile personalizzato per la dashboard
│   │   │
│   │   └── 📁 img/                  # Immagini e icone
│   │       └── 🖼️ favicon.ico       # Icona del sito web
│   │
│   ├── 📁 templates/                # File HTML dei template Jinja2 per le pagine web
│   │   ├── 🌐 active_learning.html  # Template per la pagina di Active Learning
│   │   ├── 🌐 config.html           # Template per la pagina di configurazione dell'applicazione
│   │   ├── 🌐 email_message.html    # Template per la visualizzazione/composizione delle email
│   │   ├── 🌐 index.html            # Template della pagina principale (dashboard)
│   │   ├── 🌐 manual_email.html     # Template per l'invio manuale di email
│   │   └── 🌐 my_profile.html       # Template per la visualizzazione del profilo utente
│   │
│   ├── 📄 Dataset_init.csv          # Dataset iniziale per l'addestramento o il seeding del modello ML
│   ├── 🐍 __init__.py               # Inizializzazione del pacchetto Python `web-app`
│   ├── 🐍 app.py                    # File principale dell'applicazione Flask, configura l'app e registra le blueprint
│   ├── 🐍 config.py                 # Configurazioni globali per l'applicazione Flask
│   ├── 🐍 db.py                     # Modulo per la connessione e gestione del database MongoDB
│   ├── 🐍 ml_model.py               # Contiene la logica per il caricamento e l'utilizzo del modello ML
│   ├── 🐍 train_model.py            # Script per l'addestramento o il ri-addestramento del modello ML
│   ├── 🐍 utils.py                  # Funzioni utility generiche per l'intera web app
│   └── 🐍 utils_github.py           # Funzioni utility specifiche per GitHub (es. operazioni su profili)
│
├── 🔒 .env                          # File di configurazione delle variabili d'ambiente (non versionato)
├── 🚫 .gitignore                    # Specifica i file e le directory da ignorare per Git
├── 📖 README.md                     # Questo file! Descrizione e istruzioni del progetto
└── 📄 requirements.txt              # Elenco delle dipendenze Python del progetto
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
Crea un file `.env` nella root del progetto con le seguenti variabili (aggiungi le tue credenziali e configurazioni):

```bash
# ================================
# GitHub / scraping
# ================================
GITHUB_TOKEN=il_tuo_token         # Il tuo Personal Access Token di GitHub (richiesto per API)
GITHUB_API=https://api.github.com # Endpoint API di GitHub
MY_CITY=inserisci_una_città       # La città da utilizzare come punto di partenza per la ricerca
NEARBY_CITIES=Roma,Milano,Torino  # Lista di città vicine, separate da virgola (es. "Roma,Milano")
KEYWORDS_BIO=python,data science  # Parole chiave per filtrare le bio degli utenti (separate da virgola)
KEYWORDS_README=flask,mongodb     # Parole chiave per filtrare i README degli utenti (separate da virgola)
ITALIAN_LOCATIONS=Italy,Italia    # Nomi di località italiane da considerare (separate da virgola)
N_USERS=10                        # Numero massimo di utenti da estrarre per ogni ciclo di scraping
REQUEST_DELAY=1                   # Ritardo in secondi tra le richieste all'API GitHub per evitare rate limiting
seed=il_tuo_username_github       # L'username GitHub da cui iniziare la ricerca (consigliato il proprio)

# ================================
# Flask
# ================================
FLASK_SECRET_KEY=la_tua_chiave_segreta   # Chiave segreta per la sicurezza delle sessioni Flask

# ================================
# Email
# ================================
EMAIL_HOST=smtp.gmail.com           # Host SMTP del servizio email (es. smtp.gmail.com)
EMAIL_PORT=587                      # Porta SMTP
EMAIL_USER=la_tua_mail@example.com  # La tua email per l'invio
EMAIL_PASSWORD=la_tua_password_app  # La password per app generata dal tuo provider (es. Google, Outlook)
MAIL_USE_TLS=True                   # Abilita StartTLS
MAIL_USE_SSL=False                  # Disabilita SSL diretto se usi TLS

# Modalità debug email
DEBUG_EMAIL_MODE=true                      # Se TRUE, le email verranno inviate solo all'indirizzo DEBUG_EMAIL
DEBUG_EMAIL=destinatario_test@example.com  # Indirizzo email per i test in modalità debug (puoi lasciare così)

# ================================
# Configurazione profilo GitHub
# ================================
MY_GITHUB_PROFILE=https://github.com/tuo-username  # Il link al tuo profilo GitHub
KEY_USERS=user1,user2                              # Lista di username GitHub di utenti "chiave" (separati da virgola)
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

## 🤝 Contribuire
Le pull request sono benvenute!  
Per modifiche importanti, apri prima una issue per discutere cosa vorresti cambiare.

---

## 📜 Licenza
Questo progetto è distribuito sotto licenza MIT. Vedi [LICENSE](LICENSE) per i dettagli.