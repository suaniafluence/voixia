# tests/test_openai_ws.py
import pytest
from app.openai_ws import init_openai_session

class DummyWS:
    def __init__(self): self.sent = []
    async def send(self, data): self.sent.append(data)

@pytest.mark.asyncio
async def test_init_session():
    ws = DummyWS()
    await init_openai_session(ws)
    assert len(ws.sent) == 1
    assert 'init' in ws.sent[0]