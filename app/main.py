# app/main.py

# app/main.py
import threading
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .asterisk_ari import start_ari, client
from .settings import PORT
from .events import on_stasis_start
from .logger import logger

 app = FastAPI()

 @app.on_event("startup")
 async def startup_event():

    # Branche l’événement et démarre la boucle ARI dans un thread séparé
    client.on_channel_event('StasisStart', on_stasis_start)
    threading.Thread(
        target=lambda: start_ari(apps="voixia"),
        daemon=True
    ).start()
    logger.info('Boucle ARI démarrée en arrière-plan (voixia)')

 @app.get("/", response_class=JSONResponse)
 async def index():
     return {"status": "voixia API up and running"}

 @app.websocket("/media-stream")
 async def media_stream(ws):
     await ws.accept()
     try:
         async for msg in ws.iter_text():
             logger.debug(f"Message WebSocket reçu: {msg}")
     except Exception as e:
         logger.error(f"WS erreur: {e}")
