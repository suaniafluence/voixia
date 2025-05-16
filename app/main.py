import os
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
from scripts.sip_listener import start_sip_server, stop_sip_server
from prometheus_client import generate_latest, Gauge, CollectorRegistry
import socket

# Configuration initiale
load_dotenv()

# Métriques Prometheus
registry = CollectorRegistry()
sip_registered = Gauge('sip_registered', 'SIP registration status', registry=registry)
active_calls = Gauge('sip_active_calls', 'Current active calls', registry=registry)
rtp_ports = Gauge('sip_rtp_ports', 'Active RTP ports', registry=registry)

app = FastAPI()
sip_protocol = None

# ─── Handlers d'événements ──────────────────────────────────────────────
async def sip_startup():
    global sip_protocol
    try:
        # Résolution DNS explicite pour OVH
        sip_server = os.getenv("SIP_SERVER")
        sip_port = int(os.getenv("SIP_PORT", 5060))

        # NEW: Gestion plus robuste de l'adresse
        if not sip_server:
            raise ValueError("SIP_SERVER non configuré dans .env")        


        addr_info = socket.getaddrinfo(sip_server, sip_port, 
                                      type=socket.SOCK_DGRAM, 
                                      proto=socket.IPPROTO_UDP)
        # NEW: Vérification des résultats DNS
        if not addr_info:
            raise ValueError(f"Impossible de résoudre {sip_server}:{sip_port}")
        
        sip_protocol = await start_sip_server(addr_info[0][4])
        print(f"✅ SIP connecté à {sip_server}:{sip_port}")
    except Exception as e:
        print(f"❌ Échec connexion SIP: {str(e)}")
        raise RuntimeError("Échec démarrage SIP") from e

async def sip_shutdown():


    if sip_protocol:
        await stop_sip_server(sip_protocol)
        print("🛑 SIP arrêté proprement")

app.add_event_handler("startup", sip_startup)
app.add_event_handler("shutdown", sip_shutdown)

# ─── Routes API ────────────────────────────────────────────────────────
@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "service": "VoixIA SIP Proxy",
        "status": "running",
        "sip_server": os.getenv("SIP_SERVER"),
        "sip_user": os.getenv("SIP_USERNAME").split("@")[0]
    }

@app.get("/healthz", response_class=JSONResponse)
async def healthcheck():
    status = {
        "components": {
            "http": "ok",
            "sip": "registered" if sip_protocol and sip_protocol.registered else "disconnected",
            "rtp": "active" if sip_protocol and sip_protocol.rtp_ports else "inactive"
        },
        "metrics": {
            "active_calls": len(sip_protocol.active_calls) if sip_protocol else 0,
            "last_error": sip_protocol.last_error if sip_protocol else None
        }
    }
    
    # Mise à jour Prometheus
    if sip_protocol:
        sip_registered.set(int(sip_protocol.registered))
        active_calls.set(len(sip_protocol.active_calls))
        rtp_ports.set(len(sip_protocol.rtp_ports))
    
    return status

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(registry),
        media_type="text/plain"
    )

# ─── Debug Endpoints (optionnel) ───────────────────────────────────────
@app.get("/debug/sip")
async def debug_sip():
    if not sip_protocol:
        return {"error": "SIP non initialisé"}
    
    return {
        "registered": sip_protocol.registered,
        "active_calls": list(sip_protocol.active_calls.keys()),
        "rtp_ports": list(sip_protocol.rtp_ports),
        "last_challenge": sip_protocol.challenge
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)