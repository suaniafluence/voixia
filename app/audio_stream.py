import json

class AudioStream:
    async def receive_audio(self, websocket, gpt_client):
        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                if data.get("type") == "audio":
                    await gpt_client.send_audio(data["payload"])
        except Exception as e:
            print(f"AudioStream error: {e}")