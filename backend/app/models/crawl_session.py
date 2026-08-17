from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class CrawlSession(Base):
    __tablename__ = "crawl_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    
    status = Column(String, default="running") # running, completed, failed
    pages_discovered = Column(Integer, default=0)
    pages_crawled = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", backref="crawl_sessions")
