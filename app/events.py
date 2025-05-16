# app/events.py
import asyncio
from .asterisk_ari import get_ari_client
from .media_loop import media_loop
from .logger import logger

async def on_stasis_start(event, channel):
    cid = channel.json['id']
    logger.info(f'StasisStart sur canal {cid}')

    # Créer un bridge pour mixer
    bridge = await channel._client.bridges.create(type='mixing', name=cid)
    await bridge.addChannel(channel=cid)

    # Souscription media
    await channel._client.send_message({
        'method': 'POST',
        'path': f'/channels/{cid}/media',
        'body': {'formats': ['slin16'], 'subscriptionId': 'media_sub'}
    })

    # Lancer boucle media ↔ OpenAI
    asyncio.create_task(media_loop(cid, channel._client))