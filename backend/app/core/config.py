from pydantic_settings import BaseSettings
from pydantic import field_validator, validator
from typing import Any, Dict, List, Optional, Union
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "Chat BI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/chatbi"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-exp:free"
    DEFAULT_LLM_PROVIDER: str = "gemini"
    DB_TYPE: str = "postgres"
    
    # Gemini / Vertex AI Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_LOCATION: str = "asia-northeast1"
    
    # Supabase Configuration (Optional for SaaS/Edge Functions)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Vanna Configuration
    VANNA_API_KEY: Optional[str] = None
    VANNA_MODEL_NAME: str = "tabi-retail"
    
    # Cube.js Configuration
    CUBE_API_URL: str = "http://localhost:4000"
    CUBE_API_SECRET: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v: str, values: Dict[str, Any]) -> str:
        if v == "your-secret-key-here-change-in-production" and values.get("ENVIRONMENT") == "production":
            raise ValueError("SECRET_KEY must be changed in production!")
        return v
    
    # CORS
    BACKEND_CORS_ORIGINS: Any = ""
    
    # Trusted hosts
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()