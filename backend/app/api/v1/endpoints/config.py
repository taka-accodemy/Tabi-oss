from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.config_service import config_service
from app.api.deps import get_current_active_user
from app.core.security import User
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()

class DatabaseConfigRequest(BaseModel):
    db_type: str
    config_data: Dict[str, Any]

@router.get("/database")
async def get_database_config(current_user: User = Depends(get_current_active_user)):
    """Get current database configuration"""
    return {
        "db_type": config_service.get_db_type(),
        "config": config_service.get_config()
    }

@router.post("/database")
async def update_database_config(
    request: DatabaseConfigRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Update database configuration"""
    try:
        success = config_service.update_db_config(request.db_type, request.config_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save database configuration")
        return {"success": True, "message": "Database configuration updated"}
    except Exception as e:
        logger.error(f"Error updating db config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/credentials/upload")
async def upload_credentials(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a credential file (GCP JSON, AWS credentials, etc.)"""
    try:
        content = await file.read()
        file_path = config_service.save_credential_file(file.filename, content)
        return {"success": True, "file_path": file_path, "filename": file.filename}
    except Exception as e:
        logger.error(f"Error uploading credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))
