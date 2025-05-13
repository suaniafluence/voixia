# 📘 Documentation UML – MVP Agent Vocal IA

Ce dossier contient les principaux diagrammes UML pour modéliser le fonctionnement du MVP de l'agent vocal IA.

## 📂 Contenu

### 1. `use_case.puml`
Diagramme de **cas d’usage** :
- Acteur : Interlocuteur
- Cas d’usage : passer un appel, parler à l’IA, recevoir une réponse, terminer l’appel.

### 2. `activity.puml`
Diagramme **d’activités** montrant le workflow logique d’un appel :
1. Appel reçu
2. Connexion SIP
3. Streaming audio
4. Réception de réponse OpenAI
5. Lecture de la réponse

### 3. `sequence.mmd`
Diagramme **de séquence** en Mermaid :
- Interactions entre l’utilisateur, le système SIP, l’application Python et l’API OpenAI.

### 4. `class.puml`
Diagramme de **classes** montrant l’architecture logicielle du code Python (CallHandler, AudioStream, GPTClient…).

### 5. `deployment.puml`
Diagramme de **déploiement** montrant l’infrastructure :
- Téléphone → OVH SIP → Serveur SIP → App Python → OpenAI API.

## 🛠️ Visualisation

- `.puml` → à ouvrir avec [PlantUML](https://plantuml.com/)
- `.mmd` → à ouvrir avec [Mermaid Live](https://mermaid.live)

# 🎙️ VoixIA — Assistant vocal intelligent via SIP + OpenAI Realtime API

**VoixIA** est un MVP d'assistant vocal connecté à l'API Realtime de OpenAI via un serveur SIP auto-hébergé.

## 🚀 Fonctionnalités

- Réception d’appels via une ligne **SIP OVH**
- Streaming audio vers **l’API Realtime OpenAI (GPT-4o)**
- Réponses vocales synthétisées et renvoyées à l’appelant
- Architecture 100% Python avec **FastAPI**, **WebSocket**, **Twisted SIP**
- Fonctionne sans Twilio ni Ngrok

---

## 📁 Structure du projet

voixia/
├── app/
│ ├── main.py # Point d’entrée FastAPI + init SIP
│ ├── websocket_routes.py # WebSocket /media-stream
│ └── sip_server.py # Serveur SIP UDP (Twisted)
├── .env.example # Exemple de configuration
├── requirements.txt # Dépendances

yaml
Copier
Modifier

---

## 🔐 Configuration

1. Copiez le fichier `.env.example` et renommez-le en `.env`
2. Remplissez vos variables :

```env
OPENAI_API_KEY=sk-...
VOICE=alloy
SIP_SERVER=sip.ovh.net
SIP_PORT=5060
SIP_USERNAME=...@sip.ovh.net
SIP_PASSWORD=...
🛠️ Installation
bash
Copier
Modifier
# Cloner le dépôt
git clone https://github.com/tonuser/voixia.git
cd voixia

# Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # ou venv\\Scripts\\activate sous Windows

# Installer les dépendances
pip install -r requirements.txt
▶️ Lancement
bash
Copier
Modifier
# Depuis la racine du projet
python app/main.py
Vous devriez voir :

"SIP server running on port 5060"

"VoixIA SIP server is running."

🧪 Test WebSocket
Pour tester localement :

bash
Copier
Modifier
wscat -c ws://localhost:5050/media-stream
🧠 À venir
Intégration complète du flux audio vers OpenAI + retour vocal

Transcription en temps réel

Classification d’intention

Redirection vers un humain (optionnel)

Enregistrement des conversations (optionnel)

🧑‍💻 Auteur
Créé par Suan Tay — ingénieur IA & artisan de l'assistance vocale 🛠️
Avec l'aide de ChatGPT pour accélérer l’émergence 💡

⚠️ Licence
Projet MVP éducatif — vous êtes responsable de l’usage des clés API et données sensibles.