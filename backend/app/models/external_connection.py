from sqlalchemy import Column, String, DateTime, Text, UniqueConstraint
from datetime import datetime
import uuid
import json
from app.config.database import Base
from app.config.crypto import encrypt_secret, decrypt_secret, mask_secret

class ExternalConnection(Base):
    __tablename__ = "external_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, index=True, nullable=False)
    provider = Column(String, index=True, nullable=False)
    provider_account_id = Column(String, index=True, nullable=True)
    provider_account_name = Column(String, nullable=True)
    provider_email = Column(String, nullable=True)
    
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    
    token_expires_at = Column(DateTime, nullable=True)
    scopes = Column(String, nullable=True)
    status = Column(String, default="CONNECTED", nullable=False)
    metadata_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "provider_account_id", name="uix_user_provider_account"),
    )

    # Token Accessors with automatic encryption / decryption
    def set_access_token(self, token: str):
        self.access_token_encrypted = encrypt_secret(token)

    def get_access_token(self) -> str:
        return decrypt_secret(self.access_token_encrypted) or ""

    def set_refresh_token(self, token: str):
        self.refresh_token_encrypted = encrypt_secret(token)

    def get_refresh_token(self) -> str:
        return decrypt_secret(self.refresh_token_encrypted) or ""

    def set_api_key(self, key: str):
        self.api_key_encrypted = encrypt_secret(key)

    def get_api_key(self) -> str:
        return decrypt_secret(self.api_key_encrypted) or ""

    # Metadata helper
    def set_metadata(self, data: dict):
        self.metadata_json = json.dumps(data)

    def get_metadata(self) -> dict:
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    def to_safe_dict(self) -> dict:
        """
        Returns safe JSON payload for frontend.
        NEVER includes raw access tokens, refresh tokens, or unmasked API keys.
        """
        key_masked = ""
        raw_key = self.get_api_key()
        if raw_key:
            key_masked = mask_secret(raw_key)

        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "provider_account_name": self.provider_account_name or self.provider_email or self.provider.title(),
            "provider_email": self.provider_email or "",
            "status": self.status,
            "scopes": self.scopes or "",
            "masked_key": key_masked,
            "has_refresh_token": bool(self.refresh_token_encrypted),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
