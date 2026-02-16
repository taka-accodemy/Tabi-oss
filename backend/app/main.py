import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
print("--- Tabi Backend Starting ---")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1 import api_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database if needed
    if settings.DB_TYPE != "bigquery":
        print(f"DEBUG: Lifespan startup - calling init_db for {settings.DB_TYPE}")
        try:
            await init_db()
            print("DEBUG: Lifespan startup - init_db success")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG: Lifespan init_db FAILED: {e}\n{error_details}")
            logging.error(f"Lifespan startup error (non-fatal): {e}")
    else:
        print("DEBUG: Lifespan startup - init_db SKIPPED for BigQuery mode")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Chat BI Backend with Cube.js and LLM integration",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up trusted host middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Logging configured at top of file (before imports) with force=True

@app.get("/")
async def root():
    return {"message": "Chat BI Backend API", "version": settings.VERSION}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}