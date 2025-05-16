# app/openai_ws.py
import json
import websockets
from .settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BETA_HEADER, SYSTEM_MESSAGE, VOICE
from .logger import logger

async def init_openai_session(ws):
    payload = {
        "method": "init",
        "voice": VOICE,
        "systemMessage": SYSTEM_MESSAGE
    }
    await ws.send(json.dumps(payload))
    logger.info('Session OpenAI initialisée')