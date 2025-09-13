# 🤖 GitHub Smart Follower Dashboard

Questo progetto permette di **analizzare utenti GitHub**, assegnare loro un punteggio basato su **bio, location, repos e README**, salvarli in un database **MongoDB**, e visualizzarli tramite una **dashboard web** con filtri avanzati.  
In più è possibile **seguire automaticamente gli utenti** e inviare **email di presentazione** (se hanno un indirizzo pubblico disponibile).

---

## ✨ Funzionalità principali
- 🔍 **Ricerca automatica utenti GitHub** in base a:
  - Location (**Italia**, con priorità alta agli utenti vicini a *Enna*)
  - Keywords nella bio o nei README
  - Followers / Following in range realistici
- 🧮 **Algoritmo di scoring personalizzato** per classificare gli utenti
- 📧 **Estrazione email pubbliche** da bio e README
- 💾 **Salvataggio utenti su MongoDB**
- 🌐 **Dashboard web (Flask + Bootstrap)** con:
  - Filtri per città, followers, keywords
  - Ordinamento per score, followers o following
  - Pulsanti rapidi per:
    - Seguire l’utente su GitHub
    - Inviare email HTML di presentazione
- 🔄 **Script di refresh** (`refresh.py`) per resettare il database

---

## 📂 Struttura del progetto
```bash
├── app.py              # Avvio della dashboard Flask
├── scraping1.py        # Script principale per cercare e salvare utenti
├── refresh.py          # Script per svuotare il database utenti
│
├── templates/
│ └── dashboard.html    # Frontend della dashboard (Bootstrap)
│
├── requirements.txt    # Dipendenze Python
├── .env                # Variabili di configurazione
│
└── README.md           # Questo file
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

FLASK_SECRET_KEY=lamiachiavesegreta02
```

## 🚀 Utilizzo

### 1. Avvia lo scraper
Lo scraper interroga l’API di GitHub, calcola il punteggio di ciascun utente e salva i risultati nel database MongoDB.

```bash
python scraping1.py
```
2. **Avvia la dashboard**
La dashboard Flask ti permette di visualizzare e filtrare gli utenti trovati.
```bash
python app.py
```
Dopo l’avvio, apri il browser e vai su 👉 http://localhost:5000

3. **Resetta il database**
Se vuoi rimuovere tutti gli utenti salvati dal database:
```bash
python refresh.py
```