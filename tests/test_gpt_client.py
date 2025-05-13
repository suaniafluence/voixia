import pytest
from unittest.mock import AsyncMock, patch
from app.gpt_client import GPTClient

@pytest.mark.asyncio
async def test_initialize_session_sends_correct_payload():
    client = GPTClient()
    mock_ws = AsyncMock()
    client.ws = mock_ws

    await client.initialize_session()

    assert mock_ws.send.call_count == 1
    args = mock_ws.send.call_args[0][0]
    assert '"voice":' in args
    assert '"temperature": 0.8' in args