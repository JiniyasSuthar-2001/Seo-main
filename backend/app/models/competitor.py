from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    domain = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False)
    location = Column(String, nullable=True)
    geographic_level = Column(String, nullable=True, default="City")  # Town, City, State, Country, Global
    
    relevance_score = Column(Float, default=0.0)  # 0.0 - 1.0 or percentage
    keyword_overlap = Column(Integer, default=0)
    search_appearances = Column(Integer, default=0)
    
    status = Column(String, default="Suggested")  # Suggested, Confirmed, Ignored, Removed, Inactive
    is_primary = Column(Boolean, default=False)
    
    discovery_source = Column(String, nullable=True)  # SERP Analysis, Keyword Overlap, Manual
    discovered_keywords = Column(Text, nullable=True)  # JSON string
    competing_services = Column(Text, nullable=True)  # JSON string
    notes = Column(Text, nullable=True)
    
    first_discovered = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="competitors")
