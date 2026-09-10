import os
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.importers.base import BaseImporter
from app.importers.keyword_importer import parse_optional_int
from app.models.project import Project
from app.models.competitor import Competitor
from app.models.competitor_ranking import CompetitorRanking
from app.services.competitor_service import normalize_domain
from app.config.logger import get_logger

logger = get_logger(__name__)

class CompetitorRankingImporter(BaseImporter):
    def __init__(self, db: Session, project_id: str, filename: str = "competitor_rankings.csv", source: str = "Competitor Rankings CSV"):
        super().__init__(db, project_id, filename, source)
        self.error_details: List[Dict[str, Any]] = []

    def process_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        successful = 0
        errors = 0
        self.error_details = []

        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if not project:
            self.error_details.append({
                "row": 0,
                "field": "project_id",
                "category": "PROJECT_NOT_FOUND",
                "message": f"Project '{self.project_id}' not found."
            })
            self.records_processed = 0
            self.error_count = len(records)
            return 0, len(records)

        # Pre-fetch confirmed & suggested competitors for project
        project_competitors = self.db.query(Competitor).filter(Competitor.project_id == self.project_id).all()
        comp_by_id = {c.id: c for c in project_competitors}
        comp_by_domain = {normalize_domain(c.domain): c for c in project_competitors if c.domain}
        comp_by_name = {c.name.strip().lower(): c for c in project_competitors if c.name}

        for idx, row in enumerate(records, start=1):
            row_num = idx
            if not isinstance(row, dict):
                errors += 1
                self.error_details.append({
                    "row": row_num,
                    "field": "record",
                    "category": "INVALID_ROW_FORMAT",
                    "message": f"Row {row_num}: Record is not a key-value dictionary."
                })
                continue

            # 1. Resolve Keyword
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

            # 2. Resolve Competitor
            raw_comp = (
                row.get("competitor") or row.get("Competitor") or row.get("competitor_name") or 
                row.get("competitor_domain") or row.get("domain") or row.get("Domain") or ""
            ).strip()

            if not raw_comp:
                errors += 1
                self.error_details.append({
                    "row": row_num,
                    "field": "competitor",
                    "category": "MISSING_REQUIRED_FIELD",
                    "message": f"Row {row_num}: Missing required 'competitor' or 'domain' column."
                })
                continue

            matched_comp: Optional[Competitor] = None
            if raw_comp in comp_by_id:
                matched_comp = comp_by_id[raw_comp]
            elif normalize_domain(raw_comp) in comp_by_domain:
                matched_comp = comp_by_domain[normalize_domain(raw_comp)]
            elif raw_comp.lower() in comp_by_name:
                matched_comp = comp_by_name[raw_comp.lower()]

            if not matched_comp:
                # Create confirmed competitor automatically for the project if domain is valid
                clean_dom = normalize_domain(raw_comp) or raw_comp
                matched_comp = Competitor(
                    project_id=self.project_id,
                    name=raw_comp if not raw_comp.startswith("http") else clean_dom,
                    domain=clean_dom,
                    url=raw_comp if raw_comp.startswith("http") else f"https://{clean_dom}/",
                    status="Confirmed",
                    discovery_source="Competitor Ranking Import"
                )
                self.db.add(matched_comp)
                self.db.commit()
                self.db.refresh(matched_comp)
                comp_by_id[matched_comp.id] = matched_comp
                comp_by_domain[clean_dom] = matched_comp
                comp_by_name[matched_comp.name.lower()] = matched_comp

            # 3. Parse Position
            raw_pos = row.get("position") if "position" in row else row.get("Position", row.get("rank", row.get("Rank")))
            pos_val = None
            if raw_pos is not None and str(raw_pos).strip() and str(raw_pos).strip().lower() not in ("null", "none", "not ranking", "-", "n/a", ""):
                parsed_pos, pos_err = parse_optional_int(raw_pos, "position")
                if pos_err or (parsed_pos is not None and parsed_pos < 1):
                    errors += 1
                    self.error_details.append({
                        "row": row_num,
                        "field": "position",
                        "category": "INVALID_VALUE",
                        "message": f"Row {row_num}: Invalid position value '{raw_pos}'. Must be a positive integer (e.g. 1, 2, 9) or empty."
                    })
                    continue
                pos_val = parsed_pos

            # Parse previous position
            raw_prev = row.get("previous_position") if "previous_position" in row else row.get("Previous Position", row.get("prev_rank"))
            prev_val = None
            if raw_prev is not None and str(raw_prev).strip() and str(raw_prev).strip().lower() not in ("null", "none", "not ranking", "-", "n/a", ""):
                parsed_prev, prev_err = parse_optional_int(raw_prev, "previous_position")
                if not prev_err and parsed_prev is not None and parsed_prev >= 1:
                    prev_val = parsed_prev

            ranking_url = (row.get("url") or row.get("ranking_url") or row.get("Ranking URL") or row.get("Target URL") or "").strip() or None
            search_engine = (row.get("search_engine") or row.get("engine") or row.get("Search Engine") or "Google").strip()
            country = (row.get("country") or row.get("Country") or row.get("location") or project.target_country or "United States").strip()
            location = (row.get("location") or row.get("Location") or "").strip() or None
            device = (row.get("device") or row.get("Device") or project.target_device or "Desktop").strip()
            
            # Parse Date
            checked_at = datetime.utcnow()
            raw_date = row.get("checked_at") or row.get("date") or row.get("Date") or row.get("Checked Date")
            if raw_date and str(raw_date).strip():
                try:
                    checked_at = datetime.fromisoformat(str(raw_date).strip().replace("Z", "+00:00"))
                except Exception:
                    pass

            # 4. Upsert CompetitorRanking
            existing_ranking = self.db.query(CompetitorRanking).filter(
                CompetitorRanking.project_id == self.project_id,
                CompetitorRanking.competitor_id == matched_comp.id,
                CompetitorRanking.keyword == raw_keyword
            ).first()

            if existing_ranking:
                if pos_val is not None:
                    existing_ranking.previous_position = existing_ranking.position
                    existing_ranking.position = pos_val
                if ranking_url:
                    existing_ranking.ranking_url = ranking_url
                existing_ranking.search_engine = search_engine
                existing_ranking.country = country
                if location:
                    existing_ranking.location = location
                existing_ranking.device = device
                existing_ranking.source = "csv_import"
                existing_ranking.checked_at = checked_at
                existing_ranking.updated_at = datetime.utcnow()
            else:
                new_ranking = CompetitorRanking(
                    project_id=self.project_id,
                    competitor_id=matched_comp.id,
                    keyword=raw_keyword,
                    position=pos_val,
                    previous_position=prev_val,
                    ranking_url=ranking_url,
                    search_engine=search_engine,
                    country=country,
                    location=location,
                    device=device,
                    source="csv_import",
                    checked_at=checked_at,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(new_ranking)

            successful += 1

        self.db.commit()
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
