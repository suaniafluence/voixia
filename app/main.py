# app/main.py
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .asterisk_ari import get_ari_client
from .settings import PORT
from .events import on_stasis_start
from .logger import logger

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    ari = get_ari_client()
    ari.on_channel_event('StasisStart', on_stasis_start)
    logger.info('Handler StasisStart enregistré')

@app.get("/", response_class=JSONResponse)
async def index():
    return {"status": "voixia API up and running"}

@app.websocket("/media-stream")
async def media_stream(ws):
    await ws.accept()
    # (Optionnel) traitement direct du stream
    try:
        async for msg in ws.iter_text():
            logger.debug(f"Message WebSocket reçu: {msg}")
    except Exception as e:
        logger.error(f"WS erreur: {e}")