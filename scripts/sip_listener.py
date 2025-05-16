#!/usr/bin/env python3
import sys
import logging
import asyncio
from pysip import Client, Via, FromHeader, ToHeader, URI
from pysip.message import Request, Response
import os
from dotenv import load_dotenv

# Configuration OVH
load_dotenv()
logging.basicConfig(level=logging.INFO)

SIP_CONFIG = {
    'server': os.getenv('OVH_SIP_SERVER', 'sbc6.fr.sip.ovh'),
    'user': os.getenv('OVH_SIP_USER'),
    'password': os.getenv('OVH_SIP_PASSWORD'),
    'port': int(os.getenv('OVH_SIP_PORT', 5060)),
    'local_ip': '0.0.0.0'
}

class OVHSipHandler:
    """Gestionnaire d'événements SIP pour OVH"""
    def __init__(self):
        self.client = Client(
            local_ip=SIP_CONFIG['local_ip'],
            local_port=SIP_CONFIG['port'],
            realm=SIP_CONFIG['server'],
            username=SIP_CONFIG['user'],
            password=SIP_CONFIG['password']
        )
        
        # Enregistrement des callbacks
        self.client.on_request = self.handle_request
        self.client.on_response = self.handle_response

    async def handle_request(self, request):
        """Traite les requêtes SIP entrantes"""
        if request.method == 'INVITE':
            await self.handle_invite(request)
        elif request.method == 'BYE':
            await self.handle_bye(request)

    async def handle_invite(self, request):
        """Gestion des appels entrants OVH"""
        logging.info(f"Appel entrant depuis {request.from_header.uri}")
        
        # 1. Envoi 100 Trying (exigence OVH)
        await self.send_response(request, 100)
        
        # 2. Envoi 180 Ringing
        await self.send_response(request, 180)
        
        # 3. Préparation réponse 200 OK avec SDP
        contact_uri = URI(
            user=SIP_CONFIG['user'],
            host=SIP_CONFIG['local_ip'],
            port=SIP_CONFIG['port']
        )
        
        sdp_body = self.generate_sdp()
        await self.send_response(request, 200, contact=contact_uri, body=sdp_body)

    async def send_response(self, request, code, contact=None, body=None):
        """Envoi de réponse SIP conforme à OVH"""
        response = Response(
            status_code=code,
            method=request.method,
            from_header=request.from_header,
            to_header=request.to_header,
            call_id=request.call_id,
            cseq=request.cseq,
            via=Via(host=SIP_CONFIG['local_ip'], port=SIP_CONFIG['port']),
            contact=contact,
            content_type='application/sdp' if body else None,
            body=body
        )
        await self.client.send_response(response)

    def generate_sdp(self):
        """Génération SDP pour OVH (format spécifique)"""
        return f"""v=0
o=- 0 0 IN IP4 {SIP_CONFIG['local_ip']}
s=OVH-SIP
c=IN IP4 {SIP_CONFIG['local_ip']}
t=0 0
m=audio 10000 RTP/AVP 0
a=rtpmap:0 PCMU/8000
"""

    async def register(self):
        """Enregistrement périodique chez OVH"""
        while True:
            try:
                await self.client.register()
                logging.info("Enregistrement OVH réussi")
                await asyncio.sleep(300)  # Refresh toutes 5min
            except Exception as e:
                logging.error(f"Échec enregistrement: {e}")
                await asyncio.sleep(30)

async def main():
    handler = OVHSipHandler()
    await asyncio.gather(
        handler.client.listen(),
        handler.register()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Arrêt propre du service")
        sys.exit(0)