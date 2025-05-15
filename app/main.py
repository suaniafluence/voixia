from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from scripts.sip_listener import start_sip_server
from app.websocket_routes import websocket_router

load_dotenv()

app = FastAPI()
app.include_router(websocket_router)

app.add_event_handler("startup",  start_sip_server)
app.add_event_handler("shutdown", lambda: print("🛑 Arrêt SIP listener."))

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "VoixIA SIP server is running."}

# ─── Healthcheck simple ──────────────────────────────────────────────
@app.get("/healthz", response_class=JSONResponse)
async def healthcheck():
    """
    Vérifie que l’API HTTP est up et que notre boucle SIP tourne.
    """
    # Tu pourrais aussi vérifier ici un drapeau ou un état global
    return {
        "http": "ok",
        "sip_listener": "ok"
    }