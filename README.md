# 🤖 GitHub Smart Follower Dashboard

Un progetto che unisce **analisi intelligente**, **automazione** e **design curato**.  
Ti permette di:

- 📊 **Analizzare utenti GitHub** e valutarli con un punteggio basato su *bio, location, repo e README*  
- 💾 **Salvare i dati su MongoDB** in modo strutturato  
- 🌐 **Visualizzare e gestire tutto da una dashboard web** moderna e responsive  
- 🤝 **Connetterti facilmente**: puoi seguire utenti in automatico e inviare **email di presentazione personalizzate**  

---

## ✨ Funzionalità principali

✅ **Ricerca avanzata utenti GitHub**  
   - Filtra per **location** (con priorità all’Italia e agli utenti vicini a *Enna*)  
   - Analisi di **keywords** nella bio e nei README  
   - Controllo realistico su **followers / following**  

🧮 **Algoritmo di scoring personalizzato**  
   - Classifica automaticamente gli utenti in base alla rilevanza  

📧 **Gestione email integrata**  
   - Estrazione automatica di email pubbliche da bio/README  
   - Invio diretto di **email HTML di presentazione** dalla dashboard  

💾 **Database MongoDB**  
   - Salvataggio strutturato e persistente degli utenti analizzati  

🌐 **Dashboard interattiva (Flask + Bootstrap)**  
   - 🔎 Filtri per città, followers e keywords  
   - 📊 Ordinamento per score, followers o following  
   - ⚡ Azioni rapide con pulsanti dedicati:  
     - ➕ Segui su GitHub  
     - 📩 Invia email di presentazione  

🔄 **Reset veloce del database**  
   - Con lo script `refresh.py` puoi ripartire da zero in un click  

---

✨ **In sintesi:** una piattaforma che unisce **data analysis, automazione e networking** per ottimizzare il tuo tempo su GitHub 🚀

---

## 📂 Struttura del progetto
```bash
├── 📁 web-app/
│   ├── 📁 scraping1/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 config.py
│   │   ├── 🐍 github_api.py
│   │   ├── 🐍 main.py
│   │   ├── 🐍 scoring.py
│   │   ├── 🐍 storage.py
│   │   └── 🐍 utils.py
│   │ 
│   ├── 📁 templates/
│   │   ├── 📁 static/
│   │   │   └── 📁 img/
│   │   │       └── 🖼️ favicon.ico
│   │   ├── 🌐 config.html
│   │   ├── 🌐 email_message.html
│   │   ├── 🌐 index.html
│   │   ├── 🌐 manual_email.html
│   │   └── 🌐 my_profile.html
│   │
│   ├── 🐍 __init__.py
│   ├── 🐍 app.py
│   ├── 🐍 db.py
│   ├── 🐍 utils.py
│   └── 🐍 utils_github.py
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

## 📦 Installazione

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