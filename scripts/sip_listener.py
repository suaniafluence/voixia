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

# ─── Config SIP & Média ────────────────────────────────────────────────
SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))

PUBLIC_HOST  = os.getenv("PUBLIC_HOST")           # IP publique ou FQDN
RTP_PORT     = int(os.getenv("RTP_PORT", 10000))  # port RTP local

# ─── Digest MD5 pour REGISTER ────────────────────────────────────────────
def make_digest_response(challenge: dict) -> str:
    realm, nonce = challenge["realm"], challenge["nonce"]
    uri = f"sip:{SIP_SERVER}"
    ha1 = hashlib.md5(f"{SIP_USERNAME}:{realm}:{SIP_PASSWORD}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
    return hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

# ─── Protocole RTP (amélioré pour multi-appels) ──────────────────────────
class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, remote_media_addr):
        self.remote_media_addr = remote_media_addr
        self.transport = None
        self.seq = 0
        self.timestamp = 0
        self.ssrc = uuid.uuid4().int & 0xFFFFFFFF
        self.is_active = True  # NEW: Contrôle d'état

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        pass  # Toujours utile pour keep-alive NAT

    def build_rtp_packet(self, payload: bytes) -> bytes:
        header = bytearray(12 + len(payload))
        header[0] = 0x80
        header[1] = 0x00
        self.seq = (self.seq + 1) & 0xFFFF
        self.timestamp = (self.timestamp + len(payload)) & 0xFFFFFFFF
        header[2:4]  = self.seq.to_bytes(2, 'big')
        header[4:8]  = self.timestamp.to_bytes(4, 'big')
        header[8:12] = self.ssrc.to_bytes(4, 'big')
        header[12:]  = payload
        return bytes(header)

    async def send_silence(self):
        silence = bytes([0x7F]) * 160  # NEW: 0x7F pour mu-law signé
        while self.is_active:  # NEW: Condition de sortie
            pkt = self.build_rtp_packet(silence)
            try:
                self.transport.sendto(pkt, self.remote_media_addr)
                await asyncio.sleep(0.02)
            except:
                break

# ─── Protocole SIP (avec gestion multi-appels) ────────────────────────────
class SIPProtocol(asyncio.DatagramProtocol):
    def __init__(self, registrar_addr):
        self.registrar_addr    = registrar_addr
        self.transport         = None
        self.challenge         = None
        self.registered        = False
        self.active_calls      = {}  # NEW: Dictionnaire des appels par Call-ID
        self.call_id           = uuid.uuid4().hex  # NEW: Call-ID persistant
        self.cseq              = 0   # NEW: CSeq incrémental
        self.last_error = None  # NEW: Stockage dernière erreur
        self.rtp_ports = set() # NEW: Suivi des ports RTP actifs
        
        # NEW: Gestion des tâches pour nettoyage
        self.register_task     = None
        self.rtp_transports    = []

    def connection_made(self, transport):
        self.transport = transport
        print(f"🚀 SIP listener → 0.0.0.0:{SIP_PORT}")
        self.register_task = asyncio.create_task(self._do_register())

    def datagram_received(self, data, addr):
        msg = data.decode(errors="ignore")
        first_line = msg.split("\r\n",1)[0]

        # NEW: Extraction Call-ID pour routage
        call_id = next((l.split(":")[1].strip() for l in msg.splitlines() 
                      if l.startswith("Call-ID:")), None)
        
        # 1) Challenge 401 Unauthorized
        if first_line.startswith("SIP/2.0 401"):
            m = re.search(r'WWW-Authenticate:\s*Digest\s+([^\r\n]+)', msg, re.IGNORECASE)
            if m:
                params = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
                self.challenge = params
                asyncio.create_task(self._do_register(challenge=params))
            return

        # 2) REGISTER 200 OK
        if first_line.startswith("SIP/2.0 200") and "REGISTER" in msg:
            if not self.registered:
                self.registered = True
                # NEW: Extraction Expires du serveur
                expires = next((int(l.split(":")[1].strip()) 
                             for l in msg.splitlines() 
                             if l.startswith("Expires:")), 3600)
                asyncio.create_task(self._periodic_refresh(expires))
            return

        # 3) ACK → session établie
        if first_line.startswith("ACK") and call_id in self.active_calls:
            print(f"🔗 Session SIP établie pour {call_id}")
            asyncio.create_task(self._start_media(call_id))
            return

        # 4) INVITE entrant
        if first_line.startswith("INVITE"):
            try:
                # NEW: Gestion des erreurs SDP
                hdr, body = msg.split("\r\n\r\n",1)
                media_info = self._parse_sdp(body)
                
                # Stocker les infos de l'appel
                self.active_calls[call_id] = {
                    "state": "ringing",
                    "remote_sip": addr,
                    "media_addr": (media_info["ip"], media_info["port"]),
                    "rtp": None  # Rempli par _start_media
                }
                
                # Réponses SIP
                self.transport.sendto(self._build_response("100 Trying", call_id), addr)
                self.transport.sendto(self._build_response("180 Ringing", call_id), addr)
                asyncio.create_task(self._delayed_200_ok(call_id, hdr, body))
                
            except Exception as e:
                print(f"❌ Erreur SDP: {e}")
                self.transport.sendto(self._build_response("400 Bad Request", call_id), addr)
            return

    # NEW: Méthode de parsing SDP améliorée
    def _parse_sdp(self, body) -> dict:
        lines = body.splitlines()
        media_block = {"ip": None, "port": None}
        
        for line in lines:
            if line.startswith("m=audio"):
                media_block["port"] = int(line.split()[1])
            elif line.startswith("c=IN IP4"):
                media_block["ip"] = line.split()[-1]
            if media_block["ip"] and media_block["port"]:
                break
                
        if not media_block["ip"]:
            raise ValueError("Adresse IP média introuvable")
        return media_block

    # NEW: Construction générique de réponses
    def _build_response(self, status_line, call_id):
        return f"{status_line}\r\nCall-ID: {call_id}\r\nContent-Length: 0\r\n\r\n".encode()

    async def _delayed_200_ok(self, call_id, hdr, body):
        await asyncio.sleep(1)
        
        # Récupérer les infos de l'appel
        call = self.active_calls.get(call_id)
        if not call:
            return

        # Construire SDP
        sdp = "\r\n".join([
            "v=0",
            f"o=- {int(time.time())} {int(time.time())} IN IP4 {PUBLIC_HOST}",
            "s=VoixIA",
            f"c=IN IP4 {PUBLIC_HOST}",
            "t=0 0",
            f"m=audio {RTP_PORT} RTP/AVP 0",
            "a=rtpmap:0 PCMU/8000",
            ""
        ])

        # Envoyer 200 OK
        resp = [
            "SIP/2.0 200 OK",
            f"Call-ID: {call_id}",
            f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>",
            "Content-Type: application/sdp",
            f"Content-Length: {len(sdp)}",
            "",
            sdp
        ]
        self.transport.sendto("\r\n".join(resp).encode(), call["remote_sip"])

    async def _do_register(self, challenge=None):
        self.cseq += 1  # NEW: Incrément séquentiel
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
            f"Call-ID: {self.call_id}",  # NEW: Call-ID persistant
            f"CSeq: {self.cseq} REGISTER",  # NEW: CSeq incrémenté
            f"Contact: <sip:{SIP_USERNAME}@{PUBLIC_HOST}:{SIP_PORT}>",
            auth.rstrip(),
            "Expires: 3600",
            "Content-Length: 0",
            "", ""
        ])
        self.transport.sendto(reg.encode(), self.registrar_addr)

    # NEW: Rafraîchissement basé sur Expires serveur
    async def _periodic_refresh(self, expires):
        refresh_time = max(expires - 60, 60)  # 1mn avant expiration
        while True:
            await asyncio.sleep(refresh_time)
            await self._do_register(self.challenge)

    # NEW: Gestion RTP par appel
    async def _start_media(self, call_id):
        call = self.active_calls.get(call_id)
        if not call or call["rtp"]:
            return

        loop = asyncio.get_running_loop()
        try:
            # Créer un endpoint RTP dédié
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: RTPProtocol(call["media_addr"]),
                local_addr=('0.0.0.0', RTP_PORT)
            )
            call["rtp"] = {
                "transport": transport,
                "protocol": protocol,
                "task": asyncio.create_task(protocol.send_silence())
            }
            self.rtp_transports.append(transport)
            self.rtp_ports.add(RTP_PORT)
        except OSError as e:
            self.last_error = f"RTP error: {str(e)}"  # NEW: Log erreur

    # NEW: Nettoyage des ressources
    async def stop(self):
        # Arrêter les tâches REGISTER
        if self.register_task:
            self.register_task.cancel()
        
        # Fermer les transports RTP
        for transport in self.rtp_transports:
            transport.close()
        
        # Arrêter les générateurs de silence
        for call in self.active_calls.values():
            if call.get("rtp"):
                call["rtp"]["protocol"].is_active = False
                call["rtp"]["task"].cancel()
        self.rtp_ports.clear()  # NEW: Nettoyage ports

# ─── Intégration FastAPI ────────────────────────────────────────────────
async def start_sip_server(registrar_addr=None):
    loop = asyncio.get_running_loop()
    protocol = SIPProtocol(registrar_addr)
    await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=('0.0.0.0', SIP_PORT)
    )
    return protocol  # NEW: Retourne l'instance pour shutdown

async def stop_sip_server(protocol):
    await protocol.stop()