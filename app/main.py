# main.py
import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from app.websocket_routes import websocket_router
from scripts.sip_listener import start_sip_server

load_dotenv()

app = FastAPI()
app.include_router(websocket_router)

app.add_event_handler("startup",  start_sip_server)  # lance ton SIP listener
app.add_event_handler("shutdown", lambda: print("🛑 Arrêt SIP server."))

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "VoixIA SIP server is running."}


