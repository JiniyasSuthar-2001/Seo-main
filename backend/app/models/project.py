from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, index=True)
    url = Column(String)
    description = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    # Campaign Configuration Fields
    target_type = Column(String, default="Domain")  # Domain, Subdomain, URL, Subfolder
    search_engine = Column(String, default="Google")
    target_country = Column(String, default="United States")
    target_language = Column(String, default="English")
    target_device = Column(String, default="Desktop")  # Desktop, Mobile, Tablet

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
    competitors = relationship("Competitor", back_populates="project", cascade="all, delete-orphan")
    keyword_groups = relationship("KeywordGroup", back_populates="project", cascade="all, delete-orphan")

    @property
    def domain(self):
        return self.url or None

    @domain.setter
    def domain(self, value):
        self.url = value
