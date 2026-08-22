import base64
import os
import hashlib
from typing import Optional
from cryptography.fernet import Fernet

_fernet_instance: Optional[Fernet] = None

def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        raw_key = os.environ.get("ENCRYPTION_KEY") or os.environ.get("SECRET_KEY") or "seo-platform-secure-default-encryption-secret-key-32b"
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        _fernet_instance = Fernet(derived_key)
    return _fernet_instance

def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    """
    Encrypts a sensitive string (token, API key) using Fernet AES-256.
    Returns URL-safe ciphertext string.
    """
    if not plain_text:
        return None
    try:
        f = _get_fernet()
        encrypted_bytes = f.encrypt(plain_text.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"[CRYPTO ERROR] Failed to encrypt secret: {e}", flush=True)
        return None

def decrypt_secret(cipher_text: Optional[str]) -> Optional[str]:
    """
    Decrypts ciphertext string back to plain text.
    """
    if not cipher_text:
        return None
    try:
        f = _get_fernet()
        decrypted_bytes = f.decrypt(cipher_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"[CRYPTO ERROR] Failed to decrypt secret: {e}", flush=True)
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
