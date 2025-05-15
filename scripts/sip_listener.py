import os
import asyncio
import socket
import uuid
import time
import hashlib
import re
from dotenv import load_dotenv

load_dotenv()

# ─── Config SIP & média ─────────────────────────────────────────────────
SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))

PUBLIC_HOST  = os.getenv("PUBLIC_HOST")           # IP publique / FQDN
RTP_PORT     = int(os.getenv("RTP_PORT", 10000))  # port RTP local

# ─── Digest MD5 pour REGISTER ────────────────────────────────────────────
def make_digest_response(challenge: dict) -> str:
    realm, nonce = challenge["realm"], challenge["nonce"]
    uri = f"sip:{SIP_SERVER}"
    ha1 = hashlib.md5(f"{SIP_USERNAME}:{realm}:{SIP_PASSWORD}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
    return hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

# ─── Protocole RTP : header + payload mu-law silence ──────────────────────
class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, remote_media_addr):
        self.remote_media_addr = remote_media_addr
        self.transport = None
        self.seq = 0
        self.timestamp = 0
        self.ssrc = uuid.uuid4().int & 0xFFFFFFFF

    def connection_made(self, transport):
        self.transport = transport
        print(f"🎧 RTP socket prêt, envoi vers {self.remote_media_addr}")

    def datagram_received(self, data, addr):
        msg        = data.decode(errors="ignore")
        first_line = msg.split("\r\n", 1)[0]

        # … 401, REGISTER, ACK …

        if first_line.startswith("INVITE"):
            print(f"📞 Appel entrant reçu de {addr}")

            # 1️⃣ 100 Trying
            trying = "SIP/2.0 100 Trying\r\nContent-Length: 0\r\n\r\n"
            self.transport.sendto(trying.encode(), addr)

            # 2️⃣ 180 Ringing
            ringing = "SIP/2.0 180 Ringing\r\nContent-Length: 0\r\n\r\n"
            self.transport.sendto(ringing.encode(), addr)
            print("⏳ Envoi d'un 180 Ringing")

            # Scinder headers et SDP du body pour la 200 OK plus tard
            hdr, body = msg.split("\r\n\r\n", 1)

            # Lance l’envoi du 200 OK + SDP en tâche différée
            asyncio.create_task(self._delayed_200_ok(addr, hdr, body))
            return

    async def _delayed_200_ok(self, addr, hdr, body):
        # Laisse sonner un peu
        await asyncio.sleep(1)

        # → parser hdr/body, extraire c=, m=… comme avant
        # → construire sdp_body (identique à ton code précédent)
        # → assembler response_hdrs avec To-tag, Contact, Content-Type, etc.
        packet = ...  # ton 200 OK + SDP complet

        self.transport.sendto(packet.encode(), addr)
        print(f"✔️ 200 OK + SDP envoyé à {addr}")


    def build_rtp_packet(self, payload: bytes) -> bytes:
        # Version=2, P=0, X=0, CC=0, M=0, PT=0 (PCMU)
        header0 = 2 << 6
        header1 = 0 & 0x7F
        b0 = header0 | header1
        b1 = 0  # marker=0, payload type=0
        self.seq = (self.seq + 1) & 0xFFFF
        self.timestamp = (self.timestamp + len(payload)) & 0xFFFFFFFF
        pkt = bytearray(12 + len(payload))
        pkt[0]  = b0
        pkt[1]  = b1
        pkt[2:4]  = self.seq.to_bytes(2, 'big')
        pkt[4:8]  = self.timestamp.to_bytes(4, 'big')
        pkt[8:12] = self.ssrc.to_bytes(4, 'big')
        pkt[12:]  = payload
        return bytes(pkt)

    async def send_silence(self):
        # silence mu-law = 0xFF repeated for 160 samples (20ms @8000Hz)
        silence_frame = bytes([0xFF]) * 160
        while True:
            pkt = self.build_rtp_packet(silence_frame)
            self.transport.sendto(pkt, self.remote_media_addr)
            await asyncio.sleep(0.02)  # 20 ms

# ─── Protocole SIP (REGISTER, INVITE, ACK, 200+SDP) ───────────────────────
class SIPProtocol(asyncio.DatagramProtocol):
    def __init__(self, registrar_addr):
        self.registrar_addr    = registrar_addr
        self.transport         = None
        self.challenge         = None
        self.registered        = False
        self.remote_media_addr = None
        self.rtp_transport     = None
        self.rtp_protocol      = None

    def connection_made(self, transport):
        self.transport = transport
        print(f"🚀 SIP listener sur 0.0.0.0:{SIP_PORT}")
        asyncio.create_task(self._do_register())

    def datagram_received(self, data, addr):
        msg        = data.decode(errors="ignore")
        first_line = msg.split("\r\n",1)[0]

        # 401 Digest challenge
        if first_line.startswith("SIP/2.0 401"):
            m = re.search(r'WWW-Authenticate:\s*Digest\s+([^\r\n]+)', msg, re.IGNORECASE)
            if m:
                params = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
                self.challenge = params
                print(f"🔐 Challenge: realm={params['realm']} nonce={params['nonce']}")
                asyncio.create_task(self._do_register(challenge=params))
            return

        # REGISTER OK
        if first_line.startswith("SIP/2.0 200") and "CSeq: 1 REGISTER" in msg:
            print("✅ REGISTER accepté")
            if not self.registered:
                self.registered = True
                asyncio.create_task(self._periodic_refresh())
            return

        # ACK → session établie
        if first_line.startswith("ACK"):
            print(f"🔗 Session SIP établie avec {addr}")
            asyncio.create_task(self._start_media())
            return

        # INVITE entrant → parse SDP + répondre 200 OK
        if first_line.startswith("INVITE"):
            print(f"📞 INVITE reçu de {addr}")
            hdr, body = msg.split("\r\n\r\n",1)
            lines = body.splitlines()
            c_line = next(l for l in lines if l.startswith("c=IN"))
            m_line = next(l for l in lines if l.startswith("m=audio"))
            rip = c_line.split()[-1]
            rport = int(m_line.split()[1])
            self.remote_media_addr = (rip, rport)

            hdrs = hdr.split("\r\n")
            vias   = [l for l in hdrs if l.startswith("Via:")]
            frm    = next(l for l in hdrs if l.startswith("From:"))
            to     = next(l for l in hdrs if l.startswith("To:"))
            callid = next(l for l in hdrs if l.startswith("Call-ID:"))
            cseq   = next(l for l in hdrs if l.startswith("CSeq:"))

            tag = uuid.uuid4().hex[:8]
            to_tag = f"{to};tag={tag}"

            sdp = "\r\n".join([
                "v=0",
                f"o=- {int(time.time())} {int(time.time())} IN IP4 {PUBLIC_HOST}",
                "s=VoixIA",
                f"c=IN IP4 {PUBLIC_HOST}",
                "t=0 0",
                f"m=audio {RTP_PORT} RTP/AVP 0 8 96",
                "a=rtpmap:0 PCMU/8000",
                "a=rtpmap:8 PCMA/8000",
                "a=rtpmap:96 opus/48000/2",
                ""
            ])
            resp_hdrs = [
                "SIP/2.0 200 OK",
                *vias,
                frm,
                to_tag,
                callid,
                cseq,
                f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>",
                "Content-Type: application/sdp",
                f"Content-Length: {len(sdp)}",
                ""
            ]
            packet = "\r\n".join(resp_hdrs) + sdp
            self.transport.sendto(packet.encode(), addr)
            print(f"✔️ 200 OK+SDP → {addr}")
            return

    async def _do_register(self, challenge=None):
        cid = str(uuid.uuid4())
        branch = "z9hG4bK" + uuid.uuid4().hex
        tag = uuid.uuid4().hex[:8]

        auth = ""
        if challenge:
            resp = make_digest_response(challenge)
            auth = (
                f'Authorization: Digest username="{SIP_USERNAME}", '
                f'realm="{challenge["realm"]}", '
                f'nonce="{challenge["nonce"]}", '
                f'uri="sip:{SIP_SERVER}", '
                f'response="{resp}", algorithm=MD5\r\n'
            )

        reg = "\r\n".join([
            f"REGISTER sip:{SIP_SERVER} SIP/2.0",
            f"Via: SIP/2.0/UDP 0.0.0.0;branch={branch}",
            "Max-Forwards: 70",
            f"To: <sip:{SIP_USERNAME}@{SIP_SERVER}>",
            f"From: <sip:{SIP_USERNAME}@{SIP_SERVER}>;tag={tag}",
            f"Call-ID: {cid}",
            "CSeq: 1 REGISTER",
            f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>",
            auth.rstrip(),
            "Expires: 3600",
            "Content-Length: 0",
            "", ""
        ]) + ""
        self.transport.sendto(reg.encode(), self.registrar_addr)
        print(f"🔄 REGISTER {'(auth)' if challenge else ''}")

    async def _periodic_refresh(self):
        while True:
            await asyncio.sleep(300)
            asyncio.create_task(self._do_register(self.challenge))

    async def _start_media(self):
        if self.rtp_transport:
            return
        loop = asyncio.get_running_loop()
        try:
            self.rtp_transport, self.rtp_protocol = await loop.create_datagram_endpoint(
                lambda: RTPProtocol(self.remote_media_addr),
                local_addr=('0.0.0.0', RTP_PORT)
            )
            asyncio.create_task(self.rtp_protocol.send_silence())
            print(f"✅ RTP handler démarré, silence sur {RTP_PORT}")
        except OSError as e:
            print(f"❌ Impossible de binder RTP : {e}")

# ─── Entrypoint (startup FastAPI) ─────────────────────────────────────────
async def start_sip_server():
    loop = asyncio.get_running_loop()
    infos = socket.getaddrinfo(SIP_SERVER, SIP_PORT,
                               family=socket.AF_UNSPEC,
                               type=socket.SOCK_DGRAM)
    registrar_addr = infos[0][4]
    protocol = SIPProtocol(registrar_addr)
    await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=('0.0.0.0', SIP_PORT)
    )
    await asyncio.Event().wait()
