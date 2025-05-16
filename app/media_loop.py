# app/media_loop.py
import base64
import numpy as np
import websockets
from .audio_utils import mulaw2linear, linear2mulaw
from .settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BETA_HEADER
from .logger import logger

async def media_loop(channel_id, ari_client):
    # Ouvrir WS vers OpenAI
    uri = f'wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}'
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": OPENAI_BETA_HEADER
    }
    async with websockets.connect(uri, extra_headers=headers) as openai_ws:
        await openai_ws.send(json.dumps({
            "method": "init",
            "voice": VOICE,
            "systemMessage": SYSTEM_MESSAGE
        }))

        # Boucle ARI WS events
        async for msg in ari_client.ws:
            event = msg.get('event')
            if event != 'ChannelAgiExec':
                continue
            args = msg.get('args', [])
            b64 = args[2]  # audio base64
            pcm = mulaw2linear(base64.b64decode(b64))

            # Envoyer à OpenAI
            await openai_ws.send(pcm.tobytes())

            # Recevoir réponse audio
            resp = await openai_ws.recv()
            mu = linear2mulaw(resp)

            # Jouer sur Asterisk
            await ari_client.channels.play(
                channel=channel_id,
                media=f"sound:buffer_{channel_id}",
                playbackId='play'
            )
            logger.debug(f'Response audio jouée sur canal {channel_id}')