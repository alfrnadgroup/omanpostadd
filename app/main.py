# main.py
from fastapi import FastAPI
from app.api import addresses

app = FastAPI(title="Oman Post Addressing System")

app.include_router(addresses.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Welcome to Oman Post Addressing System"}
