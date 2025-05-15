# scripts/sip_listener.py

import os
import asyncio
from dotenv import load_dotenv
import aiosip

# 1️⃣ Charge le .env
load_dotenv()

SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))
CONTACT_URI  = f"sip:{SIP_USERNAME}@{SIP_SERVER}"

# 2️⃣ Callback pour gérer les INVITE
async def on_invite(request, message):
    print("📞 Appel entrant ! From:", message.headers.get('from'))
    await request.respond(180, 'Ringing')
    await asyncio.sleep(1)
    await request.respond(200, 'OK')

# 3️⃣ Tâche de refresh REGISTER
async def refresh_registration(endpoint):
    while True:
        try:
            await endpoint.register(
                from_details=(SIP_USERNAME, SIP_SERVER),
                to_details=(SIP_SERVER,),
                password=SIP_PASSWORD,
                contact_uri=CONTACT_URI,
            )
            print("🔄 REGISTER rafraîchi.")
        except Exception as e:
            print("❌ Erreur REGISTER :", e)
        await asyncio.sleep(300)

# 4️⃣ Expose start_sip_server pour FastAPI
async def start_sip_server():
    print("🚀 Démarrage du SIP listener…")
    app_sip = aiosip.Application()
    # crée le endpoint UDP
    endpoint = await app_sip.create_endpoint(
        local_addr=('0.0.0.0', SIP_PORT),
        protocol='udp'
    )

    # enregistrement initial
    await endpoint.register(
        from_details=(SIP_USERNAME, SIP_SERVER),
        to_details=(SIP_SERVER,),
        password=SIP_PASSWORD,
        contact_uri=CONTACT_URI,
    )
    print("✅ Enregistré sur SIP server.")

    # lance la tâche de refresh
    asyncio.create_task(refresh_registration(endpoint))

    # enregistre le handler INVITE
    app_sip.register_method('INVITE', on_invite)

    # démarre la boucle SIP (bloquant)
    await app_sip.run()
