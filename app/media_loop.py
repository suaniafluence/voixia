# app/media_loop.py
import base64
import json                                 # ← nécessaire pour json.dumps
import websockets
import numpy as np
from .audio_utils import mulaw2linear, linear2mulaw
from pathlib import Path
from dotenv import load_dotenv



from .settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_BETA_HEADER,
    VOICE,               # ← ajoute ça
    SYSTEM_MESSAGE       # ← et ça
)
from .logger import logger

async def media_loop(channel_id, ari_client):
    # Ouvrir WS vers OpenAI
    uri = f'wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}'
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": OPENAI_BETA_HEADER
    }
    async with websockets.connect(uri, extra_headers=headers) as openai_ws:
        # Initialisation de la session Realtime
        await openai_ws.send(json.dumps({
            "method": "init",
            "voice": VOICE,
            "systemMessage": SYSTEM_MESSAGE
        }))

        # Boucle ARI WS events
        async for msg in ari_client.ws:
            if msg.get('event') != 'ChannelAgiExec':
                continue
            b64 = msg['args'][2]  # audio en base64
            pcm = mulaw2linear(base64.b64decode(b64))

            # Envoi du flux PCM à OpenAI
            await openai_ws.send(pcm.tobytes())

            # Récupération de la réponse audio
            resp = await openai_ws.recv()
            mu = linear2mulaw(resp)

            # Lecture dans Asterisk
            await ari_client.channels.play(
                channel=channel_id,
                media=f"sound:buffer_{channel_id}",
                playbackId='play'
            )
            logger.debug(f"Réponse audio jouée sur canal {channel_id}")
