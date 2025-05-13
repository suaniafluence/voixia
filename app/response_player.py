import json
import base64

class ResponsePlayer:
    async def send_response(self, websocket, gpt_client):
        try:
            while True:
                response = await gpt_client.receive()
                parsed = json.loads(response)
                if parsed.get("type") == "response.audio.delta" and "delta" in parsed:
                    payload = parsed["delta"]
                    audio_base64 = base64.b64encode(base64.b64decode(payload)).decode("utf-8")
                    await websocket.send_json({
                        "event": "media",
                        "media": {"payload": audio_base64}
                    })
        except Exception as e:
            print(f"ResponsePlayer error: {e}")