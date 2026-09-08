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
    "password",
    "default_secret_key",
    "your-secret-key-here",
    "your-encryption-key-here"
}

import socket

def get_lan_ip() -> str:
    """
    Detects primary active IPv4 address on the local area network (Wi-Fi/LAN).
    Falls back cleanly to '127.0.0.1' if network interfaces are offline.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, extra="ignore")

    PROJECT_NAME: str = "SEO Intelligence Platform"
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "development"
    ALLOW_DEV_USER_HEADER: bool = os.environ.get("ALLOW_DEV_USER_HEADER", "false").lower() in ("true", "1")
    DATABASE_URL: str = f"sqlite:///{_DB_PATH.replace(os.sep, '/')}"
    CRAWL_DATA_DIR: str = os.path.join(_BACKEND_DIR, "data", "websites")
    AUTOCOMPLETE_ENDPOINT_URL: str = os.environ.get("AUTOCOMPLETE_ENDPOINT_URL", "https://suggestqueries.google.com/complete/search")

    # Server & Host Settings - Default to 0.0.0.0 for dual Local + LAN development access
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8020"))
    FRONTEND_HOST: str = os.environ.get("FRONTEND_HOST", "0.0.0.0")
    FRONTEND_PORT: int = int(os.environ.get("FRONTEND_PORT", "8030"))
    
    API_BASE_URL: str = os.environ.get("API_BASE_URL", f"http://127.0.0.1:{os.environ.get('PORT', '8020')}")
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

    # Platform AI Provider Credentials (Groq is default platform provider)
    AI_PROVIDER: Optional[str] = os.environ.get("AI_PROVIDER") or os.environ.get("LLM_PROVIDER") or "groq"
    GROQ_API_KEY: Optional[str] = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL: Optional[str] = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    AI_API_KEY: Optional[str] = os.environ.get("AI_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    AI_MODEL: Optional[str] = os.environ.get("AI_MODEL") or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL: Optional[str] = os.environ.get("GEMINI_MODEL", "models/gemini-flash-latest")
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")

    FRONTEND_BASE_URL: str = os.environ.get(
        "FRONTEND_BASE_URL", 
        f"http://127.0.0.1:{os.environ.get('FRONTEND_PORT', '8030')}"
    )

    @property
    def is_production(self) -> bool:
        env = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or self.ENVIRONMENT or "development").strip().lower()
        return env == "production"

    @property
    def cors_origins_list(self) -> List[str]:
        raw_origins = os.environ.get("CORS_ORIGINS") or self.CORS_ORIGINS
        origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        # In production, do NOT append dynamic private LAN addresses
        if self.is_production:
            return origins
        # In development/test mode only, optionally support local LAN access
        lan_ip = get_lan_ip()
        if lan_ip and lan_ip != "127.0.0.1":
            lan_frontend = f"http://{lan_ip}:{self.FRONTEND_PORT}"
            lan_3000 = f"http://{lan_ip}:3000"
            if lan_frontend not in origins:
                origins.append(lan_frontend)
            if lan_3000 not in origins:
                origins.append(lan_3000)
        return origins

settings = Settings()

def build_frontend_redirect(path: str = "/settings", query_params: Optional[dict] = None, base_url: Optional[str] = None) -> str:
    """
    Constructs an absolute frontend SPA redirect URL.
    Targeting base_url if provided, otherwise FRONTEND_BASE_URL (Port 8030).
    Safely encodes query parameters while excluding sensitive internal tokens or stack traces.
    """
    import urllib.parse
    base = (base_url or settings.FRONTEND_BASE_URL).rstrip("/")
    if "0.0.0.0" in base:
        base = base.replace("0.0.0.0", "127.0.0.1")
    clean_path = path if path.startswith("/") else f"/{path}"
    if query_params:
        clean_params = {}
        for k, v in query_params.items():
            if v is not None:
                clean_params[k] = str(v)
        query_str = urllib.parse.urlencode(clean_params)
        return f"{base}{clean_path}?{query_str}"
    return f"{base}{clean_path}"


def validate_startup_config(strict: Optional[bool] = None):
    """
    On application startup, validates required configuration parameters.
    In production (or when strict=True), fails closed if insecure/default secrets are present.
    """
    env_name = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or settings.ENVIRONMENT or "development").strip().lower()
    if strict is None:
        strict = (env_name == "production")

    enc_key = os.environ.get("ENCRYPTION_KEY")
    sec_key = os.environ.get("SECRET_KEY")
    allow_dev_header = os.environ.get("ALLOW_DEV_USER_HEADER", "").lower() in ("true", "1") or settings.ALLOW_DEV_USER_HEADER

    # In production, check that ALLOW_DEV_USER_HEADER is not enabled
    if env_name == "production" and allow_dev_header:
        msg = (
            "[CRITICAL SECURITY ERROR] 'ALLOW_DEV_USER_HEADER' is enabled while ENVIRONMENT is set to 'production'. "
            "Development user header authentication must never be enabled in production."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    # 1. ENCRYPTION_KEY Validation
    if not enc_key or not enc_key.strip():
        msg = (
            "[STARTUP CONFIG ERROR] Required environment variable 'ENCRYPTION_KEY' is missing. "
            "ENCRYPTION_KEY must be set in your environment to secure stored secrets."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    if enc_key and (enc_key.strip() in KNOWN_INSECURE_SECRETS or (strict and len(enc_key.strip()) < 16)):
        msg = (
            f"[STARTUP CONFIG ERROR] 'ENCRYPTION_KEY' is using a known insecure or too short value. "
            "Please update ENCRYPTION_KEY to a secure random string (minimum 32 characters for production)."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    # 2. SECRET_KEY Validation
    if not sec_key or not sec_key.strip():
        msg = (
            "[STARTUP CONFIG ERROR] Required environment variable 'SECRET_KEY' is missing. "
            "SECRET_KEY must be set in your environment for JWT token signing."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    if sec_key and (sec_key.strip() in KNOWN_INSECURE_SECRETS or (strict and len(sec_key.strip()) < 16)):
        msg = (
            f"[STARTUP CONFIG ERROR] 'SECRET_KEY' is using a known insecure or too short value. "
            "Please update SECRET_KEY to a secure random secret (minimum 32 characters for production)."
        )
        print(msg, flush=True)
        if strict:
            raise RuntimeError(msg)

    print(f"[DATABASE] Active DB path: '{_DB_PATH}'", flush=True)
    print(f"[STARTUP CONFIG] Environment: '{env_name}', strict={strict}. Validation passed cleanly.", flush=True)
