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

# ─── Configuration SIP & média ───────────────────────────────────────────
SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))

PUBLIC_HOST  = os.getenv("PUBLIC_HOST")           # IP publique ou FQDN
RTP_PORT     = int(os.getenv("RTP_PORT", 10000))  # port choisi pour RTP

# ─── Calcul du Digest MD5 pour REGISTER ──────────────────────────────────
def make_digest_response(challenge: dict) -> str:
    realm = challenge["realm"]
    nonce = challenge["nonce"]
    uri   = f"sip:{SIP_SERVER}"
    ha1 = hashlib.md5(f"{SIP_USERNAME}:{realm}:{SIP_PASSWORD}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
    return hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

# ─── Protocole RTP minimal (comfort noise) ───────────────────────────────
class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, remote_media_addr):
        self.remote_media_addr = remote_media_addr
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print(f"🎧 RTP socket prêt, envoi vers {self.remote_media_addr}")

    def datagram_received(self, data, addr):
        # Ici on pourrait traiter le flux entrant (ASR, caching, etc.)
        pass

    async def send_silence(self):
        # Comfort noise RFC 3389
        silence_frame = b'\xF8\xFF\xFE'
        while True:
            self.transport.sendto(silence_frame, self.remote_media_addr)
            await asyncio.sleep(0.02)  # toutes les 20 ms

# ─── Protocole SIP (REGISTER, INVITE, ACK, SDP) ──────────────────────────
class SIPProtocol(asyncio.DatagramProtocol):
    def __init__(self, registrar_addr):
        self.registrar_addr   = registrar_addr
        self.transport        = None
        self.challenge        = None
        self.registered       = False
        self.remote_media_addr = None
        self.rtp_transport    = None
        self.rtp_protocol     = None

    def connection_made(self, transport):
        self.transport = transport
        print(f"🚀 SIP listener démarré sur 0.0.0.0:{SIP_PORT}")
        # REGISTER initial
        asyncio.create_task(self._do_register())

    def datagram_received(self, data, addr):
        msg        = data.decode(errors="ignore")
        first_line = msg.split("\r\n", 1)[0]

        # ── Challenge Digest 401 Unauthorized ─────────────────────────────
        if first_line.startswith("SIP/2.0 401"):
            m = re.search(r'WWW-Authenticate:\s*Digest\s+([^\r\n]+)', msg, re.IGNORECASE)
            if m:
                params = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
                self.challenge = params
                print(f"🔐 Challenge reçu (realm={params['realm']}, nonce={params['nonce']})")
                asyncio.create_task(self._do_register(challenge=params))
            return

        # ── REGISTER accepté ────────────────────────────────────────────────
        if first_line.startswith("SIP/2.0 200") and "CSeq: 1 REGISTER" in msg:
            print("✅ REGISTER accepté")
            if not self.registered:
                self.registered = True
                asyncio.create_task(self._periodic_refresh())
            return

        # ── ACK reçu → session SIP établie ─────────────────────────────────
        if first_line.startswith("ACK"):
            print(f"🔗 Session SIP établie avec {addr}")
            # Dès l'ACK, on lance le média si pas déjà fait
            asyncio.create_task(self._start_media())
            return

        # ── INVITE entrant → répondre 200 OK + SDP ──────────────────────────
        if first_line.startswith("INVITE"):
            print(f"📞 Appel entrant reçu de {addr}")

            # Split headers / body pour parser SDP
            hdr, body = msg.split("\r\n\r\n", 1)
            lines     = body.splitlines()
            # extraire IP & port média
            c_line = next(l for l in lines if l.startswith("c=IN"))
            m_line = next(l for l in lines if l.startswith("m=audio"))
            remote_ip   = c_line.split()[-1]
            remote_port = int(m_line.split()[1])
            self.remote_media_addr = (remote_ip, remote_port)

            # récupérer et conserver les en-têtes SIP
            hdr_lines = hdr.split("\r\n")
            vias   = [l for l in hdr_lines if l.startswith("Via:")]
            from_h = next(l for l in hdr_lines if l.startswith("From:"))
            to_h   = next(l for l in hdr_lines if l.startswith("To:"))
            callid = next(l for l in hdr_lines if l.startswith("Call-ID:"))
            cseq   = next(l for l in hdr_lines if l.startswith("CSeq:"))

            # générer un tag pour To
            my_tag  = uuid.uuid4().hex[:8]
            to_resp = f"{to_h};tag={my_tag}"

            # préparer le SDP de réponse
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

            # construire et envoyer le 200 OK complet
            response_hdrs = [
                "SIP/2.0 200 OK",
                *vias,
                from_h,
                to_resp,
                callid,
                cseq,
                f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>",
                "Content-Type: application/sdp",
                f"Content-Length: {len(sdp_body)}",
                ""
            ]
            resp = "\r\n".join(response_hdrs) + sdp_body
            self.transport.sendto(resp.encode(), addr)
            print(f"✔️ 200 OK + SDP envoyé à {addr}")
            return

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

        self.transport.sendto(register, self.registrar_addr)
        print(f"🔄 REGISTER envoyé{' (auth)' if challenge else ''}")

    async def _periodic_refresh(self):
        while True:
            await asyncio.sleep(300)
            asyncio.create_task(self._do_register(challenge=self.challenge))

    async def _start_media(self):
        # bind RTP socket qu'une seule fois
        if self.rtp_transport is not None:
            print("ℹ️ RTP handler déjà démarré, réutilisation du socket")
            return

        loop = asyncio.get_running_loop()
        try:
            self.rtp_transport, self.rtp_protocol = await loop.create_datagram_endpoint(
                lambda: RTPProtocol(self.remote_media_addr),
                local_addr=('0.0.0.0', RTP_PORT)
            )
            asyncio.create_task(self.rtp_protocol.send_silence())
            print(f"✅ RTP handler démarré, silence envoyé sur {RTP_PORT}")
        except OSError as e:
            print(f"❌ Impossible de binder le socket RTP : {e}")

# ─── Point d’entrée pour FastAPI (startup handler) ───────────────────────
async def start_sip_server():
    loop = asyncio.get_running_loop()
    # résolution DNS du registrar SIP
    infos = socket.getaddrinfo(SIP_SERVER, SIP_PORT,
                               family=socket.AF_UNSPEC,
                               type=socket.SOCK_DGRAM)
    registrar_addr = infos[0][4]  # (ip, port)

    protocol = SIPProtocol(registrar_addr)
    await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=('0.0.0.0', SIP_PORT)
    )

    # bloque la coroutine pour garder le serveur up
    await asyncio.Event().wait()
