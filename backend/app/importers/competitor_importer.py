import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.importers.base import BaseImporter
from app.models.competitor import Competitor
from app.services.competitor_service import normalize_domain
from app.config.logger import get_logger

logger = get_logger(__name__)


def parse_optional_int(val: Any, field_name: str) -> Tuple[Optional[int], Optional[str]]:
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
    if val is None:
        return None, None
    if isinstance(val, (int, float)):
        return float(val), None
    s_val = str(val).strip()
    if not s_val:
        return None, None
    try:
        return float(s_val), None
    except (ValueError, TypeError):
        return None, f"Invalid numeric value for '{field_name}': '{val}'"


class CompetitorImporter(BaseImporter):
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

                raw_name = (row.get("name") or row.get("Competitor Name") or row.get("competitor_name") or "").strip()
                raw_domain = (row.get("domain") or row.get("url") or row.get("Domain") or row.get("URL") or row.get("Competitor Domain") or "").strip()

                if not raw_domain and not raw_name:
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "domain",
                        "category": "MISSING_REQUIRED_FIELD",
                        "message": f"Row {row_num}: Missing required competitor domain or URL."
                    })
                    continue

                norm_domain = normalize_domain(raw_domain or raw_name)
                if not norm_domain:
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "domain",
                        "category": "INVALID_DOMAIN",
                        "message": f"Row {row_num}: Invalid domain format '{raw_domain}'."
                    })
                    continue

                comp_name = raw_name or norm_domain

                # Parse optional metrics
                relevance_score, rel_err = parse_optional_float(
                    row.get("relevance_score") or row.get("Relevance Score"), "relevance_score"
                )
                keyword_overlap, kw_err = parse_optional_int(
                    row.get("keyword_overlap") or row.get("Keyword Overlap"), "keyword_overlap"
                )
                search_appearances, sa_err = parse_optional_int(
                    row.get("search_appearances") or row.get("Search Appearances"), "search_appearances"
                )

                row_error_msgs = [err for err in (rel_err, kw_err, sa_err) if err]
                if row_error_msgs:
                    errors += 1
                    msg = f"Row {row_num}: " + "; ".join(row_error_msgs)
                    self.error_details.append({
                        "row": row_num,
                        "field": "numeric_parsing",
                        "category": "INVALID_VALUE",
                        "message": msg
                    })
                    logger.warning(f"[CSV IMPORT] CompetitorImporter row {row_num} error: {msg}")
                    continue

                location = (row.get("location") or row.get("Location") or "Local Market").strip()
                geo_level = (row.get("geographic_level") or row.get("Geographic Level") or "City").strip()
                notes = (row.get("notes") or row.get("Notes") or "").strip()

                full_url = raw_domain if raw_domain.startswith(("http://", "https://")) else f"https://{norm_domain}"

                try:
                    existing = self.db.query(Competitor).filter(
                        Competitor.project_id == self.project_id,
                        Competitor.domain == norm_domain
                    ).first()

                    if existing:
                        existing.name = comp_name
                        existing.url = full_url
                        existing.location = location or existing.location
                        existing.geographic_level = geo_level or existing.geographic_level
                        if relevance_score is not None:
                            existing.relevance_score = relevance_score
                        if keyword_overlap is not None:
                            existing.keyword_overlap = keyword_overlap
                        if search_appearances is not None:
                            existing.search_appearances = search_appearances
                        if notes:
                            existing.notes = notes
                        existing.status = "Confirmed"
                        existing.updated_at = datetime.utcnow()
                    else:
                        new_comp = Competitor(
                            id=str(uuid.uuid4()),
                            project_id=self.project_id,
                            name=comp_name,
                            domain=norm_domain,
                            url=full_url,
                            location=location,
                            geographic_level=geo_level,
                            relevance_score=relevance_score,
                            keyword_overlap=keyword_overlap,
                            search_appearances=search_appearances,
                            status="Confirmed",
                            is_primary=False,
                            discovery_source="Imported Data",
                            notes=notes,
                            first_discovered=datetime.utcnow(),
                            last_checked=datetime.utcnow()
                        )
                        self.db.add(new_comp)

                    successful += 1
                except Exception as ex:
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "database",
                        "category": "DB_ERROR",
                        "message": f"Row {row_num}: Database insertion error: {str(ex)}"
                    })
                    logger.error(f"[CSV IMPORT] CompetitorImporter row {row_num} DB error: {ex}")

            self.db.commit()
            self.records_processed = successful
            self.error_count = errors
            return successful, errors

        except Exception as e:
            self.db.rollback()
            logger.error(f"[CSV IMPORT] CompetitorImporter general failure: {e}")
            raise e

    def get_structured_import_report(self) -> Dict[str, Any]:
        return {
            "status": "SUCCESS" if self.error_count == 0 else ("PARTIAL" if self.records_processed > 0 else "FAILED"),
            "data_type": "competitors",
            "filename": self.filename,
            "records_processed": self.records_processed,
            "error_count": self.error_count,
            "errors": self.error_details,
            "message": f"Imported {self.records_processed} competitors successfully ({self.error_count} errors)."
        }
