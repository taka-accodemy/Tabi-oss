from fastapi import FastAPI
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World", "PORT": os.environ.get("PORT")}

@app.get("/health")
def health():
    return {"status": "ok"}

logger.info("Minimal app started")
