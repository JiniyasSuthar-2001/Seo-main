import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from app.config.logger import get_logger
from app.llm.llm_provider import LLMProvider, AIProviderException

logger = get_logger(__name__)

DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")


class OllamaProviderAdapter(LLMProvider):
    provider_name = "ollama"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        url = base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL
        self.base_url = url.rstrip("/")
        self.model = (model or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip()

    def get_installed_models(self, timeout: float = 1.5) -> List[Dict[str, Any]]:
        """Queries local Ollama /api/tags endpoint to discover installed models."""
        endpoint = f"{self.base_url}/api/tags"
        req = urllib.request.Request(endpoint, headers={"User-Agent": "SEO-Intelligence-Platform/1.0"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                result = []
                for m in models:
                    name = m.get("name", m.get("model", ""))
                    if name:
                        size_mb = round(m.get("size", 0) / (1024 * 1024), 1)
                        fit_eval = self.evaluate_hardware_fit(name)
                        result.append({
                            "name": name,
                            "size_mb": size_mb,
                            "modified_at": m.get("modified_at"),
                            "hardware_fit": fit_eval["fit"],
                            "hardware_badge": fit_eval["badge"],
                            "recommended": fit_eval["recommended"]
                        })
                return result
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama installed models from {endpoint}: {e}")
            return []

    def evaluate_hardware_fit(self, model_name: str) -> Dict[str, Any]:
        """Evaluates model hardware compatibility for 8GB RAM / NVIDIA MX110."""
        name_lower = (model_name or "").lower()
        optimal_patterns = ["1b", "2b", "3b", "4b", "mini", "tiny", "micro", "small", "0.5b"]
        
        is_optimal = any(pat in name_lower for pat in optimal_patterns)
        
        if is_optimal:
            return {
                "fit": "OPTIMAL",
                "badge": "Suitable for this computer",
                "detail": "1B–4B models run efficiently within 8GB RAM / MX110 GPU footprint.",
                "recommended": True
            }
        else:
            return {
                "fit": "WARNING",
                "badge": "Large Model Warning",
                "detail": "Model size exceeds recommended 1B–4B range for 8GB RAM / MX110. Inference may be slow or use swap RAM.",
                "recommended": False
            }

    def test_connection(self, timeout: float = 1.0) -> Dict[str, Any]:
        """Tests whether local Ollama service is reachable and retrieves models."""
        models = self.get_installed_models(timeout=timeout)
        if not models:
            raise AIProviderException(
                "Ollama is not running on this device. Install and start Ollama to use local AI.",
                status_code=503,
                code="OLLAMA_OFFLINE"
            )

        selected_model_name = self.model
        if not any(m["name"] == selected_model_name for m in models) and models:
            selected_model_name = models[0]["name"]
            self.model = selected_model_name

        fit_eval = self.evaluate_hardware_fit(selected_model_name)
        return {
            "status": "connected",
            "provider": "ollama",
            "base_url": self.base_url,
            "selected_model": selected_model_name,
            "installed_models": models,
            "hardware_fit": fit_eval["fit"],
            "hardware_badge": fit_eval["badge"],
            "hardware_detail": fit_eval["detail"],
            "message": f"Ollama local AI connected on {self.base_url} with {len(models)} model(s)."
        }

    def analyze(
        self, 
        system_instructions: str, 
        user_prompt: str, 
        context_data: Dict[str, Any], 
        timeout: float = 45.0
    ) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/api/generate"
        prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system_instructions}\n\n"
            f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\n"
            f"USER PROMPT:\n{user_prompt}\n\n"
            f"Respond strictly in valid JSON format matching the requested structure."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
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
                logger.info(f"Ollama API request completed in {duration:.2f}s using model '{self.model}'.")
                
                response_text = resp_data.get("response", "").strip()
                return json.loads(response_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Ollama API HTTP {e.code} error: {err_body[:200]}")
            if e.code == 404:
                raise AIProviderException(f"Ollama model '{self.model}' is not installed.", status_code=404, code="MODEL_NOT_FOUND")
            raise AIProviderException(f"Ollama local error (HTTP {e.code}).", status_code=502, code="PROVIDER_ERROR")
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise AIProviderException(
                "Ollama is not running on this device. Install and start Ollama to use local AI.",
                status_code=503,
                code="OLLAMA_OFFLINE"
            )

    def chat(
        self, 
        system_instructions: str, 
        query: str, 
        context_data: Dict[str, Any], 
        timeout: float = 45.0
    ) -> str:
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": f"EVIDENCE CONTEXT:\n{json.dumps(context_data, indent=2)}\n\nUSER QUESTION: {query}"}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3
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

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise AIProviderException(
                "Ollama is not running on this device. Install and start Ollama to use local AI.",
                status_code=503,
                code="OLLAMA_OFFLINE"
            )
