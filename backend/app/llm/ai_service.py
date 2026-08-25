import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.logger import get_logger
from app.models.external_connection import ExternalConnection
from app.llm.llm_provider import (
    LLMProvider,
    GroqProviderAdapter,
    OpenAIProviderAdapter,
    GeminiProviderAdapter,
    AnthropicProviderAdapter,
    AIProviderException,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_MODEL
)
from app.llm.ollama_adapter import OllamaProviderAdapter, DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL

logger = get_logger(__name__)


class AIService:
    """
    Central AI Provider Service Manager.
    Serves as the single unified entry point for all AI capabilities in the platform.
    Manages Ollama local AI, Groq platform default AI, and customer BYO AI keys (OpenAI, Gemini, Claude).
    """

    @classmethod
    def get_provider_status_matrix(
        cls, 
        user_id: Optional[str] = None, 
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Returns full diagnostic status of all 5 provider types.
        Guarantees NO raw secrets or credentials are ever returned.
        """
        # 1. Ollama Status
        ollama_adapter = OllamaProviderAdapter()
        ollama_status = {"available": False, "provider": "ollama", "name": "Ollama Local AI"}
        try:
            o_test = ollama_adapter.test_connection(timeout=3.0)
            ollama_status.update({
                "available": True,
                "status": "AVAILABLE",
                "base_url": o_test.get("base_url", DEFAULT_OLLAMA_BASE_URL),
                "selected_model": o_test.get("selected_model", DEFAULT_OLLAMA_MODEL),
                "installed_models": o_test.get("installed_models", []),
                "hardware_fit": o_test.get("hardware_fit", "OPTIMAL"),
                "hardware_badge": o_test.get("hardware_badge", "Suitable for this computer"),
                "hardware_detail": o_test.get("hardware_detail", ""),
                "description": "Runs 100% locally on your computer. Zero external cloud API calls."
            })
        except Exception as e:
            ollama_status.update({
                "available": False,
                "status": "NOT_AVAILABLE",
                "base_url": DEFAULT_OLLAMA_BASE_URL,
                "selected_model": DEFAULT_OLLAMA_MODEL,
                "installed_models": [],
                "hardware_fit": "OPTIMAL",
                "hardware_badge": "Ollama Offline",
                "hardware_detail": "Ollama isn't running on this device. Install and start Ollama to use local AI.",
                "description": "Local AI is currently offline."
            })

        # 2. Groq Status
        groq_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
        groq_configured = bool(groq_key and groq_key.strip())
        groq_models = []
        active_groq_model = settings.GROQ_MODEL or "openai/gpt-oss-120b"
        if groq_configured:
            try:
                g_adapter = GroqProviderAdapter(api_key=groq_key)
                groq_models = g_adapter.fetch_available_models(timeout=5.0)
                if groq_models and not settings.GROQ_MODEL:
                    active_groq_model = groq_models[0]["id"]
            except Exception as e:
                logger.warning(f"Failed to fetch Groq models for status matrix: {e}")

        groq_status = {
            "provider": "groq",
            "name": "Groq Platform AI",
            "available": groq_configured and (len(groq_models) > 0 or True),
            "status": "AVAILABLE" if groq_configured else "NOT_CONFIGURED",
            "model": active_groq_model,
            "available_models": groq_models,
            "is_platform_default": True,
            "description": "Groq is provided automatically by the platform. No personal API key required."
        }

        # 3. Customer Connections (OpenAI, Gemini, Claude)
        customer_map = {}
        if user_id and db:
            try:
                conns = db.query(ExternalConnection).filter(
                    ExternalConnection.user_id == user_id,
                    ExternalConnection.provider.in_(["openai", "gemini", "claude", "anthropic"])
                ).all()
                for c in conns:
                    customer_map[c.provider.lower()] = c
            except Exception as e:
                logger.warning(f"Error fetching customer connections: {e}")

        customer_providers = [
            ("openai", "OpenAI / ChatGPT", "GPT-4o & Mini models"),
            ("gemini", "Google Gemini", "Gemini Flash & Pro models"),
            ("claude", "Anthropic Claude", "Claude 3.5 Sonnet")
        ]

        customer_status = {}
        for p_code, p_name, m_info in customer_providers:
            conn = customer_map.get(p_code)
            if conn and conn.get_api_key():
                customer_status[p_code] = {
                    "provider": p_code,
                    "name": p_name,
                    "model_info": m_info,
                    "connected": True,
                    "enabled": conn.status == "CONNECTED",
                    "status": conn.status,
                    "masked_key": conn.to_safe_dict().get("masked_key", "")
                }
            else:
                customer_status[p_code] = {
                    "provider": p_code,
                    "name": p_name,
                    "model_info": m_info,
                    "connected": False,
                    "enabled": False,
                    "status": "NOT_CONNECTED",
                    "masked_key": ""
                }

        # Active provider resolution
        active_provider_info = cls.get_active_provider_info(user_id=user_id, db=db)

        return {
            "active_provider": active_provider_info["provider"],
            "active_provider_name": active_provider_info["name"],
            "active_model": active_provider_info["model"],
            "providers": {
                "ollama": ollama_status,
                "groq": groq_status,
                "openai": customer_status["openai"],
                "gemini": customer_status["gemini"],
                "claude": customer_status["claude"]
            }
        }

    @classmethod
    def get_active_provider_info(
        cls, 
        user_id: Optional[str] = None, 
        db: Optional[Session] = None,
        preferred_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns metadata regarding which provider is currently active for requests."""
        provider = cls.get_provider(user_id=user_id, db=db, preferred_provider=preferred_provider)
        if not provider:
            return {"provider": "none", "name": "None Configured", "model": "none"}
        
        p_name = getattr(provider, "provider_name", type(provider).__name__.replace("ProviderAdapter", "").lower())
        name_map = {
            "ollama": "Ollama Local AI",
            "groq": "Groq Platform AI",
            "openai": "OpenAI / ChatGPT",
            "gemini": "Google Gemini",
            "claude": "Anthropic Claude",
            "anthropic": "Anthropic Claude"
        }
        return {
            "provider": p_name,
            "name": name_map.get(p_name, p_name.title()),
            "model": getattr(provider, "model", "default")
        }

    @classmethod
    def get_provider(
        cls, 
        user_id: Optional[str] = None, 
        db: Optional[Session] = None,
        preferred_provider: Optional[str] = None,
        selected_model: Optional[str] = None
    ) -> Optional[LLMProvider]:
        """
        Instantiates the active LLMProvider based on explicit preference or fallback cascade.
        Precedence:
        1. Explicit preferred provider (if available & configured).
        2. Active customer BYO AI key ('openai', 'claude', 'gemini') bound to user_id.
        3. Platform default Groq ('GROQ_API_KEY').
        4. Ollama local AI (if reachable).
        5. Platform fallback environment keys.
        """
        p_pref = (preferred_provider or "").lower().strip()

        # 1. Handle explicit preferred provider choice if specified and valid
        if p_pref == "ollama":
            adapter = OllamaProviderAdapter(model=selected_model)
            try:
                adapter.test_connection(timeout=2.0)
                return adapter
            except Exception as e:
                logger.warning(f"Preferred provider 'ollama' is not available: {e}")

        elif p_pref in ("openai", "gpt") and user_id and db:
            conn = cls._get_customer_connection(user_id, db, "openai")
            if conn and conn.get_api_key():
                return OpenAIProviderAdapter(api_key=conn.get_api_key())

        elif p_pref in ("claude", "anthropic") and user_id and db:
            conn = cls._get_customer_connection(user_id, db, "claude")
            if conn and conn.get_api_key():
                return AnthropicProviderAdapter(api_key=conn.get_api_key())

        elif p_pref == "gemini" and user_id and db:
            conn = cls._get_customer_connection(user_id, db, "gemini")
            if conn and conn.get_api_key():
                return GeminiProviderAdapter(api_key=conn.get_api_key())

        elif p_pref == "groq":
            groq_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
            if groq_key and groq_key.strip():
                return GroqProviderAdapter(api_key=groq_key, model=settings.GROQ_MODEL or DEFAULT_GROQ_MODEL)

        # 2. Customer-provided active external connection (scoped to user_id)
        if user_id and db:
            try:
                conn = (
                    db.query(ExternalConnection)
                    .filter(
                        ExternalConnection.user_id == user_id,
                        ExternalConnection.provider.in_(["openai", "claude", "anthropic", "gemini"]),
                        ExternalConnection.status == "CONNECTED"
                    )
                    .first()
                )
                if conn:
                    api_key = conn.get_api_key()
                    if api_key and api_key.strip():
                        p = conn.provider.lower().strip()
                        if p in ("openai", "gpt"):
                            return OpenAIProviderAdapter(api_key=api_key)
                        elif p in ("claude", "anthropic"):
                            return AnthropicProviderAdapter(api_key=api_key)
                        elif p == "gemini":
                            return GeminiProviderAdapter(api_key=api_key)
            except Exception as e:
                logger.warning(f"Error checking customer connection: {e}")

        # 3. Platform Default Groq Provider
        groq_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
        if groq_key and groq_key.strip():
            groq_model = os.environ.get("GROQ_MODEL") or settings.GROQ_MODEL or DEFAULT_GROQ_MODEL
            return GroqProviderAdapter(api_key=groq_key, model=groq_model)

        # 4. Ollama Local AI Check
        try:
            o_adapter = OllamaProviderAdapter(model=selected_model)
            o_adapter.test_connection(timeout=2.0)
            return o_adapter
        except Exception:
            pass

        # 5. Platform environment key fallbacks
        if settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY"):
            return OpenAIProviderAdapter(api_key=settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY"), model=DEFAULT_OPENAI_MODEL)
        elif settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"):
            return GeminiProviderAdapter(api_key=settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"), model=settings.GEMINI_MODEL or DEFAULT_GEMINI_MODEL)
        elif settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY"):
            return AnthropicProviderAdapter(api_key=settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY"), model=DEFAULT_ANTHROPIC_MODEL)

        return None

    @classmethod
    def _get_customer_connection(cls, user_id: str, db: Session, provider: str) -> Optional[ExternalConnection]:
        return db.query(ExternalConnection).filter(
            ExternalConnection.user_id == user_id,
            ExternalConnection.provider == provider,
            ExternalConnection.status == "CONNECTED"
        ).first()

    @classmethod
    def analyze(
        cls,
        system_instructions: str,
        user_prompt: str,
        context_data: Dict[str, Any],
        user_id: Optional[str] = None,
        db: Optional[Session] = None,
        preferred_provider: Optional[str] = None,
        timeout: float = 45.0
    ) -> Dict[str, Any]:
        """
        Executes AI analysis through the active provider.
        Catches request failures and returns structured failure metadata if selected provider errors out.
        """
        provider = cls.get_provider(user_id=user_id, db=db, preferred_provider=preferred_provider)
        if not provider:
            raise AIProviderException(
                "No AI provider is configured. Ollama is offline, Groq platform API key is missing, and no customer API key is connected.",
                status_code=503,
                code="NO_PROVIDER_AVAILABLE"
            )

        try:
            return provider.analyze(
                system_instructions=system_instructions,
                user_prompt=user_prompt,
                context_data=context_data,
                timeout=timeout
            )
        except AIProviderException as e:
            p_name = getattr(provider, "provider_name", type(provider).__name__.replace("ProviderAdapter", ""))
            logger.error(f"Provider '{p_name}' failed during analyze: {e.message}")
            raise AIProviderException(
                f"Your selected AI provider ({p_name.title()}) could not complete this request: {e.message}",
                status_code=e.status_code,
                code=e.code
            )
        except Exception as ex:
            p_name = getattr(provider, "provider_name", type(provider).__name__.replace("ProviderAdapter", ""))
            logger.error(f"Unexpected provider error from '{p_name}': {ex}")
            raise AIProviderException(
                f"Your selected AI provider ({p_name.title()}) could not complete this request. {str(ex)[:100]}",
                status_code=502,
                code="PROVIDER_FAILED"
            )
