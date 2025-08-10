from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.api import addresses  # your existing API router
import os

app = FastAPI(title="Oman Post Addressing System")

# Use absolute path for static directory, relative to current file location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Serve static files (JS, CSS, index.html)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include the addresses router (this router should provide /api/plots and /api/addresses/{code})
app.include_router(addresses.router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()
