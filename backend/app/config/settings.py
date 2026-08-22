import os
from typing import Optional, List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/app
_BACKEND_DIR = os.path.dirname(_BASE_DIR)  # backend
_DB_PATH = os.path.join(_BACKEND_DIR, "seo.db")
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")

# Automatically load environment variables from backend/.env into os.environ
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH)

KNOWN_INSECURE_SECRETS = {
    "seo-platform-secure-default-encryption-secret-key-32b",
    "oauth-csrf-protection-secret-key-32b",
    "change_me",
    "secret",
    "password"
}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, extra="ignore")

    PROJECT_NAME: str = "SEO Intelligence Platform"
    DATABASE_URL: str = f"sqlite:///{_DB_PATH.replace(os.sep, '/')}"
    CRAWL_DATA_DIR: str = os.path.join(_BACKEND_DIR, "data", "websites")

    
    # Server & Host Settings
    HOST: str = os.environ.get("HOST", "127.0.0.1")
    PORT: int = int(os.environ.get("PORT", "8020"))
    FRONTEND_HOST: str = os.environ.get("FRONTEND_HOST", "127.0.0.1")
    FRONTEND_PORT: int = int(os.environ.get("FRONTEND_PORT", "8030"))
    
    API_BASE_URL: str = os.environ.get("API_BASE_URL", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('PORT', '8020')}")
    CORS_ORIGINS: str = os.environ.get(
        "CORS_ORIGINS", 
        f"http://localhost:{os.environ.get('FRONTEND_PORT', '8030')},http://127.0.0.1:{os.environ.get('FRONTEND_PORT', '8030')},http://localhost:3000,http://127.0.0.1:3000"
    )
    
    # Security Secrets
    SECRET_KEY: Optional[str] = os.environ.get("SECRET_KEY")
    ENCRYPTION_KEY: Optional[str] = os.environ.get("ENCRYPTION_KEY")
    OAUTH_STATE_SECRET: Optional[str] = os.environ.get("OAUTH_STATE_SECRET") or os.environ.get("SECRET_KEY")
    
    # Provider OAuth Credentials
    GOOGLE_CLIENT_ID: Optional[str] = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.environ.get("GOOGLE_CLIENT_SECRET")
    META_APP_ID: Optional[str] = os.environ.get("META_APP_ID") or os.environ.get("FACEBOOK_CLIENT_ID")
    META_APP_SECRET: Optional[str] = os.environ.get("META_APP_SECRET") or os.environ.get("FACEBOOK_CLIENT_SECRET")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()

def validate_startup_config(strict: bool = True):
    """
    On application startup, validates required configuration parameters.
    Ensures ENCRYPTION_KEY and SECRET_KEY are configured safely.
    """
    enc_key = os.environ.get("ENCRYPTION_KEY")
    sec_key = os.environ.get("SECRET_KEY")

    if not enc_key or not enc_key.strip():
        msg = (
            "[STARTUP CONFIG ERROR] Required environment variable 'ENCRYPTION_KEY' is missing. "
            "ENCRYPTION_KEY must be set in your environment or backend/.env file to secure stored secrets."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    if enc_key in KNOWN_INSECURE_SECRETS:
        msg = (
            f"[STARTUP CONFIG ERROR] 'ENCRYPTION_KEY' is using a known insecure default value ('{enc_key}'). "
            "Please update ENCRYPTION_KEY to a secure 32-character random string."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    if sec_key and sec_key in KNOWN_INSECURE_SECRETS:
        msg = (
            f"[STARTUP CONFIG ERROR] 'SECRET_KEY' is using a known insecure default value ('{sec_key}'). "
            "Please update SECRET_KEY to a secure random secret."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    print(f"[DATABASE] Active DB path: '{_DB_PATH}'", flush=True)
    print("[STARTUP CONFIG] Configuration validation passed cleanly.", flush=True)

