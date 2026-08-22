from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class KeywordGroup(Base):
    __tablename__ = "keyword_groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="keyword_groups")
    keywords = relationship("Keyword", back_populates="group")
