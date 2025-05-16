# -*- coding: utf-8 -*-
"""
Optimized SIP listener for OVH using pysip
Includes REGISTER lifecycle, incoming INVITE handling, keep-alive, and clean shutdown
"""
import os
import sys
import signal
import threading
import time
import logging
from dotenv import load_dotenv
import pysip  # bibliothèque pysip pour SIP/RTP

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("sip_listener")

# Chargement des paramètres
load_dotenv()
SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER = os.getenv("SIP_SERVER")  # proxy OVH
SIP_PORT = int(os.getenv("SIP_PORT", "5060"))
PUBLIC_HOST = os.getenv("PUBLIC_HOST")  # IP publique du serveur (pour SDP)
logger.debug(f"Config loaded: username={SIP_USERNAME}, server={SIP_SERVER}, port={SIP_PORT}, public_host={PUBLIC_HOST}")

ep = None
account = None
calls = {}  # stocke les appels actifs

class MyCallHandler(pysip.CallHandler):
    def __init__(self, call):
        super().__init__(call)
        self.call = call
        self.tone_gen = pysip.ToneGenerator()

    def on_state(self, state):
        info = self.call.info()
        logger.info(f"Call {info.id} state: {info.state}")
        if info.state == pysip.CallState.CONFIRMED:
            self.tone_gen.create_channel(0, 0)
            self.tone_gen.start(self.call)
        elif info.state in (pysip.CallState.DISCONNECTED, pysip.CallState.DISCONNECTING):
            self.tone_gen.stop()
            self.call = None
            calls.pop(info.id, None)
            logger.info(f"Call {info.id} cleaned up")

    def on_media(self, media):
        logger.debug(f"Media event for call {self.call.info().id}: {media}")

class MyAccountHandler(pysip.AccountHandler):
    def __init__(self, account):
        super().__init__(account)
        self.account = account

    def on_registration_state(self, info):
        # appelé après REGISTER et renouveaux
        logger.info(f"Registration state: {info.status} ({info.reason}) expires in {info.expires}s")

    def on_incoming_call(self, call):
        call_id = call.info().id
        logger.info(f"Incoming call ID={call_id}")
        calls[call_id] = call
        handler = MyCallHandler(call)
        call.set_handler(handler)
        call.answer(180)  # ringing
        time.sleep(1)
        call.answer(200)  # OK


def init_endpoint():
    global ep
    ep = pysip.Endpoint()
    ep.init(user_agent="OVH-pysip/1.0")
    transport = pysip.TransportConfig(port=SIP_PORT, keepalive=True)
    ep.create_transport(transport)
    ep.start()
    logger.info(f"Endpoint started on port {SIP_PORT}")
    return ep


def create_account(ep):
    global account
    acc_cfg = pysip.AccountConfig(
        id=f"sip:{SIP_USERNAME}@{SIP_SERVER}",
        registrar=f"sip:{SIP_SERVER}:{SIP_PORT}",
        auth=(SIP_USERNAME, SIP_PASSWORD),
        refresh=300
    )
    acc_cfg.extra_headers = [
        f"Contact: <sip:{SIP_USERNAME}@{SIP_SERVER}:{SIP_PORT};transport=udp>",
        "Allow: INVITE, ACK, BYE, CANCEL, OPTIONS, MESSAGE",
        "Expires: 300"
    ]
    account = ep.create_account(acc_cfg)
    handler = MyAccountHandler(account)
    account.set_handler(handler)
    return account


def shutdown(signum, frame):
    global ep, account
    logger.warning(f"Shutdown signal {signum} received, cleaning up")
    # Hangup all active calls
    for call in list(calls.values()):
        try:
            call.hangup()
        except Exception:
            pass
    # Destroy account and endpoint
    if account:
        account.destroy()
    if ep:
        ep.destroy()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    ep = init_endpoint()
    account = create_account(ep)
    logger.info("Ready to register and receive calls!")
    threading.Event().wait()  # maintien du thread principal
