from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from app.config.database import Base

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    dataset_id = Column(String, ForeignKey("datasets.id"))
    
    keyword = Column(String, index=True)
    target_url = Column(String, nullable=True)
    search_volume = Column(Integer, nullable=True)
    difficulty = Column(Float, nullable=True)
    intent = Column(String, nullable=True)
    position = Column(Integer, nullable=True)
    country = Column(String, nullable=True)
    device = Column(String, nullable=True)
    
    project = relationship("Project", back_populates="keywords")
    dataset = relationship("Dataset")
