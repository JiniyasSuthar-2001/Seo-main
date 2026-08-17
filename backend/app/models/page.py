from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from app.config.database import Base

class Page(Base):
    __tablename__ = "pages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    dataset_id = Column(String, ForeignKey("datasets.id"))
    
    url = Column(String, index=True)
    title = Column(String, nullable=True)
    meta_description = Column(String, nullable=True)
    canonical = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    h1 = Column(String, nullable=True)
    indexability = Column(String, nullable=True)

    project = relationship("Project", back_populates="pages")
    dataset = relationship("Dataset")
