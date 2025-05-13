# 🎙️ VoixIA — Assistant vocal intelligent via SIP + OpenAI Realtime API

![Tests](https://github.com/suaniafluence/voixia/actions/workflows/python-tests.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

**VoixIA** est un MVP d'assistant vocal connecté à l'API Realtime de OpenAI via un serveur SIP auto-hébergé.

## 🚀 Fonctionnalités

- Réception d’appels via une ligne **SIP OVH**
- Streaming audio vers **l’API Realtime OpenAI (GPT-4o)**
- Réponses vocales synthétisées et renvoyées à l’appelant
- Architecture 100% Python avec **FastAPI**, **WebSocket**, **Twisted SIP**
- Fonctionne sans Twilio ni Ngrok

---

## 📁 Structure du projet

```
voixia/
├── app/
│   ├── main.py
│   ├── websocket_routes.py
│   ├── sip_server.py
│   ├── call_handler.py
│   ├── gpt_client.py
│   ├── audio_stream.py
│   └── response_player.py
├── tests/
├── .env.example
├── requirements.txt
└── .github/workflows/python-tests.yml
```

---

## 🔐 Configuration

1. Copiez `.env.example` en `.env`
2. Remplissez vos variables :

```env
OPENAI_API_KEY=sk-...
VOICE=alloy
SIP_SERVER=sip.ovh.net
SIP_PORT=5060
SIP_USERNAME=...
SIP_PASSWORD=...
```

---

## 🛠️ Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ▶️ Lancement

```bash
python app/main.py
```

---

## 🧪 Tests

```bash
pip install pytest pytest-asyncio pytest-cov
pytest --cov=app tests/
```

---

## 🧠 À venir

- Transcription en temps réel
- Classification d’intention
- Enregistrement de conversations
- UI Web ou dashboard pour config

---

## 🧑‍💻 Auteur

Créé par **Suan Tay** — ingénieur IA  
Avec l'aide de ChatGPT pour la structuration rapide

---

## ⚠️ Licence

Projet MVP éducatif — usage personnel ou en démo uniquement.