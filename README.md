# 🎙️ Voixia

voixia transforme vos appels téléphoniques en conversations animées avec un assistant IA en temps réel, propulsé par Asterisk et l’API Realtime d’OpenAI.

🛠️ Prérequis

Python 3.11+

Asterisk 18+ (avec ARI activé)

Un compte OVH SIP (trunk SIP configuré)

Clé API OpenAI avec accès au modèle Realtime

Environnement Unix (Linux, macOS)

pip pour installer les dépendances

🚀 Installation

Cloner le dépôt

git clone https://github.com/ton-org/voixia.git
cd voixia

Créer et configurer votre environnement virtuel

python -m venv .venv
source .venv/bin/activate

Installer les dépendances

pip install -r requirements.txt

Configurer les variables d’environnement dans un fichier .env à la racine :

OPENAI_API_KEY=sk-…
ARI_USER=voixia_user
ARI_PASS=unSecretDeFolie
ASTERISK_URL=http://localhost:8088
PORT=8000

Copier les fichiers de config Asterisk dans /etc/asterisk/ :

pjsip.conf

extensions.conf

⚙️ Architecture

OVH SIP Trunk
     ↓
  Asterisk (pjsip.conf)
     ↓  extensions.conf (Stasis « openai-realtime »)
 FastAPI + ARI
 ├── main.py          → endpoints HTTP/WebSocket
 ├── settings.py      → lecture du .env
 ├── asterisk_ari.py  → connexion ARI & handlers
 ├── events.py        → gestion StasisStart, media…
 ├── media_loop.py    → boucle ARI ↔ OpenAI Realtime
 └── audio_utils.py   → transcodage μ-law ⇄ PCM16
     ↓
OpenAI Realtime API
     ↕
Synthèse vocale & transcription
     ↓
  Utilisateur au téléphone

📞 Utilisation

Lancer Asterisk et assurez-vous qu’ARI est accessible.

Démarrer l’application :

uvicorn app.main:app --host 0.0.0.0 --port $PORT

Passez un appel sur votre numéro OVH :

Attendez le message de bienvenue.

Discutez normalement, voixia s’occupe de tout.