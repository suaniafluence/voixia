# scripts/sip_listener.py

import os
import asyncio
import socket
import uuid

from dotenv import load_dotenv
import aiosip

# ─── 1. Charge la config depuis .env ───────────────────────────
load_dotenv()

SIP_USERNAME = os.getenv("SIP_USERNAME", "suantay")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER", "sip.linphone.org")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))
CONTACT_URI  = f"sip:{SIP_USERNAME}@{SIP_SERVER}"

# ─── 2. Callback pour les INVITE entrants ──────────────────────
async def on_invite(request, message):
    print("📞 Appel entrant ! From:", message.headers.get('from'))
    await request.respond(180, 'Ringing')
    await asyncio.sleep(1)
    await request.respond(200, 'OK')

# ─── 3. Routine pour rafraîchir le REGISTER ────────────────────
async def refresh_registration(endpoint):
    interval = 300  # toutes les 5 min
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
        await asyncio.sleep(interval)

# ─── 4. Entrypoint ───────────────────────────────────────────────
async def main():
    # Crée l’app et le endpoint avant d’appeler run()
    app = aiosip.Application()
    endpoint = await app.create_endpoint(
        local_addr=('0.0.0.0', SIP_PORT),
        protocol='udp'
    )

    print(f"🔐 Enregistrement initial auprès de {SIP_SERVER}…")
    await endpoint.register(
        from_details=(SIP_USERNAME, SIP_SERVER),
        to_details=(SIP_SERVER,),
        password=SIP_PASSWORD,
        contact_uri=CONTACT_URI,
    )
    print("✅ Enregistré avec succès.")

    # Lance une tâche de refresh périodique
    asyncio.create_task(refresh_registration(endpoint))

    # Déclare le handler INVITE
    app.register_method('INVITE', on_invite)
    print("🚀 Serveur SIP prêt, en attente d’appels…")

    # Lance la boucle events (bloquant)
    await app.run()


