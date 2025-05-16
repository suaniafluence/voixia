# scripts/sip_listener.py
import os
import asyncio
import logging
from dotenv import load_dotenv
import aiosip
from aiosip.auth import Auth

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO)

class OVHSipServer:
    def __init__(self):
        self.config = {
            'user': os.getenv('OVH_SIP_USER'),
            'password': os.getenv('OVH_SIP_PASSWORD'),
            'server': os.getenv('OVH_SIP_SERVER', 'sbc6.fr.sip.ovh'),
            'local_ip': os.getenv('PUBLIC_HOST', '0.0.0.0'),
            'sip_port': int(os.getenv('SIP_PORT', 5060)),
            'rtp_port': int(os.getenv('RTP_PORT', 10000))
        }

        self.app = aiosip.Application()
        self.transport = aiosip.UDPTransport(
            self.app,
            local_addr=(self.config['local_ip'], self.config['sip_port'])
        )

        self.auth = Auth(
            username=self.config['user'],
            password=self.config['password'],
            realm=self.config['server']
        )

    async def register_ovh(self):
        """Enregistrement périodique chez OVH"""
        while True:
            try:
                await self.app.register(
                    from_header=aiosip.Contact.from_string(
                        f'sip:{self.config["user"]}@{self.config["server"]}'
                    ),
                    to_header=aiosip.Contact.from_string(
                        f'sip:{self.config["user"]}@{self.config["server"]}'
                    ),
                    contact_header=aiosip.Contact.from_string(
                        f'sip:{self.config["user"]}@{self.config["local_ip"]}:{self.config["sip_port"]}'
                    ),
                    expires=300,
                    auth=self.auth
                )
                logging.info("✅ Enregistrement OVH réussi")
                await asyncio.sleep(250)  # Rafraîchir avant expiration
            except Exception as e:
                logging.error(f"❌ Échec enregistrement: {e}")
                await asyncio.sleep(30)

    async def handle_invite(self, request, message):
        """Gestion des appels entrants OVH"""
        logging.info(f"📞 Appel entrant depuis {message.headers['From']}")

        # 1. Envoyer 100 Trying (requis par OVH)
        await request.reply(100, 'Trying')

        # 2. Envoyer 180 Ringing
        await request.reply(180, 'Ringing')

        # 3. Préparer la réponse 200 OK avec SDP
        sdp_body = self.generate_sdp()
        await request.reply(
            200,
            'OK',
            headers={
                'Contact': f'<sip:{self.config["user"]}@{self.config["local_ip"]}:{self.config["sip_port"]}>',
                'Content-Type': 'application/sdp'
            },
            content=sdp_body.encode()
        )

    def generate_sdp(self):
        """Génération SDP compatible OVH"""
        return f"""v=0
o=- 0 0 IN IP4 {self.config['local_ip']}
s=OVH-SIP
c=IN IP4 {self.config['local_ip']}
t=0 0
m=audio {self.config['rtp_port']} RTP/AVP 0
a=rtpmap:0 PCMU/8000
"""

    async def run(self):
        # Enregistrer les handlers
        self.app.dialplan.add_user('INVITE', self.handle_invite)

        # Démarrer le transport
        await self.transport.start()

        # Lancer l'enregistrement périodique
        await self.register_ovh()

async def main():
    server = OVHSipServer()
    await server.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Arrêt propre du serveur SIP")