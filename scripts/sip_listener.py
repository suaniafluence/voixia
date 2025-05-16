# -*- coding: utf-8 -*-
"""
Optimized SIP listener for OVH using pjsua2
"""
import os
import sys
import signal
import threading
import time
import logging
from dotenv import load_dotenv
import pjsua2 as pj

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("sip_listener")

load_dotenv()
SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER = os.getenv("SIP_SERVER")
SIP_PORT = int(os.getenv("SIP_PORT", "5060"))
PUBLIC_HOST = os.getenv("PUBLIC_HOST")
logger.debug(f"Config loaded: SIP_USERNAME={SIP_USERNAME}, SIP_SERVER={SIP_SERVER}, SIP_PORT={SIP_PORT}, PUBLIC_HOST={PUBLIC_HOST}")

ep = None

class MyCallCallback(pj.CallCallback):
    def __init__(self, call=None):
        super().__init__(call)
        self.tone_gen = pj.ToneGenerator()
        logger.debug(f"MyCallCallback created for call ID={self.call.getId()}")

    def onState(self, prm: pj.OnCallStateParam):
        info = self.call.getInfo()
        logger.info(f"Call {self.call.getId()} state changed: {info.stateText}")
        if info.state == pj.PJSIP_INV_STATE_CONFIRMED:
            logger.debug(f"Call {self.call.getId()} confirmed, starting silence transmission")
            self.tone_gen.createChannel(0, 0)
            self.tone_gen.startTransmit(self.call)

    def onMediaState(self, prm: pj.OnCallMediaStateParam):
        logger.debug(f"Call {self.call.getId()} media state changed: {prm}")

class MyAccountCallback(pj.AccountCallback):
    def __init__(self, account=None):
        super().__init__(account)
        self.logger = logging.getLogger("MyAccountCallback")

    def onIncomingCall(self, prm: pj.OnIncomingCallParam):
        self.logger.info(f"Incoming call received: callId={prm.callId}")
        call = pj.Call(self.account, prm.callId)
        call_cb = MyCallCallback(call)
        call.setCallback(call_cb)
        self.logger.debug(f"Answering 180 Ringing for callId={call.getId()}")
        call.answer(180, "Ringing")
        time.sleep(1)
        self.logger.debug(f"Answering 200 OK for callId={call.getId()}")
        call.answer(200, "OK")

def init_endpoint() -> pj.Endpoint:
    logger.info(f"Initializing PJSUA2 endpoint on port {SIP_PORT}")
    endpoint = pj.Endpoint()
    endpoint.libCreate()
    ua_cfg = pj.EpConfig()
    ua_cfg.uaConfig.userAgent = "OVH-pjsua2/1.0"
    ua_cfg.uaConfig.maxCalls = 4
    endpoint.libInit(ua_cfg)
    tp_cfg = pj.TransportConfig()
    tp_cfg.port = SIP_PORT
    tp_cfg.setQosType(pj.PjQosType.PJ_QOS_SIGNALING)
    tp_cfg.enableKeepAlive = True
    endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)
    endpoint.libStart()
    logger.info(f"🚀 Endpoint SIP démarré sur 0.0.0.0:{SIP_PORT}")
    return endpoint

def create_account(endpoint: pj.Endpoint) -> pj.Account:
    logger.info("Creating SIP account and registering...")
    acc_cfg = pj.AccountConfig()
    acc_cfg.idUri = f"sip:{SIP_USERNAME}@{SIP_SERVER}"
    acc_cfg.regConfig.registrarUri = f"sip:{SIP_SERVER}:{SIP_PORT}"
    acc_cfg.sipConfig.authCreds.append(pj.AuthCredInfo("digest", "*", SIP_USERNAME, 0, SIP_PASSWORD))
    acc_cfg.regConfig.timeoutSec = 300
    account = pj.Account()
    account.create(acc_cfg)
    account.setCallback(MyAccountCallback(account))
    return account

def shutdown(signum, frame):
    global ep
    logger.warning(f"Shutdown signal received ({signum}), destroying endpoint...")
    if ep:
        try:
            ep.libDestroy()
            logger.info("Endpoint destroyed successfully")
        except Exception as e:
            logger.error(f"Error destroying endpoint: {e}")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    ep = init_endpoint()
    acc = create_account(ep)
    logger.info("✅ Prêt à recevoir des appels !")
    threading.Event().wait()
