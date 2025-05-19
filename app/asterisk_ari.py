# app/asterisk_ari.py

import ari
from .settings import ASTERISK_URL, ARI_USER, ARI_PASS
from .logger import logger

client = ari.connect(ASTERISK_URL, ARI_USER, ARI_PASS)

def start_ari(on_stasis_cb):
    logger.info("🟢 Connexion ARI établie")
    client.on_channel_event("StasisStart", on_stasis_cb)
    client.run(apps="voixia")