import pytest
from unittest.mock import AsyncMock
from app.call_handler import CallHandler
from app.audio_stream import AudioStream
from app.gpt_client import GPTClient
from app.response_player import ResponsePlayer

@pytest.mark.asyncio
async def test_call_handler_runs_audio_and_response():
    audio_mock = AsyncMock()
    gpt_mock = AsyncMock()
    response_mock = AsyncMock()

    handler = CallHandler(audio_mock, gpt_mock, response_mock)

    websocket_mock = AsyncMock()

    await handler.handle_call(websocket_mock)

    audio_mock.receive_audio.assert_called_once_with(websocket_mock, gpt_mock)
    response_mock.send_response.assert_called_once_with(websocket_mock, gpt_mock)