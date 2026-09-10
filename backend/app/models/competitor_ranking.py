from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class CompetitorRanking(Base):
    __tablename__ = "competitor_rankings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    competitor_id = Column(String, ForeignKey("competitors.id"), nullable=False, index=True)
    
    keyword = Column(String, nullable=False, index=True)
    position = Column(Integer, nullable=True)  # 1-indexed (1, 2, 3...) or NULL if not ranking
    previous_position = Column(Integer, nullable=True)
    ranking_url = Column(String, nullable=True)
    
    search_engine = Column(String, nullable=True, default="Google")
    country = Column(String, nullable=True, default="United States")
    location = Column(String, nullable=True)
    device = Column(String, nullable=True, default="Desktop")  # Desktop / Mobile / Tablet
    
    source = Column(String, nullable=False, default="serp_provider")  # serp_provider, csv_import, manual_import
    
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project")
    competitor = relationship("Competitor")

    __table_args__ = (
        Index("ix_comp_ranking_lookup", "project_id", "competitor_id", "keyword", "checked_at"),
        Index("ix_comp_ranking_kw", "project_id", "keyword"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "competitor_id": self.competitor_id,
            "competitor_name": self.competitor.name if self.competitor else None,
            "competitor_domain": self.competitor.domain if self.competitor else None,
            "keyword": self.keyword,
            "position": self.position,
            "previous_position": self.previous_position,
            "ranking_url": self.ranking_url,
            "search_engine": self.search_engine or "Google",
            "country": self.country or "United States",
            "location": self.location,
            "device": self.device or "Desktop",
            "source": self.source or "serp_provider",
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
