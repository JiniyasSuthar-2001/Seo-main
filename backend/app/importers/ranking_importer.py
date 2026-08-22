import os
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.importers.base import BaseImporter
from app.importers.keyword_importer import parse_optional_int, parse_optional_float
from app.models.keyword import Keyword
from app.models.project import Project
from app.config.utils import get_sanitized_domain
from app.config.settings import settings
from app.config.logger import get_logger

logger = get_logger(__name__)

class RankingImporter(BaseImporter):
    def __init__(self, db: Session, project_id: str, filename: str, source: str = "Rankings CSV"):
        super().__init__(db, project_id, filename, source)
        self.error_details: List[Dict[str, Any]] = []

    def process_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        successful = 0
        errors = 0
        self.error_details = []

        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        domain = project.domain if project else ""
        safe_domain = get_sanitized_domain(domain) if domain else ""

        rankings_file_records = []

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

                raw_keyword = (
                    row.get("keyword") or row.get("Keyword") or row.get("query") or row.get("Query") or ""
                ).strip()

                if not raw_keyword:
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "keyword",
                        "category": "MISSING_REQUIRED_FIELD",
                        "message": f"Row {row_num}: Missing required 'keyword' column."
                    })
                    continue

                # Parse position and previous position
                pos_val, pos_err = parse_optional_int(
                    row.get("position") if "position" in row else row.get("Position", row.get("rank", row.get("Rank"))),
                    "position"
                )
                prev_pos_val, prev_pos_err = parse_optional_int(
                    row.get("previous_position") if "previous_position" in row else row.get("Previous Position", row.get("prev_rank")),
                    "previous_position"
                )

                if pos_err or prev_pos_err:
                    errors += 1
                    msg = f"Row {row_num}: " + "; ".join(filter(None, [pos_err, prev_pos_err]))
                    self.error_details.append({
                        "row": row_num,
                        "field": "numeric_position",
                        "category": "INVALID_VALUE",
                        "message": msg
                    })
                    continue

                target_url = (row.get("url") or row.get("target_url") or row.get("URL") or row.get("Target URL") or "").strip() or None
                search_engine = (row.get("search_engine") or row.get("engine") or row.get("Search Engine") or "").strip() or None
                location = (row.get("location") or row.get("country") or row.get("Location") or "").strip() or None
                device = (row.get("device") or row.get("Device") or "").strip() or None
                date_str = (row.get("date") or row.get("Date") or "").strip() or None

                try:
                    # Update database keyword entry if present or create new
                    existing_kw = self.db.query(Keyword).filter(
                        Keyword.project_id == self.project_id,
                        Keyword.keyword == raw_keyword
                    ).first()

                    if existing_kw:
                        if pos_val is not None:
                            existing_kw.position = pos_val
                        if target_url:
                            existing_kw.target_url = target_url
                        if location:
                            existing_kw.country = location
                        if device:
                            existing_kw.device = device
                    else:
                        new_kw = Keyword(
                            project_id=self.project_id,
                            dataset_id=self.dataset.id if self.dataset else None,
                            keyword=raw_keyword,
                            target_url=target_url,
                            position=pos_val,
                            country=location,
                            device=device,
                            source="Rankings CSV Import"
                        )
                        self.db.add(new_kw)

                    rankings_file_records.append({
                        "keyword": raw_keyword,
                        "position": pos_val,
                        "previous_position": prev_pos_val,
                        "url": target_url or (f"https://{domain}/" if domain else None),
                        "search_engine": search_engine or "Google",
                        "location": location or "Unknown",
                        "device": device or "Desktop",
                        "date": date_str,
                        "data_source": "Rankings CSV Import"
                    })

                    successful += 1
                except Exception as e:
                    errors += 1
                    err_msg = f"Row {row_num}: Database update failure."
                    self.error_details.append({
                        "row": row_num,
                        "field": "database",
                        "category": "DB_FAILURE",
                        "message": err_msg
                    })
                    logger.error(f"[RANKING IMPORTER] Row {row_num} failure: {e}")

            self.db.commit()

            # Save to rankings.json for project
            if safe_domain and rankings_file_records:
                proj_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
                os.makedirs(proj_dir, exist_ok=True)
                rankings_file = os.path.join(proj_dir, "rankings.json")
                existing_json = []
                if os.path.exists(rankings_file):
                    try:
                        with open(rankings_file, "r") as rf:
                            existing_json = json.load(rf)
                    except Exception:
                        existing_json = []

                # Merge rankings by keyword
                json_dict = {item["keyword"]: item for item in existing_json if isinstance(item, dict) and "keyword" in item}
                for item in rankings_file_records:
                    json_dict[item["keyword"]] = item

                with open(rankings_file, "w") as wf:
                    json.dump(list(json_dict.values()), wf, indent=2)

        except Exception as e:
            self.db.rollback()
            errors = len(records)
            successful = 0
            self.error_details.append({
                "row": 0,
                "field": "batch",
                "category": "TRANSACTION_FAILED",
                "message": "Batch database transaction failed. All rows rolled back."
            })
            logger.error(f"[RANKING IMPORTER] Batch error: {e}")

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
