import sys
import os
import logging

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_startup")

print("DEBUG: Starting import test")

# ... (imports) ...
startup_error = None

try:
    print("DEBUG: Importing fastapi")
    from fastapi import FastAPI
    import uvicorn
    
    # ... (other imports) ...
    print("DEBUG: Importing app.main")
    from app.main import app as main_app
    print("DEBUG: Import test COMPLETE")

except Exception as e:
    import traceback
    startup_error = f"{e}\n{traceback.format_exc()}"
    print(f"DEBUG: CRITICAL STARTUP ERROR: {startup_error}")

# Always start a dummy app to expose the error
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    if startup_error:
        return {"status": "startup_failed", "error": startup_error}
    return {"status": "startup_success", "message": "All imports loaded correctly"}

@app.get("/health")
def health():
    return {"status": "healthy"}


# If all good, allow starting a dummy app to keep container alive
app = FastAPI()

@app.get("/")
def root():
    return {"status": "debug_ok", "imports": "success"}

@app.get("/health")
def health():
    return {"status": "healthy"}
