# scripts/sip_listener.py

import asyncio
import os
import aiosip

SIP_USERNAME = os.getenv("SIP_USERNAME", "suantay")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER = os.getenv("SIP_SERVER", "sip.linphone.org")
SIP_PORT = int(os.getenv("SIP_PORT", 5060))
CONTACT_URI = f"sip:{SIP_USERNAME}@{SIP_SERVER}"

async def on_invite(request, message):
    print("📞 Appel entrant reçu !")
    print("📍 From:", message.headers.get('from'))
    await request.respond(180, 'Ringing')
    await asyncio.sleep(1)
    await request.respond(200, 'OK')

async def main():
    app = aiosip.Application()
    await app.run()

    print(f"📡 Création du endpoint SIP sur 0.0.0.0:{SIP_PORT}")
    endpoint = await app.create_endpoint(local_addr=('0.0.0.0', SIP_PORT), protocol='udp')

    print(f"🔐 Enregistrement en cours auprès de {SIP_SERVER}...")
    await endpoint.register(
        from_details=(SIP_USERNAME, SIP_SERVER),
        to_details=(SIP_SERVER,),
        password=SIP_PASSWORD,
        contact_uri=CONTACT_URI
    )
    print("✅ Enregistré avec succès.")

    app.register_method('INVITE', on_invite)

    print("🚀 Serveur SIP prêt à recevoir les appels.")
    await asyncio.Event().wait()  # Reste actif

if __name__ == "__main__":
    asyncio.run(main())
