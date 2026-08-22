from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class AuditIssue(Base):
    __tablename__ = "audit_issues"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("crawl_sessions.id"), nullable=True, index=True)
    
    rule_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)  # Crawlability, Indexability, HTTPS, Metadata, Content, etc.
    severity = Column(String, nullable=False, default="warning")  # critical, error, warning, notice
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)  # JSON string of evidence metadata
    affected_urls_json = Column(Text, nullable=True)  # JSON list of affected URLs
    affected_pages_count = Column(Integer, default=0)
    recommendation = Column(Text, nullable=True)
    
    status = Column(String, default="Open")  # Open, In Progress, Ignored, Resolved
    
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_detected = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
