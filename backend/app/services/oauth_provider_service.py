import os
import secrets
import hmac
import hashlib
import time
import json
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional
from app.config.settings import settings


def get_oauth_state_secret() -> str:
    """
    Returns configured OAUTH_STATE_SECRET or SECRET_KEY environment variable.
    Raises ValueError if neither secret is configured.
    """
    secret = os.environ.get("OAUTH_STATE_SECRET") or os.environ.get("SECRET_KEY")
    if not secret or not secret.strip():
        raise ValueError(
            "OAuth configuration error: Missing required 'OAUTH_STATE_SECRET' or 'SECRET_KEY' environment variable. "
            "Configure OAUTH_STATE_SECRET in your .env or server environment to enable secure OAuth state signing."
        )
    return secret.strip()

def generate_oauth_state(user_id: str, provider: str, extra_params: Optional[dict] = None) -> str:
    """
    Generates a cryptographically signed OAuth state token to prevent CSRF / session injection attacks.
    Payload format: user_id|provider|timestamp|nonce|extra_str|signature
    """
    hmac_secret = get_oauth_state_secret()
    nonce = secrets.token_hex(8)
    timestamp = int(time.time())
    extra_str = json.dumps(extra_params or {})
    raw_payload = f"{user_id}|{provider}|{timestamp}|{nonce}|{extra_str}"
    
    signature = hmac.new(hmac_secret.encode("utf-8"), raw_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    signed_state = urllib.parse.quote(f"{raw_payload}|{signature}")
    return signed_state

def validate_oauth_state(state: str) -> dict:
    """
    Validates a signed OAuth state token. Ensures signature matches and token is unexpired (< 1 hour).
    Raises ValueError if invalid, tampered, or expired.
    """
    if not state:
        raise ValueError("OAuth state parameter is missing.")

    hmac_secret = get_oauth_state_secret()

    try:
        unquoted = urllib.parse.unquote(state)
        parts = unquoted.split("|")
        if len(parts) != 6:
            raise ValueError("Malformed state format.")

        user_id, provider, timestamp_str, nonce, extra_str, signature = parts
        
        raw_payload = f"{user_id}|{provider}|{timestamp_str}|{nonce}|{extra_str}"
        expected_sig = hmac.new(hmac_secret.encode("utf-8"), raw_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("State signature verification failed (possible CSRF attack).")

        timestamp = int(timestamp_str)
        if time.time() - timestamp > 3600:  # 1 hour expiration
            raise ValueError("OAuth state token has expired.")

        return {
            "user_id": user_id,
            "provider": provider,
            "nonce": nonce,
            "extra": json.loads(extra_str) if extra_str else {}
        }
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid OAuth state: {e}")


class OAuthProviderConfig:
    """
    Registry of provider OAuth endpoints, client IDs, secrets, default scopes, and redirect URIs.
    """
    
    @staticmethod
    def get_provider_details(provider: str, redirect_base: Optional[str] = None) -> dict:
        base_url = redirect_base or settings.API_BASE_URL
        p = provider.lower()
        callback_url = f"{base_url}/api/integrations/{p}/callback"

        
        if p == "google":
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
            return {
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "revoke_url": "https://oauth2.googleapis.com/revoke",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": "https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/webmasters.readonly https://www.googleapis.com/auth/business.manage",
                "redirect_uri": callback_url
            }

        elif p in ("meta", "facebook", "instagram"):
            client_id = os.environ.get("META_APP_ID") or os.environ.get("FACEBOOK_CLIENT_ID", "")
            client_secret = os.environ.get("META_APP_SECRET") or os.environ.get("FACEBOOK_CLIENT_SECRET", "")
            return {
                "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
                "userinfo_url": "https://graph.facebook.com/v18.0/me?fields=id,name,email",
                "pages_url": "https://graph.facebook.com/v18.0/me/accounts?fields=id,name,access_token,category,instagram_business_account",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": "public_profile,email,pages_show_list,pages_read_engagement,instagram_basic",
                "redirect_uri": callback_url
            }

        elif p == "microsoft":
            client_id = os.environ.get("MICROSOFT_CLIENT_ID", "")
            client_secret = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
            return {
                "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                "userinfo_url": "https://graph.microsoft.com/v1.0/me",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": "User.Read offline_access",
                "redirect_uri": callback_url
            }

        elif p == "linkedin":
            client_id = os.environ.get("LINKEDIN_CLIENT_ID", "")
            client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
            return {
                "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                "userinfo_url": "https://api.linkedin.com/v2/userinfo",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": "openid profile email",
                "redirect_uri": callback_url
            }

        elif p in ("twitter", "x"):
            client_id = os.environ.get("TWITTER_CLIENT_ID") or os.environ.get("X_CLIENT_ID", "")
            client_secret = os.environ.get("TWITTER_CLIENT_SECRET") or os.environ.get("X_CLIENT_SECRET", "")
            return {
                "auth_url": "https://twitter.com/i/oauth2/authorize",
                "token_url": "https://api.twitter.com/2/oauth2/token",
                "userinfo_url": "https://api.twitter.com/2/users/me",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": "tweet.read users.read offline.access",
                "redirect_uri": callback_url
            }

        else:
            raise ValueError(f"Unsupported OAuth provider: '{provider}'")


def build_authorization_url(provider: str, user_id: str, redirect_base: Optional[str] = None) -> str:
    """
    Constructs official OAuth 2.0 login URL for the given provider.
    """
    base_url = redirect_base or settings.API_BASE_URL
    config = OAuthProviderConfig.get_provider_details(provider, base_url)

    if not config["client_id"]:
        raise ValueError(f"{provider.title()} client ID is not configured in backend environment.")

    state = generate_oauth_state(user_id, provider)

    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scopes"],
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }

    url_parts = list(urllib.parse.urlparse(config["auth_url"]))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)

    return urllib.parse.urlunparse(url_parts)


def validate_api_key_provider(provider: str, api_key: str) -> dict:
    """
    Validates user-provided API key for AI key providers (OpenAI, Gemini, Claude).
    Performs live HTTP verification against provider endpoint.
    No substring bypasses are permitted in production code.
    """
    p = provider.lower()
    clean_key = api_key.strip()
    if not clean_key:
        raise ValueError("API key cannot be empty.")

    if p == "openai":
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {clean_key}", "User-Agent": "SEO-Intelligence-Platform/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return {
                        "provider": "openai",
                        "account_name": "OpenAI User Account",
                        "email": "api-key-authenticated@openai.com",
                        "account_id": "openai_user_key"
                    }
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise ValueError("Invalid OpenAI API Key. Authentication failed (HTTP 401).")
            elif e.code == 429:
                return {
                    "provider": "openai",
                    "account_name": "OpenAI User Account (Rate Limited)",
                    "email": "api-key-rate-limited@openai.com",
                    "account_id": "openai_user_key"
                }
            raise ValueError(f"OpenAI validation failed: HTTP {e.code}")
        except Exception as e:
            raise ValueError(f"OpenAI connection error: {e}")

    elif p == "gemini":
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
        req = urllib.request.Request(endpoint, headers={"User-Agent": "SEO-Intelligence-Platform/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return {
                        "provider": "gemini",
                        "account_name": "Google Gemini User Account",
                        "email": "api-key-authenticated@gemini.google.com",
                        "account_id": "gemini_user_key"
                    }
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                raise ValueError("Invalid Google Gemini API Key. Authentication failed.")
            raise ValueError(f"Gemini validation failed: HTTP {e.code}")
        except Exception as e:
            raise ValueError(f"Gemini connection error: {e}")

    elif p in ("claude", "anthropic"):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": clean_key,
                "anthropic-version": "2023-06-01",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return {
                        "provider": "claude",
                        "account_name": "Claude AI (Anthropic) User Account",
                        "email": "api-key-authenticated@anthropic.com",
                        "account_id": "claude_user_key"
                    }
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ValueError("Invalid Claude AI / Anthropic API Key. Authentication failed (HTTP 401/403).")
            elif e.code == 429:
                return {
                    "provider": "claude",
                    "account_name": "Claude AI (Rate Limited)",
                    "email": "api-key-rate-limited@anthropic.com",
                    "account_id": "claude_user_key"
                }
            raise ValueError(f"Claude AI validation failed: HTTP {e.code}")
        except Exception as e:
            raise ValueError(f"Claude AI connection error: {e}")

    raise ValueError(f"Unsupported API Key provider: '{provider}'")


def exchange_code_for_tokens(provider: str, code: str, redirect_base: Optional[str] = None) -> dict:
    """
    Exchanges authorization code for access and refresh tokens with official provider endpoint.
    Raises ValueError if client ID/secret are unconfigured or if token exchange fails.
    """
    base_url = redirect_base or settings.API_BASE_URL
    p = provider.lower()
    config = OAuthProviderConfig.get_provider_details(p, base_url)

    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")

    if not client_id or not client_secret:
        raise ValueError(
            f"{provider.title()} OAuth credentials are not configured in backend environment. "
            f"Please configure {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET in backend/.env."
        )

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": config["redirect_uri"]
    }

    try:
        req_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            config["token_url"],
            data=req_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            resp_body = resp.read().decode("utf-8")
            token_json = json.loads(resp_body)
            if "access_token" not in token_json:
                raise ValueError(f"Provider response did not include access_token: {resp_body[:100]}")
            return token_json
    except urllib.error.HTTPError as e:
        err_text = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err_text)
            err_msg = parsed.get("error_description") or parsed.get("error") or err_text
        except Exception:
            err_msg = err_text
        raise ValueError(f"Token exchange failed with {provider.title()} (HTTP {e.code}): {err_msg}")
    except Exception as e:
        raise ValueError(f"Failed to connect to {provider.title()} token endpoint: {e}")


def fetch_provider_user_profile(provider: str, access_token: str) -> dict:
    """
    Retrieves authentic user profile and account details from provider using verified access token.
    Raises ValueError if provider API call fails.
    """
    p = provider.lower()
    config = OAuthProviderConfig.get_provider_details(p)
    userinfo_url = config.get("userinfo_url")

    if not userinfo_url:
        raise ValueError(f"Userinfo endpoint URL not configured for provider '{provider}'.")

    try:
        req = urllib.request.Request(
            userinfo_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": "SEO-Intelligence-Platform/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            info = json.loads(resp.read().decode("utf-8"))

        account_id = str(info.get("sub") or info.get("id") or f"{p}_user")
        account_name = info.get("name") or info.get("displayName") or info.get("username") or f"{p.title()} User Account"
        account_email = info.get("email") or info.get("userPrincipalName") or ""

        metadata = {}
        if p in ("meta", "facebook", "instagram"):
            pages_url = config.get("pages_url")
            if pages_url:
                try:
                    p_req = urllib.request.Request(
                        pages_url,
                        headers={"Authorization": f"Bearer {access_token}", "User-Agent": "SEO-Intelligence-Platform/1.0"}
                    )
                    with urllib.request.urlopen(p_req, timeout=10) as p_resp:
                        p_info = json.loads(p_resp.read().decode("utf-8"))
                        metadata["facebook_pages"] = p_info.get("data", [])
                except Exception:
                    metadata["facebook_pages"] = []

        return {
            "account_id": account_id,
            "account_name": account_name,
            "email": account_email,
            "metadata": metadata
        }
    except urllib.error.HTTPError as e:
        raise ValueError(f"Failed to retrieve user identity from {p.title()} (HTTP {e.code}).")
    except Exception as e:
        raise ValueError(f"Failed to query {p.title()} user profile: {e}")
