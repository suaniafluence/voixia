# scripts/sip_listener.py

import os
import asyncio
import socket
import uuid
from dotenv import load_dotenv

load_dotenv()

SIP_USERNAME = os.getenv("SIP_USERNAME")
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")
SIP_SERVER   = os.getenv("SIP_SERVER")
SIP_PORT     = int(os.getenv("SIP_PORT", 5060))
CONTACT_URI  = f"sip:{SIP_USERNAME}@{SIP_SERVER}"

def make_register():
    call_id = str(uuid.uuid4())
    branch  = "z9hG4bK" + uuid.uuid4().hex
    tag     = uuid.uuid4().hex[:8]
    cseq    = 1

    return (
        f"REGISTER sip:{SIP_SERVER} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP 0.0.0.0;branch={branch}\r\n"
        f"Max-Forwards: 70\r\n"
        f"To: <sip:{SIP_USERNAME}@{SIP_SERVER}>\r\n"
        f"From: <sip:{SIP_USERNAME}@{SIP_SERVER}>;tag={tag}\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: {cseq} REGISTER\r\n"
        f"Contact: <{CONTACT_URI}:5060>\r\n"
        f"Expires: 3600\r\n"
        f"Content-Length: 0\r\n\r\n"
    ).encode()

async def sip_register_loop():
    """Send REGISTER every 5 minutes to keep alive."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    while True:
        pkt = make_register()
        sock.sendto(pkt, (SIP_SERVER, SIP_PORT))
        print("🔄 REGISTER envoyé")
        await asyncio.sleep(300)

class SIPProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        print(f"🚀 SIP listener démarré sur 0.0.0.0:{SIP_PORT}")

    def datagram_received(self, data, addr):
        msg = data.decode(errors="ignore")
        print(f"📨 Reçu de {addr}:\n{msg.strip()}\n")
        if msg.startswith("INVITE"):
            # 180 Ringing
            ringing = (
                "SIP/2.0 180 Ringing\r\n"
                f"Via: SIP/2.0/UDP {addr[0]}:{addr[1]}\r\n"
                "Content-Length: 0\r\n\r\n"
            ).encode()
            self.transport.sendto(ringing, addr)
            # 200 OK
            ok = (
                "SIP/2.0 200 OK\r\n"
                f"Via: SIP/2.0/UDP {addr[0]}:{addr[1]}\r\n"
                "Content-Length: 0\r\n\r\n"
            ).encode()
            self.transport.sendto(ok, addr)
            print(f"✔️ INVITE répondu 180/200 à {addr}")

async def start_sip_server():
    loop = asyncio.get_running_loop()

    # 1) Démarre le listener UDP
    await loop.create_datagram_endpoint(
        lambda: SIPProtocol(),
        local_addr=('0.0.0.0', SIP_PORT)
    )

    # 2) Lance la tâche de REGISTER périodique
    asyncio.create_task(sip_register_loop())

    # 3) Bloque pour garder en vie
    await asyncio.Event().wait()
