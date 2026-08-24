from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Google Email or User ID
    google_id = Column(String, index=True, nullable=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        masked = self.email[0] + "***" + self.email[self.email.find("@"):] if "@" in self.email else "user***@gmail.com"
        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "masked_email": masked,
            "name": self.name,
            "picture": self.picture,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
