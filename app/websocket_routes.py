import asyncio
from fastapi import WebSocket, APIRouter
from app.call_handler import CallHandler
from app.audio_stream import AudioStream
from app.gpt_client import GPTClient
from app.response_player import ResponsePlayer

websocket_router = APIRouter()

@websocket_router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")

    gpt_client = GPTClient()
    await gpt_client.connect()

    audio_stream = AudioStream()
    response_player = ResponsePlayer()
    handler = CallHandler(audio_stream, gpt_client, response_player)

    await asyncio.gather(
        handler.audio_stream.receive_audio(websocket, handler.gpt_client),
        handler.response_player.send_response(websocket, handler.gpt_client)
    )