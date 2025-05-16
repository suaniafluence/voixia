import os
from dotenv import load_dotenv

load_dotenv()

# Asterisk ARI
ASTERISK_URL = os.getenv('ASTERISK_URL', 'http://localhost:8088')
ARI_USER = os.getenv('ARI_USER')
ARI_PASS = os.getenv('ARI_PASS')

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = 'gpt-4o-realtime-preview-2024-10-01'
OPENAI_BETA_HEADER = 'realtime=v1'
SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created'
]

# Server
PORT = int(os.getenv('PORT', 8000))