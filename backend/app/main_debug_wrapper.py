import sys
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# Configure basic logging immediately
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_wrapper")

startup_error = None
app_main_module = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_error, app_main_module
    logger.info("DEBUG WRAPPER: Lifespan started")
    
    try:
        logger.info("DEBUG WRAPPER: Attempting to import app.main")
        # Doing the import inside lifespan to catch module-level errors during startup flow
        from app.main import app as original_app
        # main.py defines 'lifespan'
        from app.main import lifespan as original_lifespan
        
        app_main_module = True
        logger.info("DEBUG WRAPPER: app.main imported. Entering original lifespan.")
        
        # We must use the original app instance for the lifespan context
        async with original_lifespan(original_app):
            logger.info("DEBUG WRAPPER: Original lifespan yielded successfully")
            yield
            logger.info("DEBUG WRAPPER: Original lifespan exited")
            
    except Exception:
        startup_error = traceback.format_exc()
        logger.error(f"DEBUG WRAPPER: Captured startup error:\n{startup_error}")
        # Yield to allow the application to start and verify the error via HTTP
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    if startup_error:
        return {
            "status": "startup_failed", 
            "error": startup_error,
            "app_main_imported": bool(app_main_module)
        }
    if not app_main_module:
        return {"status": "warning", "message": "Lifespan did not run or import failed silently?"}
        
    return {"status": "startup_success", "message": "Original app started correctly (wrapper is active)"}

@app.get("/health")
def health():
    return {"status": "healthy_wrapper"}
