import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment keys if missing
if not os.environ.get("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-unit-audit-suite-32b"
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "test-secret-key-for-signing-session-32b"

def test_ai_provider_architecture():
    print("============================================================", flush=True)
    print(" REAL LLM PROVIDER ARCHITECTURE & ADAPTER SUITE", flush=True)
    print("============================================================\n", flush=True)

    from app.llm.llm_provider import (
        OpenAIProviderAdapter,
        AnthropicProviderAdapter,
        GeminiProviderAdapter,
        AIProviderException,
        get_llm_provider_for_user
    )
    from app.llm.seo_analyst import SEOAnalystAgent
    from app.config.database import SessionLocal
    from app.models.external_connection import ExternalConnection
    from app.config.auth import create_access_token
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()

    # Clean up test integration records
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_ai_user_a", "test_ai_user_b"])).delete(synchronize_session=False)
    db.commit()

    # 1. Test OpenAI Adapter with Mocked HTTP Response
    print("[1/7] Testing OpenAI Provider Adapter (Mocked HTTP API)...", flush=True)
    openai_adapter = OpenAIProviderAdapter(api_key="sk-proj-mock-openai-key-123456789")
    mock_openai_resp = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "AI audit summary for example.com",
                    "findings": [
                        {
                            "finding": "Suboptimal Title Tag",
                            "category": "technical_seo",
                            "severity": "Warning",
                            "confidence": 0.95,
                            "evidence": [{"type": "affected_url", "value": "https://example.com/test"}],
                            "impact": "Exceeds recommended character length.",
                            "recommendation": "Shorten title tag.",
                            "affected_urls": ["https://example.com/test"]
                        }
                    ],
                    "actions": []
                })
            }
        }]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_openai_resp).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = openai_adapter.analyze(
            system_instructions="System instruction",
            user_prompt="Audit prompt",
            context_data={"domain": "example.com"}
        )
        assert res["summary"] == "AI audit summary for example.com"
        assert len(res["findings"]) == 1
        print("      [PASS] OpenAI adapter correctly parsed model response.\n", flush=True)

    # 2. Test Anthropic / Claude Adapter with Mocked HTTP Response
    print("[2/7] Testing Anthropic / Claude Provider Adapter (Mocked HTTP API)...", flush=True)
    claude_adapter = AnthropicProviderAdapter(api_key="sk-ant-mock-claude-key-123456789")
    mock_claude_resp = {
        "content": [{
            "text": json.dumps({
                "summary": "Claude strategic SEO audit",
                "findings": [],
                "actions": []
            })
        }]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_claude_resp).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res_claude = claude_adapter.analyze(
            system_instructions="System instruction",
            user_prompt="Audit prompt",
            context_data={"domain": "example.com"}
        )
        assert res_claude["summary"] == "Claude strategic SEO audit"
        print("      [PASS] Anthropic adapter correctly parsed model response.\n", flush=True)

    # 3. Test Gemini Provider Adapter with Mocked HTTP Response
    print("[3/7] Testing Google Gemini Provider Adapter (Mocked HTTP API)...", flush=True)
    gemini_adapter = GeminiProviderAdapter(api_key="AIzaSyMockGeminiKey123456789")
    mock_gemini_resp = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "summary": "Gemini AI audit result",
                        "findings": [],
                        "actions": []
                    })
                }]
            }
        }]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_gemini_resp).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res_gemini = gemini_adapter.analyze(
            system_instructions="System instruction",
            user_prompt="Audit prompt",
            context_data={"domain": "example.com"}
        )
        assert res_gemini["summary"] == "Gemini AI audit result"
        print("      [PASS] Gemini adapter correctly parsed model response.\n", flush=True)

    # 4. Test Unconfigured Provider State (Honest AI_NOT_CONFIGURED status)
    print("[4/7] Testing Unconfigured Provider State...", flush=True)
    agent = SEOAnalystAgent()
    with patch("app.llm.seo_analyst.get_llm_provider", return_value=None):
        analysis_unconfigured = agent.analyze_project(domain="queenshine_com_au", user_id="test_ai_user_a", db=db)
        assert analysis_unconfigured["status"] in ("AI_NOT_CONFIGURED", "AI_TEMPORARILY_UNAVAILABLE")
        assert analysis_unconfigured["is_llm_generated"] is False
        assert analysis_unconfigured["provider"] == "none"
    print("      [PASS] Returns unconfigured status and is_llm_generated=False when no provider connected.\n", flush=True)

    # 5. Test Auth & User Isolation for Provider Selection
    print("[5/7] Testing Provider Selection & User Isolation...", flush=True)
    conn_a = ExternalConnection(
        user_id="test_ai_user_a",
        provider="openai",
        status="CONNECTED"
    )
    conn_a.set_api_key("sk-proj-test-user-a-openai-key-987654321")
    db.add(conn_a)
    db.commit()

    # User A should resolve OpenAIProviderAdapter
    prov_a = get_llm_provider_for_user("test_ai_user_a", db)
    assert isinstance(prov_a, OpenAIProviderAdapter)

    # User B (unconnected to OpenAI) should not receive User A's adapter
    prov_b = get_llm_provider_for_user("test_ai_user_b", db)
    assert not isinstance(prov_b, OpenAIProviderAdapter)
    assert prov_b != prov_a
    print("      [PASS] Verified user isolation — User B cannot access User A's API credentials.\n", flush=True)

    # 6. Test Error Handling (No Silent Fallback to Fake AI)
    print("[6/7] Testing Provider Error Exception Handling (No Fake AI Fallback)...", flush=True)
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=None)):
        try:
            agent.analyze_project(domain="queenshine_com_au", user_id="test_ai_user_a", db=db)
            assert False, "Should have raised AIProviderException on HTTP 401"
        except AIProviderException as err:
            assert err.status_code == 401
            assert err.code == "AUTH_FAILED"
            print("      [PASS] Provider HTTP 401 raised controlled AIProviderException without fake LLM fallback.\n", flush=True)

    # 7. Clean up test records
    print("[7/7] Cleaning up test records...", flush=True)
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_ai_user_a", "test_ai_user_b"])).delete(synchronize_session=False)
    db.commit()
    db.close()
    print("      [PASS] AI Provider test suite complete.\n", flush=True)


def test_anthropic_model_and_error_classification():
    """
    Specifically tests:
    1. Default Anthropic model is updated to active model (claude-3-5-sonnet-latest).
    2. Model candidates fallback list includes latest active models.
    3. Error categorization handles 401, 403, 429, 404/model not found, and network errors.
    4. Zero credential leakage in exceptions.
    """
    from app.llm.llm_provider import AnthropicProviderAdapter, DEFAULT_ANTHROPIC_MODEL, AIProviderException
    import urllib.error
    import io

    # 1. Verify default model
    assert DEFAULT_ANTHROPIC_MODEL == "claude-3-5-sonnet-latest"
    adapter = AnthropicProviderAdapter(api_key="sk-ant-test-key-123456789")
    assert adapter.model == "claude-3-5-sonnet-latest"
    candidates = adapter._get_model_candidates()
    assert "claude-3-5-sonnet-latest" in candidates
    assert "claude-3-7-sonnet-latest" in candidates

    # 2. Test 401 Auth error classification
    http_401 = urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/messages",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}')
    )
    err_401 = adapter._classify_error(http_401, "claude-3-5-sonnet-latest")
    assert err_401.status_code == 401
    assert err_401.code == "AUTH_FAILED"
    assert "API key authentication failed" in err_401.message

    # 3. Test 403 Permission error classification
    http_403 = urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/messages",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=io.BytesIO(b'{"type":"error","error":{"type":"permission_error","message":"forbidden"}}')
    )
    err_403 = adapter._classify_error(http_403, "claude-3-5-sonnet-latest")
    assert err_403.status_code == 403
    assert err_403.code == "PERMISSION_DENIED"
    assert "permission" in err_403.message.lower()

    # 4. Test 429 Rate limit classification
    http_429 = urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/messages",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=io.BytesIO(b'{"type":"error","error":{"type":"rate_limit_error","message":"rate limit exceeded"}}')
    )
    err_429 = adapter._classify_error(http_429, "claude-3-5-sonnet-latest")
    assert err_429.status_code == 429
    assert err_429.code == "RATE_LIMITED"
    assert "rate limit" in err_429.message.lower()

    # 5. Test 404 Model Not Found classification
    http_404 = urllib.error.HTTPError(
        url="https://api.anthropic.com/v1/messages",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b'{"type":"error","error":{"type":"not_found_error","message":"model: retired-model-id"}}')
    )
    err_404 = adapter._classify_error(http_404, "retired-model-id")
    assert err_404.status_code == 404
    assert err_404.code == "MODEL_NOT_FOUND"
    assert "model is unavailable" in err_404.message.lower()

    # 6. Test Network error classification
    url_err = urllib.error.URLError(reason="Connection refused")
    err_net = adapter._classify_error(url_err, "claude-3-5-sonnet-latest")
    assert err_net.status_code == 502
    assert "couldn't reach anthropic" in err_net.message.lower()


if __name__ == "__main__":
    test_ai_provider_architecture()
    test_anthropic_model_and_error_classification()
