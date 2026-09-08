"""
Cryptographic encryption and decryption service for sensitive credentials (OAuth tokens, API keys).
Uses AES-256 Fernet symmetric encryption strictly derived from the configured ENCRYPTION_KEY.
"""
import base64
import os
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

_primary_fernet: Optional[Fernet] = None

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

def reset_fernet_cache():
    """Resets cached Fernet instances (useful for testing configuration changes)."""
    global _primary_fernet
    _primary_fernet = None

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
    Decrypts ciphertext string back to plain text using ENCRYPTION_KEY.
    Raises no uncaught exceptions on malformed ciphertexts, returning None.
    """
    if not cipher_text:
        return None
    
    try:
        f = _get_primary_fernet()
        decrypted_bytes = f.decrypt(cipher_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        return None
    except Exception as e:
        return None

def migrate_legacy_encrypted_secret(cipher_text: str, old_key: str, new_key: str) -> Optional[str]:
    """
    Explicit migration utility to re-encrypt data from an old/compromised key to a new secure key.
    Does not store or hardcode any key in source code.
    """
    if not cipher_text or not old_key or not new_key:
        return None
    try:
        old_derived = base64.urlsafe_b64encode(hashlib.sha256(old_key.encode("utf-8")).digest())
        new_derived = base64.urlsafe_b64encode(hashlib.sha256(new_key.encode("utf-8")).digest())
        old_f = Fernet(old_derived)
        new_f = Fernet(new_derived)
        decrypted = old_f.decrypt(cipher_text.encode("utf-8"))
        return new_f.encrypt(decrypted).decode("utf-8")
    except Exception:
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
