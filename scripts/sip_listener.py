# scripts/sip_listener.py

import os
import asyncio
import socket
import uuid
import time
import hashlib
import re
from dotenv import load_dotenv

load_dotenv()

SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))
PUBLIC_HOST  = os.getenv("PUBLIC_HOST")         # IP publique ou FQDN
RTP_PORT     = int(os.getenv("RTP_PORT", 10000))  # port choisi pour RTP

def make_digest_response(challenge: dict) -> str:
    realm = challenge["realm"]
    nonce = challenge["nonce"]
    uri   = f"sip:{SIP_SERVER}"
    ha1 = hashlib.md5(f"{SIP_USERNAME}:{realm}:{SIP_PASSWORD}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
    return hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, remote_addr):
        self.remote_addr = remote_addr  # où envoyer le media
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # data = paquet RTP reçu depuis OVH (PCM mu-law)
        # ici tu pourrais l’asservir à ton ASR, ou juste ignorer
        pass

    async def send_silence(self):
        # Exemple : envoyer des paquets silence pour retenir l’appel
        silence_frame = b'\xF8\xFF\xFE'  # comfort noise NTP silence (RFC 3389)
        while True:
            self.transport.sendto(silence_frame, self.remote_addr)
            await asyncio.sleep(0.02)  # 20 ms

class SIPProtocol(asyncio.DatagramProtocol):
    def __init__(self, remote_addr):
        self.remote_addr = remote_addr
        self.transport   = None
        self.challenge   = None
        self.registered  = False

    def connection_made(self, transport):
        self.transport = transport
        print(f"🚀 SIP listener démarré sur 0.0.0.0:{SIP_PORT}")
        asyncio.create_task(self._do_register())

    def datagram_received(self, data, addr):
        msg        = data.decode(errors="ignore")
        first_line = msg.split("\r\n", 1)[0]

        # 401 Unauthorized → challenge Digest
        if first_line.startswith("SIP/2.0 401"):
            m = re.search(r'WWW-Authenticate:\s*Digest\s+([^\r\n]+)', msg, re.IGNORECASE)
            if m:
                params = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
                self.challenge = params
                print(f"🔐 Challenge reçu (realm={params['realm']}, nonce={params['nonce']})")
                asyncio.create_task(self._do_register(challenge=params))
            return

        # 200 OK au REGISTER
        if first_line.startswith("SIP/2.0 200") and "CSeq: 1 REGISTER" in msg:
            print("✅ REGISTER accepté")
            if not self.registered:
                self.registered = True
                asyncio.create_task(self._periodic_refresh())
            return

        # ACK reçu → session établie
        if first_line.startswith("ACK"):
            print(f"🔗 Session établie avec {addr}")
            # Démarre le media handler
            asyncio.create_task(self._start_media())
            return
    
        # INVITE entrant → répondre 200 OK avec SDP
        if first_line.startswith("INVITE"):
            print(f"📞 Appel entrant reçu de {addr}")

            # parser la requête
            lines = msg.split("\r\n")
            vias   = [l for l in lines if l.startswith("Via:")]
            from_h = next(l for l in lines if l.startswith("From:"))
            to_h   = next(l for l in lines if l.startswith("To:"))
            callid = next(l for l in lines if l.startswith("Call-ID:"))
            cseq   = next(l for l in lines if l.startswith("CSeq:"))

            # générer un tag pour To:
            my_tag  = uuid.uuid4().hex[:8]
            to_resp = f"{to_h};tag={my_tag}"

            # construire le SDP
            sdp_body = (
                "v=0\r\n"
                f"o=- {int(time.time())} {int(time.time())} IN IP4 {PUBLIC_HOST}\r\n"
                "s=VoixIA\r\n"
                f"c=IN IP4 {PUBLIC_HOST}\r\n"
                "t=0 0\r\n"
                f"m=audio {RTP_PORT} RTP/AVP 0 8 96\r\n"
                "a=rtpmap:0 PCMU/8000\r\n"
                "a=rtpmap:8 PCMA/8000\r\n"
                "a=rtpmap:96 opus/48000/2\r\n"
            )

            # assembler la réponse
            headers = [
                "SIP/2.0 200 OK",
                *vias,
                from_h,
                to_resp,
                callid,
                cseq,
                f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>",
                "Content-Type: application/sdp",
                f"Content-Length: {len(sdp_body)}",
                "",
            ]
            resp = "\r\n".join(headers) + sdp_body
            self.transport.sendto(resp.encode(), addr)
            print(f"✔️ 200 OK + SDP envoyé à {addr}")
            return
        
    async def _start_media(self):
        """
        - Ouvre un socket RTP en UDP sur RTP_PORT
        - Lit ce que renvoie ton pipeline IA (audio PCM)
        - Emballe en paquets RTP et envoie à self.remote_addr_media
        - (Optionnel) recoit le flux audio et le traite
        """
        loop = asyncio.get_running_loop()
        # bind sur le port RTP pour recevoir (et envoyer) le média
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: RTPProtocol(self.remote_addr),  
            local_addr=(PUBLIC_HOST, RTP_PORT)
        )
        # maintien de l’appel en envoyant du silence
        asyncio.create_task(protocol.send_silence())
        print(f"🎧 RTP handler démarré sur {PUBLIC_HOST}:{RTP_PORT}")

    async def _do_register(self, challenge: dict = None):
        call_id = str(uuid.uuid4())
        branch  = "z9hG4bK" + uuid.uuid4().hex
        tag     = uuid.uuid4().hex[:8]
        cseq    = 1

        auth_hdr = ""
        if challenge:
            resp = make_digest_response(challenge)
            auth_hdr = (
                f'Authorization: Digest username="{SIP_USERNAME}", '
                f'realm="{challenge["realm"]}", '
                f'nonce="{challenge["nonce"]}", '
                f'uri="sip:{SIP_SERVER}", '
                f'response="{resp}", algorithm=MD5\r\n'
            )

        register = (
            f"REGISTER sip:{SIP_SERVER} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP 0.0.0.0;branch={branch}\r\n"
            f"Max-Forwards: 70\r\n"
            f"To: <sip:{SIP_USERNAME}@{SIP_SERVER}>\r\n"
            f"From: <sip:{SIP_USERNAME}@{SIP_SERVER}>;tag={tag}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq} REGISTER\r\n"
            f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>\r\n"
            + auth_hdr +
            f"Expires: 3600\r\n"
            f"Content-Length: 0\r\n\r\n"
        ).encode()

        self.transport.sendto(register, self.remote_addr)
        print(f"🔄 REGISTER envoyé{' (auth)' if challenge else ''}")

    async def _periodic_refresh(self):
        while True:
            await asyncio.sleep(300)
            asyncio.create_task(self._do_register(challenge=self.challenge))


async def start_sip_server():
    loop = asyncio.get_running_loop()

    # résoudre l’adresse du registrar
    infos = socket.getaddrinfo(SIP_SERVER, SIP_PORT,
                               family=socket.AF_UNSPEC,
                               type=socket.SOCK_DGRAM)
    remote_addr = infos[0][4]  # (ip, port)

    # démarrer le listener UDP
    protocol = SIPProtocol(remote_addr)
    await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=('0.0.0.0', SIP_PORT)
    )

    # bloquer pour que le serveur reste vivant
    await asyncio.Event().wait()
