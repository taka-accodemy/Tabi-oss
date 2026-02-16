from fastapi import APIRouter
from .endpoints import query, schema, health, auth, config

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(schema.router, prefix="/schema", tags=["schema"])
api_router.include_router(config.router, prefix="/config", tags=["config"])