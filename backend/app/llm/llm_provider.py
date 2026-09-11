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
DEFAULT_GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "models/gemini-flash-latest")


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
        endpoint = "https://api.openai.com/v1/chat/completions"
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
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                duration = time.time() - start_time
                logger.info(f"OpenAI API request completed successfully in {duration:.2f}s using model '{self.model}'.")
                
                content_text = resp_data["choices"][0]["message"]["content"]
                return json.loads(content_text.strip())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"OpenAI API HTTP {e.code} error: {err_body[:200]}")
            if e.code == 401:
                raise AIProviderException("Invalid OpenAI API Key provided.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("OpenAI API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"OpenAI API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise AIProviderException(f"OpenAI connection error: {e}", status_code=502, code="CONNECTION_FAILED")

    def test_connection(self, timeout: float = 15.0) -> Dict[str, Any]:
        endpoint = "https://api.openai.com/v1/models"
        req = urllib.request.Request(
            endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {
                    "status": "connected",
                    "provider": "openai",
                    "model": self.model,
                    "message": "OpenAI connection successful."
                }
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AIProviderException("OpenAI API key is invalid or unauthorized.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("OpenAI API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"OpenAI API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            raise AIProviderException(f"OpenAI connection error: {str(e)[:120]}", status_code=502, code="CONNECTION_FAILED")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        endpoint = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}
            ],
            "temperature": 0.3
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AIProviderException("Invalid OpenAI API Key.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("OpenAI API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            raise AIProviderException(f"OpenAI API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            raise AIProviderException(f"OpenAI connection error: {e}", status_code=502, code="CONNECTION_FAILED")


class AnthropicProviderAdapter(LLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        if not api_key or not api_key.strip():
            raise AIProviderException("Anthropic API Key is required.", status_code=401, code="INVALID_CREDENTIALS")
        self.api_key = api_key.strip()
        custom_model = (model or os.environ.get("ANTHROPIC_MODEL") or "").strip()
        self.model = custom_model if custom_model else DEFAULT_ANTHROPIC_MODEL

    def _get_model_candidates(self) -> List[str]:
        candidates = []
        if self.model and self.model.strip():
            candidates.append(self.model.strip())
        defaults = [
            "claude-3-5-sonnet-latest",
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20240620"
        ]
        for d in defaults:
            if d not in candidates:
                candidates.append(d)
        return candidates

    def _classify_error(self, e: Exception, target_model: str) -> AIProviderException:
        if isinstance(e, urllib.error.HTTPError):
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error(f"Anthropic API HTTP {e.code} error for model '{target_model}'")
            
            if e.code == 401:
                return AIProviderException(
                    "API key authentication failed. Check that your Anthropic API key is valid and active.",
                    status_code=401,
                    code="AUTH_FAILED"
                )
            elif e.code == 403:
                return AIProviderException(
                    "The API key does not have permission to use this resource.",
                    status_code=403,
                    code="PERMISSION_DENIED"
                )
            elif e.code == 429:
                return AIProviderException(
                    "The Anthropic rate limit has been reached. Please try again shortly.",
                    status_code=429,
                    code="RATE_LIMITED"
                )
            elif e.code in (400, 404):
                err_lower = err_body.lower()
                if "model" in err_lower or "not_found" in err_lower or "invalid_request" in err_lower:
                    return AIProviderException(
                        "The configured Anthropic model is unavailable. Please check the model configuration.",
                        status_code=404,
                        code="MODEL_NOT_FOUND"
                    )
                return AIProviderException(
                    f"Anthropic request validation failed: {err_body[:100]}",
                    status_code=400,
                    code="INVALID_REQUEST"
                )
            elif e.code in (500, 502, 503, 504):
                return AIProviderException(
                    "We couldn't reach Anthropic. Please try again.",
                    status_code=502,
                    code="PROVIDER_UNAVAILABLE"
                )
            return AIProviderException(
                f"Anthropic API error (HTTP {e.code}).",
                status_code=502,
                code="PROVIDER_ERROR"
            )
        elif isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
            logger.error(f"Anthropic network connection failed for model '{target_model}'")
            return AIProviderException(
                "We couldn't reach Anthropic. Please try again.",
                status_code=502,
                code="CONNECTION_FAILED"
            )
        else:
            logger.error(f"Anthropic unexpected error for model '{target_model}': {type(e).__name__}")
            return AIProviderException(
                "Anthropic connection verification failed. Please try again.",
                status_code=502,
                code="UNKNOWN_PROVIDER_ERROR"
            )

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": target_model,
                "max_tokens": 4096,
                "system": system_instructions,
                "messages": [
                    {"role": "user", "content": f"{user_prompt}\n\nEVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}"}
                ]
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "User-Agent": "SEO-Intelligence-Platform/1.0"
                },
                method="POST"
            )

            start_time = time.time()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    duration = time.time() - start_time
                    logger.info(f"Anthropic API request completed successfully in {duration:.2f}s using model '{target_model}'.")
                    self.model = target_model
                    
                    content_text = resp_data["content"][0]["text"]
                    return json.loads(content_text.strip())
            except Exception as e:
                classified = self._classify_error(e, target_model)
                if classified.code == "MODEL_NOT_FOUND":
                    last_exception = classified
                    continue
                raise classified

        if last_exception:
            raise last_exception
        raise AIProviderException("No compatible Anthropic model available.", status_code=404, code="NO_MODEL_AVAILABLE")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": target_model,
                "max_tokens": 2048,
                "system": system_instructions,
                "messages": [
                    {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}
                ]
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "User-Agent": "SEO-Intelligence-Platform/1.0"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    self.model = target_model
                    return resp_data["content"][0]["text"]
            except Exception as e:
                classified = self._classify_error(e, target_model)
                if classified.code == "MODEL_NOT_FOUND":
                    last_exception = classified
                    continue
                raise classified

        if last_exception:
            raise last_exception
        raise AIProviderException("No compatible Anthropic model available.", status_code=404, code="NO_MODEL_AVAILABLE")

    def test_connection(self, timeout: float = 15.0) -> Dict[str, Any]:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": target_model,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Ping"}]
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "User-Agent": "SEO-Intelligence-Platform/1.0"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    self.model = target_model
                    return {
                        "status": "connected",
                        "provider": "anthropic",
                        "model": target_model,
                        "message": f"Anthropic Claude connection successful ({target_model})."
                    }
            except Exception as e:
                classified = self._classify_error(e, target_model)
                if classified.code == "MODEL_NOT_FOUND":
                    last_exception = classified
                    continue
                raise classified

        if last_exception:
            raise last_exception
        raise AIProviderException("No compatible Anthropic model available.", status_code=404, code="NO_MODEL_AVAILABLE")


class GroqProviderAdapter(LLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        if not api_key or not api_key.strip():
            raise AIProviderException("Groq API Key is required.", status_code=401, code="INVALID_CREDENTIALS")
        self.api_key = api_key.strip()
        g_model = (model or os.environ.get("GROQ_MODEL") or "").strip()
        self.model = g_model if g_model else None

    def fetch_available_models(self, timeout: float = 8.0) -> List[Dict[str, Any]]:
        """
        Queries official Groq GET https://api.groq.com/openai/v1/models endpoint using self.api_key.
        Discovers models active for text/chat completions, excluding audio or prompt-guard models.
        """
        endpoint = "https://api.groq.com/openai/v1/models"
        req = urllib.request.Request(
            endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models_data = data.get("data", [])
                valid_models = []
                for m in models_data:
                    m_id = m.get("id", "")
                    active = m.get("active", True)
                    # Filter out whisper audio models, prompt guards, and inactive models
                    if active and m_id and not any(sub in m_id.lower() for sub in ["whisper", "prompt-guard", "safeguard"]):
                        valid_models.append({
                            "id": m_id,
                            "name": m_id,
                            "owned_by": m.get("owned_by", "Groq")
                        })
                return valid_models
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AIProviderException("Groq API key is invalid or unauthorized.", status_code=401, code="AUTH_FAILED")
            elif e.code == 429:
                raise AIProviderException("Groq API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
            logger.warning(f"Failed to query Groq models endpoint (HTTP {e.code})")
            return []
        except Exception as e:
            logger.warning(f"Error querying Groq models endpoint: {e}")
            return []

    def _get_model_candidates(self) -> List[str]:
        candidates = []

        # 1. Dynamically query Groq GET /models endpoint first for active chat models
        discovered = self.fetch_available_models()
        if discovered:
            for m in discovered:
                m_id = m["id"]
                if m_id not in candidates:
                    candidates.append(m_id)

        # 2. Add requested model if specified
        if self.model and self.model not in candidates:
            candidates.append(self.model)

        # 3. Known standard active Groq models fallback list
        fallback_defaults = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        for d in fallback_defaults:
            if d not in candidates:
                candidates.append(d)

        return candidates

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"{user_prompt}\n\nEVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}"}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "SEO-Intelligence-Platform/1.0"
                },
                method="POST"
            )

            start_time = time.time()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    duration = time.time() - start_time
                    logger.info(f"Groq API request completed successfully in {duration:.2f}s using model '{target_model}'.")
                    self.model = target_model
                    
                    content_text = resp_data["choices"][0]["message"]["content"]
                    return json.loads(content_text.strip())
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"Groq API HTTP {e.code} error for '{target_model}': {err_body[:200]}")
                if e.code == 413:
                    logger.warning(f"[GROQ 413] Payload too large for model '{target_model}'. Truncating context samples and retrying...")
                    # Truncate context payload dynamically to fit Groq limit
                    compact_context = dict(context_data)
                    compact_context["pages_sample"] = compact_context.get("pages_sample", [])[:5]
                    compact_context["issues_sample"] = compact_context.get("issues_sample", [])[:5]
                    try:
                        retry_payload = {
                            "model": target_model,
                            "messages": [
                                {"role": "system", "content": system_instructions},
                                {"role": "user", "content": f"{user_prompt}\n\nEVIDENCE CONTEXT:\n{json.dumps(compact_context, indent=2)}"}
                            ],
                            "temperature": 0.2,
                            "response_format": {"type": "json_object"}
                        }
                        retry_req = urllib.request.Request(
                            endpoint,
                            data=json.dumps(retry_payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}",
                                "User-Agent": "SEO-Intelligence-Platform/1.0"
                            },
                            method="POST"
                        )
                        with urllib.request.urlopen(retry_req, timeout=timeout) as retry_resp:
                            retry_data = json.loads(retry_resp.read().decode("utf-8"))
                            self.model = target_model
                            content_text = retry_data["choices"][0]["message"]["content"]
                            return json.loads(content_text.strip())
                    except Exception as retry_err:
                        logger.error(f"[GROQ 413 RETRY FAILED] {retry_err}")
                        last_exception = AIProviderException(f"Groq payload size exceeded model token limit (HTTP 413).", status_code=413, code="PAYLOAD_TOO_LARGE")
                        continue
                elif e.code in (400, 404):
                    last_exception = AIProviderException(f"Groq model '{target_model}' not supported.", status_code=404, code="MODEL_NOT_FOUND")
                    continue
                elif e.code in (401, 403):
                    raise AIProviderException("Groq API authentication failed.", status_code=401, code="AUTH_FAILED")
                elif e.code == 429:
                    raise AIProviderException("Groq API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
                raise AIProviderException(f"Groq API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
            except Exception as e:
                logger.error(f"Groq request failed for model '{target_model}': {e}")
                last_exception = AIProviderException(f"Groq connection error: {e}", status_code=502, code="CONNECTION_FAILED")

        if last_exception:
            raise last_exception
        raise AIProviderException("No supported Groq model available.", status_code=502, code="NO_MODEL_AVAILABLE")

    def test_connection(self, timeout: float = 15.0) -> Dict[str, Any]:
        available_models = self.fetch_available_models(timeout=min(timeout, 8.0))
        candidates = []
        if self.model:
            candidates.append(self.model)
        if available_models:
            for m in available_models:
                if m["id"] not in candidates:
                    candidates.append(m["id"])
        else:
            candidates.extend(self._get_model_candidates())

        last_exception = None

        for target_model in candidates:
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": target_model,
                "messages": [
                    {"role": "user", "content": "Respond with: Groq connection working."}
                ],
                "max_tokens": 30
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "SEO-Intelligence-Platform/1.0"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    text = resp_data["choices"][0]["message"].get("content", "").strip()
                    if not text:
                        text = "Groq connection successful."
                    self.model = target_model
                    return {
                        "status": "connected",
                        "provider": "groq",
                        "model": target_model,
                        "available_models": available_models,
                        "message": f"Groq AI connection successful ({target_model})."
                    }
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"Groq test HTTP {e.code} error for '{target_model}': {err_body[:200]}")
                if e.code in (400, 404):
                    last_exception = AIProviderException(f"Groq model '{target_model}' not found or unavailable.", status_code=404, code="MODEL_NOT_FOUND")
                    continue
                elif e.code in (401, 403):
                    raise AIProviderException("Groq API key is invalid or unauthorized.", status_code=401, code="AUTH_FAILED")
                elif e.code == 429:
                    raise AIProviderException("Groq API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
                raise AIProviderException(f"Groq API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
            except Exception as e:
                logger.error(f"Groq test connection failed for '{target_model}': {e}")
                last_exception = AIProviderException(f"Groq connection error: {str(e)[:120]}", status_code=502, code="CONNECTION_FAILED")

        if last_exception:
            raise last_exception
        raise AIProviderException("No compatible Groq text model available for your API key.", status_code=404, code="NO_MODEL_AVAILABLE")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}
                ]
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "SEO-Intelligence-Platform/1.0"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    self.model = target_model
                    return resp_data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"Groq chat HTTP {e.code} error for '{target_model}': {err_body[:200]}")
                if e.code == 413:
                    logger.warning(f"[GROQ CHAT 413] Payload too large for model '{target_model}'. Truncating context samples and retrying...")
                    compact_context = dict(context_data)
                    compact_context["pages_sample"] = compact_context.get("pages_sample", [])[:5]
                    compact_context["issues_sample"] = compact_context.get("issues_sample", [])[:5]
                    try:
                        retry_payload = {
                            "model": target_model,
                            "messages": [
                                {"role": "system", "content": system_instructions},
                                {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(compact_context, indent=2)}\n\nUSER QUESTION: {query}"}
                            ]
                        }
                        retry_req = urllib.request.Request(
                            endpoint,
                            data=json.dumps(retry_payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}",
                                "User-Agent": "SEO-Intelligence-Platform/1.0"
                            },
                            method="POST"
                        )
                        with urllib.request.urlopen(retry_req, timeout=timeout) as retry_resp:
                            retry_data = json.loads(retry_resp.read().decode("utf-8"))
                            self.model = target_model
                            return retry_data["choices"][0]["message"]["content"]
                    except Exception as retry_err:
                        logger.error(f"[GROQ CHAT 413 RETRY FAILED] {retry_err}")
                        last_exception = AIProviderException(f"Groq payload size exceeded model token limit (HTTP 413).", status_code=413, code="PAYLOAD_TOO_LARGE")
                        continue
                elif e.code in (400, 404):
                    last_exception = AIProviderException(f"Groq model '{target_model}' not supported.", status_code=404, code="MODEL_NOT_FOUND")
                    continue
                elif e.code in (401, 403):
                    raise AIProviderException("Groq API authentication failed.", status_code=401, code="AUTH_FAILED")
                elif e.code == 429:
                    raise AIProviderException("Groq API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
                raise AIProviderException(f"Groq API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
            except Exception as e:
                last_exception = AIProviderException(f"Groq connection error: {e}", status_code=502, code="CONNECTION_FAILED")

        if last_exception:
            raise last_exception
        raise AIProviderException("No supported Groq model available.", status_code=502, code="NO_MODEL_AVAILABLE")


class GeminiProviderAdapter(LLMProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL):
        if not api_key or not api_key.strip():
            raise AIProviderException("Gemini API Key is required.", status_code=401, code="INVALID_CREDENTIALS")
        self.api_key = api_key.strip()
        self.model = model

    def _get_model_candidates(self) -> List[str]:
        candidates = []
        if self.model:
            m = self.model.strip()
            if not m.startswith("models/"):
                candidates.append(f"models/{m}")
            candidates.append(m)

        defaults = [
            "models/gemini-2.5-flash",
            "models/gemini-flash-latest",
            "models/gemini-2.5-pro",
            "models/gemini-pro-latest",
            "models/gemini-1.5-flash"
        ]
        for d in defaults:
            if d not in candidates:
                candidates.append(d)
        return candidates

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
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
                    logger.info(f"Gemini API request completed successfully in {duration:.2f}s using model '{target_model}'.")
                    self.model = target_model
                    
                    content_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(content_text.strip())
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"Gemini API HTTP {e.code} error for '{target_model}': {err_body[:200]}")
                if e.code == 404:
                    last_exception = AIProviderException(f"Gemini model '{target_model}' is not available.", status_code=404, code="MODEL_NOT_FOUND")
                    continue
                elif e.code in (400, 401, 403):
                    raise AIProviderException("Google Gemini API authentication failed.", status_code=401, code="AUTH_FAILED")
                elif e.code == 429:
                    raise AIProviderException("Google Gemini API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
                raise AIProviderException(f"Google Gemini API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
            except Exception as e:
                logger.error(f"Gemini request failed for '{target_model}': {e}")
                last_exception = AIProviderException(f"Gemini connection error: {e}", status_code=502, code="CONNECTION_FAILED")

        if last_exception:
            raise last_exception
        raise AIProviderException("No supported Gemini model available.", status_code=502, code="NO_MODEL_AVAILABLE")

    def test_connection(self, timeout: float = 15.0) -> Dict[str, Any]:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": "Respond with exactly: Gemini connection successful."}]
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
                    text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    self.model = target_model
                    return {
                        "status": "connected",
                        "provider": "gemini",
                        "model": target_model,
                        "message": text
                    }
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error(f"Gemini test HTTP {e.code} error for '{target_model}': {err_body[:200]}")
                if e.code == 404:
                    last_exception = AIProviderException(f"Gemini model '{target_model}' is not available.", status_code=404, code="MODEL_NOT_FOUND")
                    continue
                elif e.code in (400, 401, 403):
                    raise AIProviderException("Gemini API key is invalid or unauthorized.", status_code=401, code="AUTH_FAILED")
                elif e.code == 429:
                    raise AIProviderException("Gemini API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
                raise AIProviderException(f"Gemini API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
            except Exception as e:
                logger.error(f"Gemini test connection failed for '{target_model}': {e}")
                last_exception = AIProviderException(f"Gemini connection error: {str(e)[:120]}", status_code=502, code="CONNECTION_FAILED")

        if last_exception:
            raise last_exception
        raise AIProviderException("No supported Gemini model available.", status_code=502, code="NO_MODEL_AVAILABLE")

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> str:
        candidates = self._get_model_candidates()
        last_exception = None

        for target_model in candidates:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={self.api_key}"
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
                    self.model = target_model
                    return resp_data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    last_exception = AIProviderException(f"Gemini model '{target_model}' is not available.", status_code=404, code="MODEL_NOT_FOUND")
                    continue
                elif e.code in (400, 401, 403):
                    raise AIProviderException("Gemini API authentication failed.", status_code=401, code="AUTH_FAILED")
                elif e.code == 429:
                    raise AIProviderException("Gemini API rate limit exceeded.", status_code=429, code="RATE_LIMITED")
                raise AIProviderException(f"Gemini API error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
            except Exception as e:
                last_exception = AIProviderException(f"Gemini connection error: {e}", status_code=502, code="CONNECTION_FAILED")

        if last_exception:
            raise last_exception
        raise AIProviderException("No supported Gemini model available.", status_code=502, code="NO_MODEL_AVAILABLE")


def get_llm_provider_for_user(user_id: Optional[str] = None, db: Optional[Session] = None, preferred_provider: Optional[str] = None) -> Optional[LLMProvider]:
    """
    Retrieves and instantiates the active LLM Provider adapter via central AIService.
    Routes to preferred provider if configured, or falls back across Customer AI -> Groq -> Ollama.
    """
    from app.llm.ai_service import AIService
    return AIService.get_provider(user_id=user_id, db=db, preferred_provider=preferred_provider)
