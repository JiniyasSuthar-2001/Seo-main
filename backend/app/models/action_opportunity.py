from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class ActionOpportunity(Base):
    __tablename__ = "action_opportunities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)  # Technical, Content, Keywords, Internal Links, Backlinks, Competitors
    priority_score = Column(Float, default=50.0)  # 0 - 100 deterministic score
    priority_level = Column(String, default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW
    impact = Column(String, nullable=True)
    evidence = Column(Text, nullable=True)
    affected_urls_json = Column(Text, nullable=True)  # JSON list
    affected_count = Column(Integer, default=1)
    recommendation = Column(Text, nullable=True)
    
    status = Column(String, default="Open")  # Open, In Progress, Ignored, Resolved
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
