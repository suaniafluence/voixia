import ari
from .settings import ASTERISK_URL, ARI_USER, ARI_PASS
from .logger import logger

# Connexion
client = ari.connect(ASTERISK_URL, ARI_USER, ARI_PASS)
logger.info("Connecté à Asterisk ARI")

def start_ari(on_stasis_cb):
    client.on_channel_event("StasisStart", on_stasis_cb)
    client.run(apps="voixia")
