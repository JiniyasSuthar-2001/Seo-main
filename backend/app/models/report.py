from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from app.config.database import Base

class ReportRecord(Base):
    __tablename__ = "report_records"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    website = Column(String(255), nullable=False)
    report_type = Column(String(100), nullable=False)
    file_type = Column(String(10), nullable=False)
    filename = Column(String(255), nullable=False)
    crawl_id = Column(String(100), nullable=True)
    data_sources = Column(String(255), nullable=True)
    status = Column(String(50), default="Completed")
    generated_at = Column(DateTime, default=datetime.utcnow)
