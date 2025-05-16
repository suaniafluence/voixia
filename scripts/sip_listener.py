#!/usr/bin/env python3
import asyncio
import logging
from pjsua2 import Account, Endpoint, Call, AccountConfig, CallInfo, TransportConfig
import os
from dotenv import load_dotenv

# Configuration OVH spécifique
load_dotenv()
logging.basicConfig(level=logging.INFO)

class OVHAccount(Account):
    """Gestion spécialisée pour le SIP OVH"""
    def onIncomingCall(self, call):
        ci = call.getInfo()
        logging.info(f"Appel entrant OVH depuis {ci.remoteUri}")
        
        # Acceptation automatique avec timeout OVH recommandé
        current_call = OVHCall(self, call.getId())
        current_call.answer(200, afterSec=2)  # Délai pour éviter les rejets
        
        # Envoi OPTIONS pour keepalive NAT (important pour OVH)
        asyncio.create_task(self.send_nat_keepalive())

    async def send_nat_keepalive(self):
        """Envoi périodique pour maintenir le NAT ouvert"""
        while True:
            await asyncio.sleep(15)
            try:
                self.pjsua_acc().sendOptions()
            except Exception as e:
                logging.warning(f"Keepalive NAT échoué: {e}")

class OVHCall(Call):
    """Call optimisé pour OVH"""
    def onCallState(self, prm):
        ci = self.getInfo()
        if ci.state == 6:  # DISCONNECTED
            logging.info(f"Call {ci.callIdString} terminé (durée: {ci.connectDuration.sec}s)")
            self.hangup()

class OVHEngine:
    def __init__(self):
        self.ep = Endpoint()
        self.ep.libCreate()
        
        # Config EP pour OVH
        ep_cfg = self.ep.libGetConfig()
        ep_cfg.medConfig.ecTailLen = 0  # Désactive l'echo cancel (géré côté OVH)
        ep_cfg.medConfig.vadEnabled = False  # OVH préfère le silence complet
        
        self.ep.libInit(ep_cfg)
        
        # Transport UDP avec TOS pour QoS OVH
        udp_cfg = TransportConfig()
        udp_cfg.qosType = 5  # DSCP EF pour VoIP
        self.sip_transport = self.ep.transportCreate(
            "udp", 
            int(os.getenv("OVH_SIP_PORT", 5060)), 
            udp_cfg
        )
        
        self.account = self.create_ovh_account()
        
    def create_ovh_account(self):
        """Configuration compte OVH spécifique"""
        acfg = AccountConfig()
        acfg.idUri = f"sip:{os.getenv('OVH_SIP_USER')}@sbc6.fr.sip.ovh"
        acfg.regConfig.registrarUri = "sip:sbc6.fr.sip.ovh"
        
        # Auth OVH (realm fixe)
        acfg.sipConfig.authCreds.append({
            "scheme": "digest",
            "realm": "sbc6.fr.sip.ovh",  # Realm fixe OVH
            "username": os.getenv("OVH_SIP_USER"),
            "password": os.getenv("OVH_SIP_PASSWORD"),
            "dataType": "plaintext"
        })
        
        # Paramètres d'enregistrement OVH
        acfg.regConfig.registrarUri = "sip:sbc6.fr.sip.ovh"
        acfg.regConfig.delayBeforeRefreshSec = 300  # 5min (recommandé OVH)
        acfg.regConfig.dropCallsOnFail = False  # Important pour la résilience
        
        account = OVHAccount()
        account.create(acfg)
        return account

    async def start(self):
        self.ep.libStart()
        
        # Enregistrement forcé initial
        self.account.setRegistration(True)
        logging.info("Enregistrement OVH réussi sur sbc6.fr.sip.ovh")

async def main():
    engine = OVHEngine()
    await engine.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        engine.ep.libDestroy()

if __name__ == "__main__":
    asyncio.run(main())