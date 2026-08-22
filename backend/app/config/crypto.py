import base64
import os
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

_primary_fernet: Optional[Fernet] = None
_legacy_fernet: Optional[Fernet] = None

# Purpose Documentation:
# SECRET_KEY    = Used strictly for application session/JWT/HMAC state signing.
# ENCRYPTION_KEY = Used strictly for AES-256 Fernet encryption of stored OAuth tokens, API keys, and provider credentials.

LEGACY_FALLBACK_SECRET = "seo-platform-secure-default-encryption-secret-key-32b"

def get_encryption_key() -> str:
    """
    Returns configured ENCRYPTION_KEY environment variable.
    Raises RuntimeError if ENCRYPTION_KEY is missing or empty.
    """
    key = os.environ.get("ENCRYPTION_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "CONFIGURATION ERROR: Missing required 'ENCRYPTION_KEY' environment variable. "
            "ENCRYPTION_KEY is required to encrypt and decrypt stored OAuth tokens and API keys. "
            "Please configure ENCRYPTION_KEY in your .env or server environment."
        )
    return key.strip()

def _get_primary_fernet() -> Fernet:
    global _primary_fernet
    if _primary_fernet is None:
        raw_key = get_encryption_key()
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        _primary_fernet = Fernet(derived_key)
    return _primary_fernet

def _get_legacy_fernet() -> Fernet:
    global _legacy_fernet
    if _legacy_fernet is None:
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(LEGACY_FALLBACK_SECRET.encode("utf-8")).digest())
        _legacy_fernet = Fernet(derived_key)
    return _legacy_fernet

def reset_fernet_cache():
    """Resets cached Fernet instances (useful for testing configuration changes)."""
    global _primary_fernet, _legacy_fernet
    _primary_fernet = None
    _legacy_fernet = None

def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    """
    Encrypts a sensitive string (token, API key) using Fernet AES-256 derived strictly from ENCRYPTION_KEY.
    Returns URL-safe ciphertext string.
    """
    if not plain_text:
        return None
    f = _get_primary_fernet()
    encrypted_bytes = f.encrypt(plain_text.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_secret(cipher_text: Optional[str]) -> Optional[str]:
    """
    Decrypts ciphertext string back to plain text.
    First attempts primary decryption using ENCRYPTION_KEY.
    If decryption fails, falls back to legacy fallback key for reading pre-existing database credentials.
    """
    if not cipher_text:
        return None
    
    # 1. Primary Decryption Attempt
    try:
        f = _get_primary_fernet()
        decrypted_bytes = f.decrypt(cipher_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        # 2. Legacy Read Fallback Attempt for backward compatibility
        try:
            lf = _get_legacy_fernet()
            decrypted_bytes = lf.decrypt(cipher_text.encode("utf-8"))
            print("[CRYPTO RECOVERY] Decrypted stored credential using legacy key. Consider re-saving.", flush=True)
            return decrypted_bytes.decode("utf-8")
        except Exception:
            print("[CRYPTO ERROR] Failed to decrypt secret with primary or legacy key.", flush=True)
            return None
    except Exception as e:
        print(f"[CRYPTO ERROR] Unexpected decryption failure: {e}", flush=True)
        return None

def mask_secret(plain_text: Optional[str], prefix_len: int = 3, suffix_len: int = 4) -> str:
    """
    Masks a sensitive string for safe UI presentation (e.g. 'sk-••••••••3a9c').
    """
    if not plain_text:
        return ""
    clean = plain_text.strip()
    if len(clean) <= prefix_len + suffix_len:
        return "••••••••"
    prefix = clean[:prefix_len]
    suffix = clean[-suffix_len:]
    return f"{prefix}••••••••{suffix}"
