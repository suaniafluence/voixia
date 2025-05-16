#!/usr/bin/env python3
import asyncio
import logging
from pjsua2 import Account, Endpoint, Call, AccountConfig, CallInfo
from python_sip import SIPClient
import os
from dotenv import load_dotenv

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO)

class VoixIAAccount(Account):
    """Gère les événements SIP (appels entrants/sortants)"""
    def onIncomingCall(self, call):
        logging.info(f"Appel entrant depuis {call.getInfo().remoteUri}")
        current_call = VoixIACall(self, call.getId())
        call_op = call.getInfo()
        
        # Accepte l'appel automatiquement
        current_call.answer(200)
        
        # Démarrer le flux média
        asyncio.create_task(self.handle_media(call_op.remoteUri))

    async def handle_media(self, remote_uri):
        """Gestion des flux RTP"""
        # Ici vous intégrerez votre logique audio
        pass

class VoixIACall(Call):
    """Gère un appel SIP individuel"""
    def onCallState(self, prm):
        ci = self.getInfo()
        logging.info(f"État appel: {ci.stateText}")

class VoixIAEngine:
    """Moteur principal VoIP"""
    def __init__(self):
        self.ep = Endpoint()
        self.ep.libCreate()
        self.ep.libInit()
        
        # Configuration transport SIP
        self.sip_transport = self.ep.transportCreate(
            "udp", 
            int(os.getenv("SIP_PORT", 5060))
        )
        
        # Configuration compte SIP
        self.account = self.create_account()
        
        # Client SIP complémentaire (si besoin)
        self.sip_client = SIPClient(
            server=os.getenv("SIP_SERVER"),
            username=os.getenv("SIP_USERNAME"),
            password=os.getenv("SIP_PASSWORD")
        )

    def create_account(self):
        """Configure le compte OVH"""
        acfg = AccountConfig()
        acfg.idUri = f"sip:{os.getenv('SIP_USERNAME')}@{os.getenv('SIP_SERVER')}"
        acfg.regConfig.registrarUri = f"sip:{os.getenv('SIP_SERVER')}"
        acfg.sipConfig.authCreds.append({
            "username": os.getenv("SIP_USERNAME"),
            "password": os.getenv("SIP_PASSWORD")
        })
        account = VoixIAAccount()
        account.create(acfg)
        return account

    async def start(self):
        """Démarre le service"""
        self.ep.libStart()
        logging.info(f"SIP enregistré sur {os.getenv('SIP_SERVER')}")

    async def graceful_shutdown(self):
        """Arrêt propre"""
        self.ep.libDestroy()

async def main():
    engine = VoixIAEngine()
    await engine.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await engine.graceful_shutdown()

if __name__ == "__main__":
    asyncio.run(main())