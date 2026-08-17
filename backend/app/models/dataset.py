from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.config.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    data_type = Column(String) # pages, keywords, etc.
    source = Column(String)
    filename = Column(String)
    record_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    status = Column(String) # SUCCESS, PARTIAL, FAILED
    imported_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="datasets")
