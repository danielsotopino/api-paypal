import os
from pydantic_settings import BaseSettings
from typing import List, Optional

# Determinar el nombre del archivo de entorno
project_name = os.getenv("PROJECT_NAME", "paypal-api")
custom_env_file = f".env.{project_name}"

env_file = custom_env_file if os.path.exists(custom_env_file) else ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "PayPal API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str
    # DATABASE_ENCRYPT_KEY: str
    
    # PayPal Configuration
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    
    # Security
    # SECRET_KEY: str
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    SERVICE_NAME: str = "api-paypal"
    SERVICE_VERSION: str = "1.0.0"
    
    # Rate Limiting
    RATE_LIMIT_PAYMENT: int = 10
    RATE_LIMIT_SUBSCRIPTION: int = 100
    RATE_LIMIT_QUERY: int = 1000
    
    class Config:
        env_file = env_file
        case_sensitive = True

settings = Settings()