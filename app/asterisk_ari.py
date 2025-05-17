from ari import ARIClient
from .settings import ASTERISK_URL, ARI_USER, ARI_PASS
from .logger import logger

def get_ari_client():
    logger.info('Connexion à Asterisk ARI...')
    client = ARIClient(
        base_url=ASTERISK_URL,
        username=ARI_USER,
        password=ARI_PASS
    )
    client.connect()
    logger.info('Connecté à ARI')
    return client
