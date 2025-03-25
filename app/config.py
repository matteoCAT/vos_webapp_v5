import os
from typing import Dict, List, Optional, Union
from pydantic import validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings that can be configured through environment variables
    """
    # Application settings
    APP_NAME: str = "Restaurant Manager"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    SESSION_COOKIE: str = "session"
    SESSION_MAX_AGE: int = 14 * 24 * 60 * 60  # 14 days in seconds

    # API settings
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001/api/v1")
    API_TIMEOUT: int = 30.0  # seconds
    VERIFY_SSL: bool = os.getenv("VERIFY_SSL", "True").lower() in ("true", "1", "t")

    # Authentication settings
    AUTH_TOKEN_NAME: str = "access_token"
    AUTH_REFRESH_TOKEN_NAME: str = "refresh_token"

    # Template settings
    TEMPLATE_RELOAD: bool = DEBUG

    class Config:
        """Pydantic config"""
        env_file = ".env"
        case_sensitive = True


# Create a global settings object
settings = Settings()