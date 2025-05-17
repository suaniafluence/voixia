# voixia

**voixia** transforme vos appels téléphoniques en conversations animées avec un assistant IA en temps réel, propulsé par Asterisk et l’API Realtime d’OpenAI.

---

## 🛠️ Prérequis

- **Python 3.11+**
- **Asterisk 18+** (avec ARI activé)
- Un compte **OVH SIP** (trunk SIP configuré)
- **Clé API OpenAI** avec accès au modèle Realtime
- **py3ari==0.1.4** : client Python pour l’ARI d’Asterisk  
  _Permet de piloter Asterisk via son REST API directement depuis Python._
- Environnement Unix (Linux, macOS)
- `pip` pour installer les dépendances

---

## 🚀 Installation

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/suaniafluence/voixia.git
   cd voixia
   ```

2. **Créer et configurer** votre environnement virtuel
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d’environnement** dans un fichier `.env` :
   ```env
   OPENAI_API_KEY=sk-…
   ARI_USER=voixia_user
   ARI_PASS=unSecretDeFolie
   ASTERISK_URL=http://localhost:8088
   PORT=8000
   ```

5. **Configurer Asterisk** en copiant `pjsip.conf` et `extensions.conf` dans `/etc/asterisk/`.

---

## ⚙️ Architecture

```plaintext
OVH SIP Trunk
     ↓
  Asterisk (pjsip.conf)
     ↓  extensions.conf (Stasis « voixia »)
 FastAPI + ARI (py3ari)
 ├── main.py          → endpoints HTTP/WebSocket
 ├── settings.py      → lecture du .env
 ├── asterisk_ari.py  → connexion ARI & handlers
 ├── events.py        → gestion des événements ARI
 ├── media_loop.py    → boucle audio ↔ OpenAI Realtime
 └── audio_utils.py   → transcodage μ-law ⇄ PCM16
     ↓
OpenAI Realtime API
     ↕
Synthèse vocale & transcription
     ↓
  Utilisateur au téléphone
```  

---

## 📞 Utilisation

1. **Démarrer l’application** :
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
2. **Redémarrer Asterisk** et rechargez le dialplan :
   ```bash
   sudo asterisk -rx "dialplan reload"
   sudo asterisk -rx "module reload res_ari.so"
   ```
3. **Passez un appel** sur votre numéro OVH : 
   - Attendez le message de bienvenue.
   - Discutez normalement, voixia s’occupe de tout.

> **Astuce** : activez les logs détaillés dans `logger.py` pour déboguer les événements ARI.

---

## 🧪 Tests

```bash
pytest --maxfail=1 --disable-warnings -q
```  

---

## 🤝 Contribuer

1. Forkez ce dépôt.
2. Créez une branche feature : `git checkout -b feature/ma-super-idée`
3. Committez vos changements : `git commit -m "Ajout : ma super feature"`
4. Poussez : `git push origin feature/ma-super-idée`
5. Ouvrez une Pull Request.

---

## 🦉 Licence

MIT © 2025
