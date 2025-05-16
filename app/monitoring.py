from prometheus_client import generate_latest, Gauge, CollectorRegistry
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

# Créez un registre Prometheus isolé
registry = CollectorRegistry()

# Métriques
sip_registered = Gauge(
    "sip_registered",
    "État d'enregistrement SIP",
    registry=registry
)

active_calls = Gauge(
    "sip_active_calls",
    "Nombre d'appels actifs",
    registry=registry
)

rtp_ports_used = Gauge(
    "sip_rtp_ports_used",
    "Ports RTP utilisés",
    registry=registry
)

router = APIRouter()

@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    # Mettez à jour les métriques ici si nécessaire
    return Response(
        content=generate_latest(registry),
        media_type="text/plain"
    )