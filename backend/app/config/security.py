"""
Security and password hashing utilities.
Uses bcrypt with passlib for cryptographically secure password hashing.
"""
from typing import Optional, Tuple
from passlib.context import CryptContext

# Cryptographic password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MIN_PASSWORD_LENGTH = 8

def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with automatic salt generation.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    return pwd_context.hash(password)

def verify_password(plain_password: Optional[str], hashed_password: Optional[str]) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.
    Safely returns False if either input is None/empty or if verification fails.
    Never raises unhandled exceptions on invalid or malformed hashes.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def validate_password_strength(password: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates that a password satisfies platform password policy requirements:
    - Must be at least 8 characters long
    - Must not be empty or solely whitespace
    """
    if not password or not isinstance(password, str):
        return False, "Password is required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if password.strip() != password and len(password.strip()) < MIN_PASSWORD_LENGTH:
        return False, "Password cannot begin or end with whitespace."
    return True, None
