from fastapi import APIRouter
from typing import Dict, Any
import logging
from datetime import datetime

from app.services.cube_service import cube_service
from app.services.llm_bridge import llm_bridge
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check including external services"""
    result = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "services": {}
    }
    
    # Check Cube.js
    try:
        cube_healthy = await cube_service.health_check()
        result["services"]["cube"] = {
            "status": "healthy" if cube_healthy else "unhealthy",
            "url": settings.CUBE_API_URL
        }
    except Exception as e:
        result["services"]["cube"] = {
            "status": "error",
            "error": str(e),
            "url": settings.CUBE_API_URL
        }
    
    # Check LLM providers
    try:
        providers = llm_bridge.list_providers()
        result["services"]["llm"] = {
            "status": "healthy" if providers else "no_providers",
            "providers": providers,
            "default_provider": settings.DEFAULT_LLM_PROVIDER
        }
    except Exception as e:
        result["services"]["llm"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Overall status
    service_statuses = [service.get("status") for service in result["services"].values()]
    if "error" in service_statuses or "unhealthy" in service_statuses:
        result["status"] = "degraded"
    elif "no_providers" in service_statuses:
        result["status"] = "warning"
    
    return result


@router.get("/readiness")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        # Check if essential services are available
        cube_healthy = await cube_service.health_check()
        llm_providers = llm_bridge.list_providers()
        
        if cube_healthy and llm_providers:
            return {"status": "ready"}
        else:
            return {"status": "not_ready", "reason": "Essential services not available"}
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}


@router.get("/liveness")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}


@router.get("/metrics")
async def get_metrics():
    """Get basic metrics"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "unknown",  # Would need to track this
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG
    }