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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
    competitors = relationship("Competitor", back_populates="project", cascade="all, delete-orphan")

    @property
    def domain(self):
        # No fallback - a project's domain is either its real url or nothing.
        # Every route depends on 'if not project.domain' to correctly reject
        # projects with no website configured; a hard-coded fallback here
        # would make that check silently never fire.
        return self.url or None

    @domain.setter
    def domain(self, value):
        self.url = value
