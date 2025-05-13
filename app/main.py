import os
import nest_asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.websocket_routes import websocket_router
from app.sip_server import start_sip_server
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()

app = FastAPI()
app.include_router(websocket_router)

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "VoixIA SIP server is running."}

if __name__ == "__main__":
    import uvicorn
    start_sip_server()
    uvicorn.run(app, host="0.0.0.0", port=5050)