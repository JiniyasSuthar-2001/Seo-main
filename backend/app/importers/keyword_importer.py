from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.importers.base import BaseImporter
from app.models.keyword import Keyword
from app.config.logger import get_logger

logger = get_logger(__name__)


def parse_optional_int(val: Any, field_name: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Safely parses integer values from CSV fields.
    Distinguishes missing/empty values (returns None, None), valid integers (returns int, None),
    and invalid numeric text (returns None, error_message).
    Numeric 0 is correctly preserved as integer 0 rather than being treated as falsy/missing.
    """
    if val is None:
        return None, None
    if isinstance(val, (int, float)):
        return int(val), None
    s_val = str(val).strip()
    if not s_val:
        return None, None
    try:
        return int(s_val), None
    except (ValueError, TypeError):
        return None, f"Invalid integer value for '{field_name}': '{val}'"


def parse_optional_float(val: Any, field_name: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Safely parses float values from CSV fields.
    """
    if val is None:
        return 0.0, None
    if isinstance(val, (int, float)):
        return float(val), None
    s_val = str(val).strip()
    if not s_val:
        return 0.0, None
    try:
        return float(s_val), None
    except (ValueError, TypeError):
        return 0.0, f"Invalid numeric value for '{field_name}': '{val}'"


class KeywordImporter(BaseImporter):
    def __init__(self, db: Session, project_id: str, filename: str, source: str):
        super().__init__(db, project_id, filename, source)
        self.error_details: List[Dict[str, Any]] = []

    def process_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        successful = 0
        errors = 0
        self.error_details = []

        try:
            for idx, row in enumerate(records, start=1):
                row_num = idx
                if not isinstance(row, dict):
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "record",
                        "category": "INVALID_ROW_FORMAT",
                        "message": f"Row {row_num}: Record is not a valid key-value object."
                    })
                    continue

                raw_keyword = (row.get("keyword") or "").strip()
                if not raw_keyword:
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "keyword",
                        "category": "MISSING_REQUIRED_FIELD",
                        "message": f"Row {row_num}: Missing required 'keyword' field."
                    })
                    continue

                # Parse search_volume, difficulty, position
                search_vol, sv_err = parse_optional_int(row.get("search_volume"), "search_volume")
                difficulty_val, diff_err = parse_optional_float(row.get("difficulty"), "difficulty")
                pos_val, pos_err = parse_optional_int(row.get("position"), "position")

                row_error_msgs = [err for err in (sv_err, diff_err, pos_err) if err]
                if row_error_msgs:
                    errors += 1
                    msg = f"Row {row_num}: " + "; ".join(row_error_msgs)
                    self.error_details.append({
                        "row": row_num,
                        "field": "numeric_parsing",
                        "category": "INVALID_VALUE",
                        "message": msg
                    })
                    logger.warning(f"[CSV IMPORT] KeywordImporter row {row_num} error: {msg}")
                    continue

                try:
                    kw = Keyword(
                        project_id=self.project_id,
                        dataset_id=self.dataset.id,
                        keyword=raw_keyword,
                        target_url=(row.get("target_url") or "").strip() or None,
                        search_volume=search_vol if search_vol is not None else 0,
                        difficulty=difficulty_val if difficulty_val is not None else 0.0,
                        intent=(row.get("intent") or "").strip() or None,
                        position=pos_val  # Preserves 0 as integer 0, None for empty/missing
                    )
                    self.db.add(kw)
                    successful += 1
                except Exception as e:
                    errors += 1
                    err_msg = f"Row {row_num}: Database insertion error."
                    self.error_details.append({
                        "row": row_num,
                        "field": "database",
                        "category": "DB_INSERTION_FAILED",
                        "message": err_msg
                    })
                    logger.error(f"[CSV IMPORT] KeywordImporter row {row_num} DB failure: {e}")

            self.db.commit()
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
            logger.error(f"[CSV IMPORT] KeywordImporter batch transaction error: {e}")

        self.records_processed = successful
        self.error_count = errors
        return successful, errors

    def get_structured_import_report(self) -> Dict[str, Any]:

        """
        Returns structured import report with capped error details and additional errors count.
        """
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
