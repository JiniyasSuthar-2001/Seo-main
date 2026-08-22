import os
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.importers.base import BaseImporter
from app.models.project import Project
from app.config.utils import get_sanitized_domain
from app.services.competitor_service import normalize_domain

from app.config.settings import settings
from app.config.logger import get_logger

logger = get_logger(__name__)

class BacklinkImporter(BaseImporter):
    def __init__(self, db: Session, project_id: str, filename: str, source: str = "Backlinks CSV"):
        super().__init__(db, project_id, filename, source)
        self.error_details: List[Dict[str, Any]] = []

    def process_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        successful = 0
        errors = 0
        self.error_details = []

        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        domain = project.domain if project else ""
        safe_domain = get_sanitized_domain(domain) if domain else ""

        backlinks_file_records = []

        try:
            for idx, row in enumerate(records, start=1):
                row_num = idx
                if not isinstance(row, dict):
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "record",
                        "category": "INVALID_ROW_FORMAT",
                        "message": f"Row {row_num}: Record is not a key-value object."
                    })
                    continue

                source_url = (
                    row.get("source_url") or row.get("Source URL") or row.get("referring_url") or row.get("Referring URL") or row.get("source") or ""
                ).strip()
                target_url = (
                    row.get("target_url") or row.get("Target URL") or row.get("destination_url") or row.get("url") or ""
                ).strip()
                source_domain = (
                    row.get("source_domain") or row.get("Source Domain") or row.get("domain") or row.get("Domain") or row.get("referring_domain") or ""
                ).strip()

                if not source_url and not source_domain:
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "source_url",
                        "category": "MISSING_REQUIRED_FIELD",
                        "message": f"Row {row_num}: Missing required 'source_url' or 'source_domain' column."
                    })
                    continue

                if source_url and not source_domain:
                    source_domain = normalize_domain(source_url)

                anchor_text = (row.get("anchor_text") or row.get("Anchor Text") or row.get("anchor") or row.get("Anchor") or "").strip() or None
                follow_status = (row.get("follow_status") or row.get("Follow/Nofollow") or row.get("rel") or row.get("type") or "dofollow").strip()
                status = (row.get("status") or row.get("Status") or "active").strip()
                first_seen = (row.get("first_seen") or row.get("First Seen") or "").strip() or None
                last_seen = (row.get("last_seen") or row.get("Last Seen") or "").strip() or None

                backlinks_file_records.append({
                    "source_url": source_url or f"https://{source_domain}/",
                    "source_domain": source_domain,
                    "target_url": target_url or (f"https://{domain}/" if domain else None),
                    "anchor_text": anchor_text or "No Anchor Text",
                    "follow_status": follow_status,
                    "status": status,
                    "first_seen": first_seen,
                    "last_seen": last_seen,
                    "data_source": "Backlinks CSV Import"
                })

                successful += 1

            # Save to backlinks.json for project
            if safe_domain and backlinks_file_records:
                proj_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
                os.makedirs(proj_dir, exist_ok=True)
                backlinks_file = os.path.join(proj_dir, "backlinks.json")
                existing_json = []
                if os.path.exists(backlinks_file):
                    try:
                        with open(backlinks_file, "r") as bf:
                            existing_json = json.load(bf)
                    except Exception:
                        existing_json = []

                # Merge backlinks by source_url + target_url
                json_dict = {}
                for item in existing_json:
                    if isinstance(item, dict):
                        key = f"{item.get('source_url')}|{item.get('target_url')}"
                        json_dict[key] = item

                for item in backlinks_file_records:
                    key = f"{item.get('source_url')}|{item.get('target_url')}"
                    json_dict[key] = item

                with open(backlinks_file, "w") as wf:
                    json.dump(list(json_dict.values()), wf, indent=2)

        except Exception as e:
            errors = len(records)
            successful = 0
            self.error_details.append({
                "row": 0,
                "field": "batch",
                "category": "IMPORT_FAILED",
                "message": f"Backlink import failed: {e}"
            })
            logger.error(f"[BACKLINK IMPORTER] Batch error: {e}")

        self.records_processed = successful
        self.error_count = errors
        return successful, errors

    def get_structured_import_report(self) -> Dict[str, Any]:
        capped_details = self.error_details[:50]
        additional_count = max(0, len(self.error_details) - 50)
        return {
            "dataset_id": self.dataset.id if self.dataset else None,
            "status": self.dataset.status if self.dataset else "FAILED",
            "successful_records": self.records_processed,
            "error_records": self.error_count,
            "error_details": capped_details,
            "additional_errors_count": additional_count
        }
