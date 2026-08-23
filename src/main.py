import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import signals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="UltraCore Headless MT5 Signals",
    description="Lightweight FastAPI service for MT5 signal generation.",
    version="1.0.0"
)

# Add CORS for local testing if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the new signals router
app.include_router(signals.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "UltraCore Signal Generator"}
