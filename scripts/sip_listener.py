# scripts/sip_listener.py

import os
import asyncio
import socket
import uuid
import hashlib
import re
from dotenv import load_dotenv

load_dotenv()

SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))
CONTACT_URI  = f"sip:{SIP_USERNAME}@{SIP_SERVER}"

def make_digest_response(challenge: dict) -> str:
    """
    Calcule la réponse Digest MD5 selon RFC2617
    """
    realm = challenge["realm"]
    nonce = challenge["nonce"]
    uri   = f"sip:{SIP_SERVER}"

    ha1 = hashlib.md5(f"{SIP_USERNAME}:{realm}:{SIP_PASSWORD}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
    resp = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    return resp

class SIPProtocol(asyncio.DatagramProtocol):
    def __init__(self, remote_addr):
        self.remote_addr = remote_addr
        self.transport = None
        self.challenge = None
        self.registered = False
    # …
    def connection_made(self, transport):
        self.transport = transport
        print(f"🚀 SIP listener démarré sur 0.0.0.0:{SIP_PORT}")
        # Envoi du REGISTER initial (sans auth)
        asyncio.create_task(self._do_register())

    def datagram_received(self, data, addr):
        msg = data.decode(errors="ignore")
        first_line = msg.split("\r\n", 1)[0]

        # 1) Challenge 401 Unauthorized
        if first_line.startswith("SIP/2.0 401"):
            m = re.search(r'WWW-Authenticate:\s*Digest\s+([^\r\n]+)', msg, re.IGNORECASE)
            if m:
                params = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
                self.challenge = params
                print(f"🔐 Challenge reçu (realm={params.get('realm')}, nonce={params.get('nonce')})")
                asyncio.create_task(self._do_register(challenge=params))
            return

        # 2) 200 OK pour REGISTER
        if first_line.startswith("SIP/2.0 200") and "CSeq: 1 REGISTER" in msg:
            print("✅ REGISTER accepté")
            if not self.registered:
                self.registered = True
                # Lancement du rafraîchissement périodique
                asyncio.create_task(self._periodic_refresh())
            return

        # 3) INVITE entrant
        if first_line.startswith("INVITE"):
            print(f"📞 Appel entrant reçu de {addr}")
            # 180 Ringing
            ringing = (
                "SIP/2.0 180 Ringing\r\n"
                f"Via: SIP/2.0/UDP {addr[0]}:{addr[1]}\r\n"
                "Content-Length: 0\r\n\r\n"
            ).encode()
            self.transport.sendto(ringing, addr)
            # 200 OK un peu plus tard
            asyncio.create_task(self._respond_ok(addr))
            return

    async def _respond_ok(self, addr):
        await asyncio.sleep(1)
        ok = (
            "SIP/2.0 200 OK\r\n"
            f"Via: SIP/2.0/UDP {addr[0]}:{addr[1]}\r\n"
            "Content-Length: 0\r\n\r\n"
        ).encode()
        self.transport.sendto(ok, addr)
        print(f"✔️ INVITE répondu 200 OK à {addr}")

    async def _do_register(self, challenge: dict = None):
        """
        Envoie un REGISTER, avec ou sans Authorization selon challenge.
        """
        call_id = str(uuid.uuid4())
        branch  = "z9hG4bK" + uuid.uuid4().hex
        tag     = uuid.uuid4().hex[:8]
        cseq    = 1

        auth_hdr = ""
        if challenge:
            response = make_digest_response(challenge)
            auth_hdr = (
                f'Authorization: Digest username="{SIP_USERNAME}", '
                f'realm="{challenge["realm"]}", '
                f'nonce="{challenge["nonce"]}", '
                f'uri="sip:{SIP_SERVER}", '
                f'response="{response}", algorithm=MD5\r\n'
            )

        register = (
            f"REGISTER sip:{SIP_SERVER} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP 0.0.0.0;branch={branch}\r\n"
            f"Max-Forwards: 70\r\n"
            f"To: <sip:{SIP_USERNAME}@{SIP_SERVER}>\r\n"
            f"From: <sip:{SIP_USERNAME}@{SIP_SERVER}>;tag={tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} REGISTER\r\n"
            f"Contact: <{CONTACT_URI}:5060>\r\n"
            + auth_hdr +
            f"Expires: 3600\r\n"
            f"Content-Length: 0\r\n\r\n"
        ).encode()
        self.transport.sendto(register, self.remote_addr)
        print(f"🔄 REGISTER envoyé{' (auth)' if challenge else ''}")

    async def _periodic_refresh(self):
        """
        Toutes les 5 minutes, renvoie le REGISTER (authentifié si possible).
        """
        while True:
            await asyncio.sleep(300)
            asyncio.create_task(self._do_register(challenge=self.challenge))

async def start_sip_server():
    loop = asyncio.get_running_loop()

    # ─── Résolution DNS préalable ───────────────────────────────
    infos = socket.getaddrinfo(SIP_SERVER, SIP_PORT,
                               family=socket.AF_UNSPEC,
                               type=socket.SOCK_DGRAM)
    # on prend la première adresse utilisable
    remote_addr = infos[0][4]  # ex. ("93.184.216.34", 5060)

    # 1) Démarre le listener UDP en injectant remote_addr dans le protocole
    protocol = SIPProtocol(remote_addr)
    await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=('0.0.0.0', SIP_PORT)
    )
    # …