import json
import websockets
import os

class GPTClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.voice = os.getenv("VOICE", "alloy")
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            extra_headers={
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
        )
        await self.initialize_session()

    async def initialize_session(self):
        session_update = {
            "type": "session.update",
            "session": {
                "voice": self.voice,
                "modalities": ["text", "audio"],
                "temperature": 0.8,
            }
        }
        await self.ws.send(json.dumps(session_update))

    async def send_audio(self, audio_payload):
        event = {
            "type": "input_audio_buffer.append",
            "audio": audio_payload
        }
        await self.ws.send(json.dumps(event))

    async def receive(self):
        return await self.ws.recv()