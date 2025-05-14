import os
import nest_asyncio
nest_asyncio.apply()
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .websocket_routes import websocket_router
from .sip_server import start_sip_server
from dotenv import load_dotenv

load_dotenv()



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FastAPI démarrage — lancement du serveur SIP…")
    asyncio.create_task(start_sip_server())
    yield
    print("🛑 Arrêt FastAPI — nettoyage possible ici.")

app = FastAPI(lifespan=lifespan)
app.include_router(websocket_router)



@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "VoixIA SIP server is running."}

if __name__ == "__main__":
    import uvicorn
    start_sip_server()
    uvicorn.run(app, host="0.0.0.0", port=5050)