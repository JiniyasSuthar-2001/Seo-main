import os
import json
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.config.logger import get_logger
from app.services.credit_service import CreditService
from app.llm.llm_provider import (
    GroqProviderAdapter,
    GeminiProviderAdapter,
    AIProviderException
)
from app.llm.ollama_adapter import OllamaProviderAdapter

logger = get_logger(__name__)

class ProviderRoutingService:

    @classmethod
    def get_provider_adapter(cls, provider_key: str, user_id: Optional[str] = None, db: Optional[Session] = None):
        key = (provider_key or "gemini").lower()

        if key in ("gemini", "google"):
            gemini_key = os.environ.get("GEMINI_API_KEY", "")
            return GeminiProviderAdapter(api_key=gemini_key)
        elif key in ("groq", "platform"):
            groq_key = os.environ.get("GROQ_API_KEY", "")
            return GroqProviderAdapter(api_key=groq_key)
        elif key in ("ollama", "local"):
            return OllamaProviderAdapter()
        else:
            # Fallback to Gemini
            gemini_key = os.environ.get("GEMINI_API_KEY", "")
            return GeminiProviderAdapter(api_key=gemini_key)

    @classmethod
    def execute_with_routing(
        cls,
        user_id: Optional[str],
        system_instructions: str,
        user_prompt: str,
        context_data: Dict[str, Any],
        db: Session,
        timeout: float = 30.0
    ) -> Tuple[Dict[str, Any], str, str]:
        """
        Executes AI reasoning using primary provider with automatic failover to fallback provider.
        Returns: (result_dict, provider_name_used, model_name_used)
        Guarantees single execution result so credit accounting never double-charges on failover retries.
        """
        settings = CreditService.get_or_create_platform_settings(db)
        primary_key = settings.primary_provider or "gemini"
        fallback_key = settings.fallback_provider or "ollama"

        # 1. Try Primary Provider
        try:
            adapter = cls.get_provider_adapter(primary_key, user_id, db)
            res = adapter.analyze(system_instructions, user_prompt, context_data, timeout=timeout)
            if res and isinstance(res, dict):
                model_used = getattr(adapter, "model", primary_key)
                return res, primary_key, model_used
        except Exception as primary_err:
            logger.warning(f"[PROVIDER ROUTING] Primary provider ({primary_key}) failed: {primary_err}. Initiating fallback to {fallback_key}...")

        # 2. Try Fallback Provider
        try:
            fallback_adapter = cls.get_provider_adapter(fallback_key, user_id, db)
            res_fb = fallback_adapter.analyze(system_instructions, user_prompt, context_data, timeout=timeout)
            if res_fb and isinstance(res_fb, dict):
                model_used = getattr(fallback_adapter, "model", fallback_key)
                return res_fb, f"{fallback_key}_fallback", model_used
        except Exception as fallback_err:
            logger.error(f"[PROVIDER ROUTING] Fallback provider ({fallback_key}) also failed: {fallback_err}")
            raise AIProviderException(f"All configured AI providers failed. Primary: {primary_key}, Fallback: {fallback_key}.", status_code=502)
