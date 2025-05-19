# app/asterisk_ari.py

from py3ari.client import ARIClient
from .settings import ASTERISK_URL, ARI_USER, ARI_PASS
from .logger import logger

client = None

def get_ari_client():
    global client
    if client is None:
        try:
            logger.info("Connexion à Asterisk ARI...")
            client = ARIClient(
                base_url=ASTERISK_URL,
                username=ARI_USER,
                password=ARI_PASS,
                load_swagger=False  # ← évite le 404 sur /resources.json
            )
            client.connect()
            logger.info("✅ Connexion ARI établie avec succès.")
        except Exception as e:
            logger.error(f"❌ Connexion ARI échouée : {e}")
            raise
    return client

def start_ari(on_stasis_cb):
    ari = get_ari_client()
    ari.on_channel_event("StasisStart", on_stasis_cb)
    logger.info("🪝 Handler 'StasisStart' enregistré")
    ari.run(apps="voixia")  # ← doit correspondre à ce que tu mets dans extensions.conf
