import os
from pydantic_settings import BaseSettings

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/app
_BACKEND_DIR = os.path.dirname(_BASE_DIR) # backend
_DB_PATH = os.path.join(_BACKEND_DIR, "seo.db")

class Settings(BaseSettings):
    PROJECT_NAME: str = "SEO Intelligence Platform"
    DATABASE_URL: str = f"sqlite:///{_DB_PATH.replace(os.sep, '/')}"

    class Config:
        env_file = ".env"

settings = Settings()
