import os
import sys
import socket
import logging
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
from prometheus_client import generate_latest, Gauge, CollectorRegistry

# Import des fonctions de démarrage/arrêt du SIP listener
from scripts.sip_listener import start_sip_server, stop_sip_server

load_dotenv()

# Logger pour le main
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

# Métriques Prometheus
registry = CollectorRegistry()
sip_registered = Gauge('sip_registered', 'SIP registration status', registry=registry)
active_calls   = Gauge('sip_active_calls',   'Current active calls',     registry=registry)
rtp_ports      = Gauge('sip_rtp_ports',      'Active RTP ports',         registry=registry)

app = FastAPI()
sip_protocol = None


@app.on_event("startup")
async def sip_startup():
    global sip_protocol

    sip_server = os.getenv("SIP_SERVER")
    sip_port   = int(os.getenv("SIP_PORT", 5060))

    if not sip_server:
        logger.error("SIP_SERVER non configuré dans .env")
        sys.exit(1)

    # Résolution DNS pour OVH
    try:
        infos = socket.getaddrinfo(sip_server, sip_port,
                                   socket.AF_UNSPEC, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        if not infos:
            raise ValueError("Aucun résultat DNS")
        host_ip, port = infos[0][4]
        registrar_addr = (host_ip, port)
    except Exception as e:
        logger.error(f"Échec résolution DNS de {sip_server}:{sip_port} → {e}")
        sys.exit(1)

    # Démarrage du serveur SIP
    try:
        sip_protocol = await start_sip_server(registrar_addr)
        logger.info(f"SIP connecté à {sip_server}:{sip_port} ({host_ip})")
    except Exception as e:
        logger.error(f"Échec démarrage SIP: {e}")
        sys.exit(1)


@app.on_event("shutdown")
async def sip_shutdown():
    global sip_protocol
    if sip_protocol:
        await stop_sip_server(sip_protocol)
        logger.info("🛑 SIP arrêté proprement")


@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "service":   "VoixIA SIP Proxy",
        "status":    "running",
        "sip_server": os.getenv("SIP_SERVER"),
        "sip_user":   os.getenv("SIP_USERNAME"),
    }


@app.get("/healthz", response_class=JSONResponse)
async def healthcheck():
    registered = bool(sip_protocol and getattr(sip_protocol, "registered", False))
    calls      = sip_protocol.active_calls if sip_protocol else {}
    ports      = sip_protocol.rtp_ports     if sip_protocol else set()
    last_err   = getattr(sip_protocol, "last_error", None) if sip_protocol else None

    # Mise à jour des métriques
    sip_registered.set(int(registered))
    active_calls.set(len(calls))
    rtp_ports.set(len(ports))

    return {
        "components": {
            "http": "ok",
            "sip":  "registered" if registered else "disconnected",
            "rtp":  "active"    if ports else "inactive"
        },
        "metrics": {
            "active_calls": len(calls),
            "last_error":   last_err
        }
    }


@app.get("/ping")
async def ping():
    return PlainTextResponse("pong")


@app.get("/metrics")
async def metrics():
    payload = generate_latest(registry)
    return Response(content=payload, media_type="text/plain")


@app.get("/debug/sip", response_class=JSONResponse)
async def debug_sip():
    if not sip_protocol:
        return {"error": "SIP non initialisé"}

    return {
        "registered":    sip_protocol.registered,
        "active_calls":  list(sip_protocol.active_calls.keys()),
        "rtp_ports":     list(sip_protocol.rtp_ports),
        "last_challenge": sip_protocol.challenge
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050, log_level="debug")
