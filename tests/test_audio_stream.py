import pytest
import json
from unittest.mock import AsyncMock
from app.audio_stream import AudioStream

@pytest.mark.asyncio
async def test_receive_audio_parses_json():
    mock_websocket = AsyncMock()
    mock_websocket.receive_text.side_effect = ['{"type": "audio", "payload": "abc123"}', Exception("Done")]

    gpt_mock = AsyncMock()
    audio_stream = AudioStream()

    await audio_stream.receive_audio(mock_websocket, gpt_mock)

    mock_websocket.receive_text.assert_called()