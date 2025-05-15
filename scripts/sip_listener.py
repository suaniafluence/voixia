# scripts/sip_listener.py

import os
import asyncio
import types
import collections
import collections.abc

# ─── Monkey-patchs pour Python 3.11+ & aiosip 0.2.0 ───────────────
import asyncio as _asyncio
import types as _types
import collections as _collections
import collections.abc as _abc

_asyncio.coroutine = _types.coroutine
_collections.MutableMapping = _abc.MutableMapping

# ─── Imports SIP / config ───────────────────────────────────────────
from dotenv import load_dotenv
import aiosip

load_dotenv()

SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))
CONTACT_URI  = f"sip:{SIP_USERNAME}@{SIP_SERVER}"

# ─── Handler INVITE ────────────────────────────────────────────────
async def on_invite(request, message):
    print("📞 Appel entrant ! From:", message.headers.get('from'))
    await request.respond(180, 'Ringing')
    await asyncio.sleep(1)
    await request.respond(200, 'OK')

# ─── Tâche de rafraîchissement REGISTER ─────────────────────────────
async def refresh_registration(peer):
    while True:
        try:
            await peer.register(
                from_details=(SIP_USERNAME, SIP_SERVER),
                to_details=(SIP_SERVER,),
                password=SIP_PASSWORD,
                contact_uri=CONTACT_URI,
            )
            print("🔄 REGISTER rafraîchi.")
        except Exception as e:
            print("❌ Erreur REGISTER :", e)
        await asyncio.sleep(300)

# ─── Le démarrage du serveur SIP ───────────────────────────────────
async def start_sip_server():
    print("🚀 Démarrage du SIP listener…")
    app_sip = aiosip.Application()

    # 1️⃣ on installe le handler INVITE
    app_sip.register_method('INVITE', on_invite)

    # 2️⃣ on “connecte” au registrar pour obtenir un peer
    peer = await app_sip.connect(
        protocol='udp',
        remote_addr=(SIP_SERVER, SIP_PORT)
    )

    # 3️⃣ on envoie le REGISTER initial
    await peer.register(
        from_details=(SIP_USERNAME, SIP_SERVER),
        to_details=(SIP_SERVER,),
        password=SIP_PASSWORD,
        contact_uri=CONTACT_URI,
    )
    print("✅ Enregistré sur SIP server.")

    # 4️⃣ on lance le rafraîchissement périodique
    asyncio.create_task(refresh_registration(peer))

    # 5️⃣ on démarre la boucle SIP (écoute INVITE, NOTIFY, etc.)
    await app_sip.run(
        local_addr=('0.0.0.0', SIP_PORT),
        protocol='udp'
    )
