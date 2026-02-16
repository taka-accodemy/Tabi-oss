#!/usr/bin/env python3
import subprocess
import os
import sys

def run_backend():
    project_root = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(project_root, "backend")
    
    if not os.path.exists(backend_dir):
        print(f"Error: Backend directory not found at {backend_dir}")
        sys.exit(1)
    
    print("🚀 Starting Tabi Backend (FastAPI) using venv...")
    try:
        # Use the uvicorn from the virtual environment explicitly
        venv_uvicorn = os.path.join(project_root, "venv", "bin", "uvicorn")
        if not os.path.exists(venv_uvicorn):
            # Fallback for some systems where it might be in 'Scripts' (Windows, but not here)
            venv_uvicorn = "uvicorn" 
            
        subprocess.run([
            venv_uvicorn, "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"
        ], cwd=backend_dir)
    except KeyboardInterrupt:
        print("\n👋 Backend stopped.")
    except FileNotFoundError:
        print("Error: 'uvicorn' not found. Please ensure it is installed in your virtual environment.")

if __name__ == "__main__":
    run_backend()
