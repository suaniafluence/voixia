# gpt_client.py

import os
import json
import asyncio
import websockets
from typing import AsyncIterator, Optional

class GPTClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.voice   = os.getenv("VOICE", "alloy")
        self.model   = os.getenv(
            "REALTIME_MODEL", 
            "gpt-4o-realtime-preview-2024-10-01"
        )
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self) -> None:
        """ Ouvre la connexion WebSocket et initialise la session. """
        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta":   "realtime=v1",
        }
        self.ws = await websockets.connect(url, extra_headers=headers)
        await self._initialize_session()

    async def _initialize_session(self) -> None:
        """ Envoi du message session.update (voice, modalities, temp). """
        assert self.ws, "WebSocket non connecté"
        msg = {
            "type": "session.update",
            "session": {
                "voice": self.voice,
                "modalities": ["text", "audio"],
                "temperature": 0.8
            }
        }
        await self.ws.send(json.dumps(msg))

    async def send_text(self, text: str) -> None:
        """ Envoie un prompt textuel. """
        assert self.ws, "WebSocket non connecté"
        msg = {
            "type": "input_text",
            "text": text
        }
        await self.ws.send(json.dumps(msg))

    async def send_audio(self, audio_bytes: bytes) -> None:
        """ Envoie un buffer audio (PCM16 ou base64, selon la spec). """
        assert self.ws, "WebSocket non connecté"
        payload = {
            "type":  "input_audio_buffer.append",
            "audio": audio_bytes.decode("latin1")  # ou base64 si nécessaire
        }
        await self.ws.send(json.dumps(payload))

    async def close(self) -> None:
        """ Ferme proprement la WS. """
        if self.ws:
            await self.ws.close()

    async def stream_events(self) -> AsyncIterator[dict]:
        """
        Itérateur asynchrone sur les events reçus de la WS.
        Chaque event est un dict JSON, pouvant contenir :
          - type="delta.text"    → streaming texte
          - type="delta.audio"   → fragment audio TTS
          - type="session.event" → infos de session (silences, erreurs…)
        """
        assert self.ws, "WebSocket non connecté"
        async for raw in self.ws:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            yield event

# --- Exemple d’utilisation ---

async def demo():
    client = GPTClient()
    await client.connect()

    # 1) Envoyer du texte et démarrer la boucle d’événements
    await client.send_text("Bonjour, comment ça va ?")
    async for evt in client.stream_events():
        t = evt.get("type")
        if t == "delta.text":
            print("GPT écrit    ▶", evt["text"])
        elif t == "delta.audio":
            # evt["audio"] contient un fragment audio encodé
            data = evt["audio"].encode("latin1")
            # ici, tu pourrais pipe vers un player RTP/websocket
            print("GPT audio   ▶", len(data), "octets")
        elif t == "session.event" and evt.get("event") == "complete":
            print("✅ Réponse terminée !")
            break

    await client.close()

if __name__ == "__main__":
    asyncio.run(demo())
