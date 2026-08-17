from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.importers.base import BaseImporter
from app.models.keyword import Keyword

class KeywordImporter(BaseImporter):
    def process_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        successful = 0
        errors = 0
        
        # Use transaction for safety
        try:
            for row in records:
                try:
                    # Basic mapping
                    kw = Keyword(
                        project_id=self.project_id,
                        dataset_id=self.dataset.id,
                        keyword=row.get('keyword', ''),
                        target_url=row.get('target_url'),
                        search_volume=int(row.get('search_volume', 0)) if row.get('search_volume') else 0,
                        difficulty=float(row.get('difficulty', 0)) if row.get('difficulty') else 0.0,
                        intent=row.get('intent'),
                        position=int(row.get('position', 0)) if row.get('position') else None
                    )
                    
                    if not kw.keyword:
                        errors += 1
                        continue
                        
                    self.db.add(kw)
                    successful += 1
                except Exception as e:
                    errors += 1
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            errors += len(records)
            successful = 0
            
        self.records_processed = successful
        self.error_count = errors
        return successful, errors
