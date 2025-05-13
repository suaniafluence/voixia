import pytest
import json
import base64
from unittest.mock import AsyncMock
from app.response_player import ResponsePlayer

@pytest.mark.asyncio
async def test_send_response_sends_audio():
    response_player = ResponsePlayer()
    gpt_mock = AsyncMock()
    audio_data = base64.b64encode(b"audio").decode("utf-8")
    gpt_mock.receive = AsyncMock(return_value=json.dumps({
        "type": "response.audio.delta",
        "delta": audio_data
    }))
    mock_ws = AsyncMock()

    async def stop_after_one(*args, **kwargs):
        raise Exception("Stop loop after first run")

    mock_ws.send_json.side_effect = stop_after_one

    try:
        await response_player.send_response(mock_ws, gpt_mock)
    except Exception as e:
        assert str(e) == "Stop loop after first run"

    mock_ws.send_json.assert_called()