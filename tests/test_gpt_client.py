import pytest
from unittest.mock import AsyncMock
from app.gpt_client import GPTClient

@pytest.mark.asyncio
async def test_initialize_session_sends_correct_payload():
    # Prépare un client « connecté »
    client = GPTClient()
    mock_ws = AsyncMock()
    client.ws = mock_ws

    # Appel de la méthode publique
    await client.initialize_session()

    # On a bien envoyé un unique message
    assert mock_ws.send.call_count == 1

    # On vérifie que le payload contient bien les clés attendues
    sent_payload = mock_ws.send.call_args.args[0]
    assert '"voice":' in sent_payload
    assert '"temperature": 0.8' in sent_payload

@pytest.mark.asyncio
async def test_initialize_session_raises_if_not_connected():
    # Si la WS n'est pas initialisée, on doit obtenir une erreur
    client = GPTClient()
    client.ws = None

    with pytest.raises(RuntimeError) as exc:
        await client.initialize_session()
    assert "WebSocket non connecté" in str(exc.value)
