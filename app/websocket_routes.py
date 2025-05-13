import json
from fastapi import WebSocket, APIRouter

websocket_router = APIRouter()

@websocket_router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Message: {message}")
            await websocket.send_text(f"Echo: {message}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket closed.")