import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/app
_BACKEND_DIR = os.path.dirname(_BASE_DIR) # backend
_DB_PATH = os.path.join(_BACKEND_DIR, "seo.db")
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")

# Automatically load environment variables from backend/.env into os.environ
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, extra="ignore")

    PROJECT_NAME: str = "SEO Intelligence Platform"
    DATABASE_URL: str = f"sqlite:///{_DB_PATH.replace(os.sep, '/')}"
    SECRET_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

settings = Settings()


