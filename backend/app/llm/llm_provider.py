import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.external_connection import ExternalConnection
from app.config.logger import get_logger

logger = get_logger(__name__)

# Default Provider Model Configurations
DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")


class AIProviderException(Exception):
    def __init__(self, message: str, status_code: int = 500, code: str = "AI_PROVIDER_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class LLMProvider(ABC):
    @abstractmethod
    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Performs structured evidence-based AI analysis."""
        pass

    @abstractmethod
    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        """Performs conversational AI response generation."""
        pass


class OpenAIProviderAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_OPENAI_MODEL):
        if not api_key or not api_key.strip():
            raise AIProviderException("OpenAI API Key is required.", status_code=401, code="INVALID_CREDENTIALS")
        self.api_key = api_key.strip()
        self.model = model

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": f"{user_prompt}\n\nEVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}"}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                duration = time.time() - start_time
                logger.info(f"OpenAI API request completed successfully in {duration:.2f}s using model '{self.model}'.")
                
                content_str = resp_data["choices"][0]["message"]["content"]
                parsed_json = json.loads(content_str)
                return parsed_json
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"OpenAI API HTTP {e.code} error: {err_body[:200]}")
            if e.code in (401, 403):
                raise AIProviderException("OpenAI API authentication failed. Please verify your API Key.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("OpenAI API rate limit or quota exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"OpenAI API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise AIProviderException(f"OpenAI connection error: {e}", status_code=502, code="CONNECTION_FAILED")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}
            ],
            "temperature": 0.3
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AIProviderException("OpenAI API authentication failed.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("OpenAI API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"OpenAI API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            raise AIProviderException(f"OpenAI connection error: {e}", status_code=502, code="CONNECTION_FAILED")


class AnthropicProviderAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_ANTHROPIC_MODEL):
        if not api_key or not api_key.strip():
            raise AIProviderException("Anthropic API Key is required.", status_code=401, code="INVALID_CREDENTIALS")
        self.api_key = api_key.strip()
        self.model = model

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": 3000,
            "system": f"{system_instructions}\nIMPORTANT: Respond ONLY with valid JSON.",
            "messages": [
                {"role": "user", "content": f"{user_prompt}\n\nEVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}"}
            ]
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                duration = time.time() - start_time
                logger.info(f"Claude API request completed successfully in {duration:.2f}s using model '{self.model}'.")
                
                content_text = resp_data["content"][0]["text"]
                # Clean code blocks if present
                if "```json" in content_text:
                    content_text = content_text.split("```json")[1].split("```")[0].strip()
                elif "```" in content_text:
                    content_text = content_text.split("```")[1].split("```")[0].strip()

                return json.loads(content_text.strip())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Claude API HTTP {e.code} error: {err_body[:200]}")
            if e.code in (401, 403):
                raise AIProviderException("Claude AI / Anthropic API authentication failed.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("Claude AI / Anthropic API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"Claude AI API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            logger.error(f"Claude request failed: {e}")
            raise AIProviderException(f"Claude connection error: {e}", status_code=502, code="CONNECTION_FAILED")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "system": system_instructions,
            "messages": [
                {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}
            ]
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AIProviderException("Claude API authentication failed.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("Claude API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"Claude API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            raise AIProviderException(f"Claude connection error: {e}", status_code=502, code="CONNECTION_FAILED")


class GeminiProviderAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL):
        if not api_key or not api_key.strip():
            raise AIProviderException("Gemini API Key is required.", status_code=401, code="INVALID_CREDENTIALS")
        self.api_key = api_key.strip()
        self.model = model

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "system_instruction": {"parts": [{"text": system_instructions}]},
            "contents": [{
                "parts": [{"text": f"{user_prompt}\n\nEVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}"}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                duration = time.time() - start_time
                logger.info(f"Gemini API request completed successfully in {duration:.2f}s using model '{self.model}'.")
                
                content_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(content_text.strip())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Gemini API HTTP {e.code} error: {err_body[:200]}")
            if e.code in (400, 401, 403):
                raise AIProviderException("Google Gemini API authentication failed.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("Google Gemini API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"Google Gemini API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            raise AIProviderException(f"Gemini connection error: {e}", status_code=502, code="CONNECTION_FAILED")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "system_instruction": {"parts": [{"text": system_instructions}]},
            "contents": [{
                "parts": [{"text": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}]
            }]
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                raise AIProviderException("Gemini API authentication failed.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("Gemini API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"Gemini API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            raise AIProviderException(f"Gemini connection error: {e}", status_code=502, code="CONNECTION_FAILED")


def get_llm_provider_for_user(user_id: str, db: Session) -> Optional[LLMProvider]:
    """
    Retrieves and instantiates the active LLM Provider adapter for the authenticated user.
    Checks external connections in priority order: openai -> claude / anthropic -> gemini.
    Decrypts credential securely at call time. Returns None if no AI connection is active.
    """
    ai_providers = ["openai", "claude", "anthropic", "gemini"]
    conn = (
        db.query(ExternalConnection)
        .filter(
            ExternalConnection.user_id == user_id,
            ExternalConnection.provider.in_(ai_providers),
            ExternalConnection.status == "CONNECTED"
        )
        .first()
    )

    if not conn:
        return None

    api_key = conn.get_api_key()
    if not api_key:
        return None

    p = conn.provider.lower()
    if p == "openai":
        return OpenAIProviderAdapter(api_key=api_key)
    elif p in ("claude", "anthropic"):
        return AnthropicProviderAdapter(api_key=api_key)
    elif p == "gemini":
        return GeminiProviderAdapter(api_key=api_key)

    return None
