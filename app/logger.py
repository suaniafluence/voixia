# app/logger.py
import logging
from .settings import LOG_EVENT_TYPES

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('voixia')
for evt in LOG_EVENT_TYPES:
    logging.getLogger(evt).setLevel(logging.DEBUG)