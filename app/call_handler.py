class CallHandler:
    def __init__(self, audio_stream, gpt_client, response_player):
        self.audio_stream = audio_stream
        self.gpt_client = gpt_client
        self.response_player = response_player

    async def handle_call(self, websocket):
        await self.audio_stream.receive_audio(websocket, self.gpt_client)
        await self.response_player.send_response(websocket, self.gpt_client)