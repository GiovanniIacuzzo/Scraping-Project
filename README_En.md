<h1 align="center" style="font-size: 3rem; font-weight: 600; letter-spacing: 1px;">
GitScore Dashboard
</h1>

<p align="center">
  Questa è la **Versione in Inglese**. passa a:  
  <a href="README.md">🇮🇹 Italiano</a>
</p>

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-black)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20%7C%20Local-green)](https://www.mongodb.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML%20Pipeline-orange)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

Turn GitHub data into actionable insights, automate daily tasks, and manage everything through a sleek, intuitive dashboard.

---

## 🛠️ Tech Stack

- 🐍 **Python 3.9+**
- ⚡ **Flask** (web framework)
- 🍃 **MongoDB** (data storage)
- 🤖 **scikit-learn + imbalanced-learn** (machine learning)
- 📦 **pandas + joblib** (data & model management)
- 🎨 **Bootstrap + Plotly** (UI & interactive charts)
- 📝 **loguru** (advanced logging)

---

## 🌟 What you can do

- Analyze GitHub users with a score based on bio, location, repositories, and README  
- Save structured data in MongoDB  
- Visualize and manage everything from a modern, responsive web dashboard  
- Connect easily: follow users and send personalized emails  

---

## ✨ Key Features

| 📊 **User Analysis**           | 🧮 **Automatic Scoring**      |
|--------------------------------|-------------------------------|
| Scan user bios, locations, repos, and READMEs | Rank users by relevance |

| 📧 **Integrated Emails**       | 💾 **MongoDB Database**       |
|--------------------------------|-------------------------------|
| Send personalized emails directly | Persistent data storage |

| 🌐 **Web Dashboard**           | 🔄 **Quick Reset**            |
|--------------------------------|-------------------------------|
| Filters, charts, and action buttons | Restart from scratch in one click |

---

## 📦 Data Collection

The system gathers data from GitHub using:

- **GitHub API** for username, bio, location, repos, followers/following  
- **Parsing user README and bio** for relevant keywords  
- **MongoDB storage** to ensure persistence and easy querying  

Each stored user includes:

- `username`  
- `bio`  
- `location`  
- `followers / following`  
- `email` (when available)  
- `score` calculated by the ML model  

> ⚡ **Note:** Data collection is batch-based to reduce load and keep the dashboard fast.

---

## 🧠 Machine Learning Model

To determine **user relevance**, a classification model is used:

- **Model input:** bio, README, location, number of followers/following  
- **Model output:** probability that a user is “interesting” for follow or contact  
- **Technology:** `scikit-learn` + custom pipeline  
- **Saved model:** `github_user_classifier.pkl` with config in `github_user_classifier.csv`  

The model is periodically updated via the **Active Learning** interface, where users annotate uncertain profiles to improve classification accuracy.

---

## 🌐 Web Dashboard

- **Flask + Bootstrap** for a modern UI  
- **Interactive data visualization:** filters by city, keywords, score  
- **Quick actions:**  
  - ➕ Follow on GitHub  
  - 📩 Send introduction email  
- **Plotly charts:** followers distribution, city heatmap, database growth trends  

---

## 📂 Project Structure
```bash
├── 📁 web-app/   # Contains all Flask app logic and components
│   │
│   ├── 📁 blueprints/               # Flask blueprints to organize app sections
│   │   ├── 🐍 active_learning_bp.py # Routes and logic for ML Active Learning
│   │   ├── 🐍 email_bp.py           # Handles sending personalized emails
│   │   ├── 🐍 main_bp.py            # Main dashboard routes (home, stats)
│   │   ├── 🐍 scraper_bp.py         # Routes for data scraping management
│   │   ├── 🐍 user_bp.py            # User actions & visualization (e.g., follow)
│   │   └── 🐍 utils_bp.py           # Utility functions used by blueprints
│   │
│   ├── 📁 models/                   # Data models (e.g., MongoDB schemas)
│   │   └── 🐍 user_model.py         # Example: data model for 'users' collection
│   │
│   ├── 📁 scraping1/                # Scraping and analysis logic
│   │   ├── 🐍 __init__.py           
│   │   ├── 🐍 config.py             
│   │   ├── 🐍 github_api.py         
│   │   ├── 🐍 main.py               
│   │   ├── 🐍 scoring.py            
│   │   ├── 🐍 storage.py            
│   │   └── 🐍 utils.py              
│   │
│   ├── 📁 static/                   # Static files (CSS, JS, images)
│   │   ├── 📁 css/                  
│   │   │   └── 🎨 style.css         
│   │   └── 📁 img/                  
│   │       └── 🖼️ favicon.ico       
│   │
│   ├── 📁 templates/                # Jinja2 HTML templates
│   │   ├── 🌐 active_learning.html  
│   │   ├── 🌐 config.html           
│   │   ├── 🌐 email_message.html    
│   │   ├── 🌐 index.html            
│   │   ├── 🌐 manual_email.html     
│   │   └── 🌐 my_profile.html       
│   │
│   ├── 📄 Dataset_init.csv          
│   ├── 🐍 __init__.py               
│   ├── 🐍 app.py                    
│   ├── 🐍 config.py                 
│   ├── 🐍 db.py                     
│   ├── 🐍 ml_model.py               
│   ├── 🐍 train_model.py            
│   ├── 🐍 utils.py                  
│   └── 🐍 utils_github.py           
│
├── 🔒 .env                          
├── 🚫 .gitignore                    
├── 📖 README.md                     
└── 📄 requirements.txt              
```

---

## ⚙️ Requirements

- **Python 3.9+**
- **MongoDB** installed locally or in the cloud (e.g. MongoDB Atlas)
- A **GitHub token** with read `read:user` and `user:follow` permissions
- A **SMTP email account** (es. Gmail) o send emails

---

## 📦 Setup

1. **Clone the project**
```bash
git clone https://github.com/tuo-username/scraping-project.git
cd scraping-project
```
Install dependencies:

```bash
pip install -r requirements.txt
```

2. **Configure the .env file**
Create a `.env` file in the project root with your credentials and config (see Italian version for details).

```bash
# ================================
# GitHub / scraping
# ================================
GITHUB_TOKEN=your_token            # Your GitHub Personal Access Token (required for API)
GITHUB_API=https://api.github.com  # GitHub API endpoint
MY_CITY=insert_a_city              # The city to use as the starting point for the search
NEARBY_CITIES=Rome,Milan,Turin     # List of nearby cities, comma-separated (e.g. "Rome,Milan")
KEYWORDS_BIO=python,data science   # Keywords to filter user bios (comma-separated)
KEYWORDS_README=flask,mongodb      # Keywords to filter user READMEs (comma-separated)
ITALIAN_LOCATIONS=Italy,Italia     # Names of Italian locations to consider (comma-separated)
N_USERS=10                         # Max number of users to fetch per scraping cycle
REQUEST_DELAY=1                    # Delay (in seconds) between GitHub API requests to avoid rate limiting
seed=your_github_username          # GitHub username to start the search from (your own account is recommended)

# ================================
# Flask
# ================================
FLASK_SECRET_KEY=your_secret_key   # Secret key for Flask session security

# ================================
# Email
# ================================
EMAIL_HOST=smtp.gmail.com            # SMTP host (e.g. smtp.gmail.com)
EMAIL_PORT=587                       # SMTP port
EMAIL_USER=your_email@example.com    # Your email for sending messages
EMAIL_PASSWORD=your_app_password     # App password generated by your email provider (e.g. Google, Outlook)
MAIL_USE_TLS=True                    # Enable StartTLS
MAIL_USE_SSL=False                   # Disable direct SSL if using TLS

# Email debug mode
DEBUG_EMAIL_MODE=true                       # If TRUE, emails will only be sent to DEBUG_EMAIL
DEBUG_EMAIL=test_recipient@example.com      # Email address for testing in debug mode (can stay as is)

# ================================
# GitHub profile configuration
# ================================
MY_GITHUB_PROFILE=https://github.com/your-username  # Link to your GitHub profile
KEY_USERS=user1,user2                               # List of "key" GitHub usernames (comma-separated)
```

3. **Setup MongoDB**

Remember to download MongoDB and create a collection:

```bash
mongosh
use scraping-project
```

Check saved users:
```bash
db.users.find().pretty()
```

4. **Run the project**

```bash
cd web-app
python app.py
```
Go to: http://127.0.0.1:5050

---

## 🤝 Contribuire
Pull requests are welcome!
For major changes, please open an issue first to discuss what you’d like to change.

---

## 📜 Licenza
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---