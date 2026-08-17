from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.dataset import Dataset
from datetime import datetime

class BaseImporter:
    def __init__(self, db: Session, project_id: str, filename: str, source: str = "API"):
        self.db = db
        self.project_id = project_id
        self.filename = filename
        self.source = source
        self.dataset = None
        self.records_processed = 0
        self.error_count = 0

    def start_import(self, data_type: str):
        self.dataset = Dataset(
            project_id=self.project_id,
            data_type=data_type,
            source=self.source,
            filename=self.filename,
            status="IMPORTING"
        )
        self.db.add(self.dataset)
        self.db.commit()
        self.db.refresh(self.dataset)
        return self.dataset

    def process_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        To be implemented by subclasses.
        Should return (successful_inserts, errors)
        """
        raise NotImplementedError

    def finish_import(self):
        if self.dataset:
            self.dataset.record_count = self.records_processed
            self.dataset.error_count = self.error_count
            self.dataset.status = "SUCCESS" if self.error_count == 0 else ("PARTIAL" if self.records_processed > 0 else "FAILED")
            self.db.commit()
            return self.dataset
