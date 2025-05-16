import os, asyncio, logging
from dotenv import load_dotenv
from PySIP.sip_account import SipAccount
from PySIP.sip_core    import SipCall

# ─── Config ───────────────────────────────────────
load_dotenv()
USER = os.getenv("SIP_USERNAME")
PASS = os.getenv("SIP_PASSWORD")
SRV  = os.getenv("SIP_SERVER")
PORT = int(os.getenv("SIP_PORT", "5060"))

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("sip_listener")

async def run():
    # Création du compte et inscription automatique toutes les 300s
    account = SipAccount(USER, PASS, f"{SRV}:{PORT}", refresh=300)

    # Gestion des appels entrants
    @account.on_incoming_call
    async def on_call(call: SipCall):
        log.info(f"→ Appel entrant: {call.info.call_id}")
        await call.answer(180)       # 180 Ringing
        await asyncio.sleep(1)
        await call.answer(200)       # 200 OK → session établie
        # Ici, PySIP n’a pas de générateur de silence intégré.
        # Vous pouvez lire un fichier WAV mu-law vide si besoin :
        # await call.call_handler.play("silence.ulaw")
        await asyncio.sleep(10)      # durée d’attente
        await call.call_handler.hangup()
        log.info(f"✖️ Appel {call.info.call_id} terminé")

    # Enregistrement SIP
    await account.register()
    log.info("✅ SIP REGISTER OK — en attente d’appels…")

    # On bloque la boucle pour laisser tourner PySIP
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(run())
