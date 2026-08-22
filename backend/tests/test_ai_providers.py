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
    analysis_unconfigured = agent.analyze_project(domain="queenshine_com_au", user_id="test_ai_user_a", db=db)
    assert analysis_unconfigured["status"] == "AI_NOT_CONFIGURED"
    assert analysis_unconfigured["is_llm_generated"] is False
    assert analysis_unconfigured["provider"] == "none"
    print("      [PASS] Returns status 'AI_NOT_CONFIGURED' and is_llm_generated=False when no provider connected.\n", flush=True)

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

    # User B (unconnected) should resolve None
    prov_b = get_llm_provider_for_user("test_ai_user_b", db)
    assert prov_b is None
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


if __name__ == "__main__":
    test_ai_provider_architecture()
