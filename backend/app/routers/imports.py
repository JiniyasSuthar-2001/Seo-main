import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.config.database import get_db
from app.importers.keyword_importer import KeywordImporter
from app.importers.ranking_importer import RankingImporter
from app.importers.backlink_importer import BacklinkImporter
from app.importers.competitor_importer import CompetitorImporter

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

class ImportRequest(BaseModel):
    filename: str
    source: str
    data_type: str
    records: List[Dict[str, Any]]

def get_importer(data_type: str, db: Session, project_id: str, filename: str, source: str):
    clean_type = data_type.strip().lower()
    if clean_type == "keywords":
        return KeywordImporter(db=db, project_id=project_id, filename=filename, source=source)
    elif clean_type == "rankings":
        return RankingImporter(db=db, project_id=project_id, filename=filename, source=source)
    elif clean_type == "backlinks":
        return BacklinkImporter(db=db, project_id=project_id, filename=filename, source=source)
    elif clean_type in ("competitors", "competitor"):
        return CompetitorImporter(db=db, project_id=project_id, filename=filename, source=source)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported data_type '{data_type}'. Must be keywords, rankings, backlinks, or competitors.")

@router.post("/")
def import_data(
    project_id: str,
    request: ImportRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    importer = get_importer(request.data_type, db, project_id, request.filename, request.source)
    importer.start_import(request.data_type)
    importer.process_records(request.records)
    importer.finish_import()
    return importer.get_structured_import_report()

@router.post("/upload")
async def upload_csv_file(
    project_id: str,
    data_type: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are accepted for data import.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit of 10MB.")

    try:
        decoded = contents.decode("utf-8-sig")
    except Exception:
        decoded = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    records = [row for row in reader]

    importer = get_importer(data_type, db, project_id, file.filename, f"{data_type.capitalize()} CSV Upload")
    importer.start_import(data_type)
    importer.process_records(records)
    importer.finish_import()
    return importer.get_structured_import_report()

@router.get("")
@router.get("/")
@router.get("/history")
@router.get("/history/")
@router.get("/list")
@router.get("/list/")
def get_imports(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    from app.models.dataset import Dataset
    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).order_by(Dataset.imported_at.desc()).all()
    return [{
        "id": d.id,
        "filename": d.name or "imported_data.csv",
        "data_type": d.type or "dataset",
        "rows_imported": d.record_count or 0,
        "timestamp": d.imported_at.isoformat() if d.imported_at else None,
        "status": d.status or "Completed",
        "provenance": d.provenance or "User Import"
    } for d in datasets]

from fastapi import Response
from app.services.reports.guideline_service import GuidelineReportService

@router.get("/guidelines/{guideline_id}/pdf")
@router.get("/guidelines/{guideline_id}.pdf")
def get_guideline_pdf(guideline_id: str):
    pdf_bytes = GuidelineReportService.generate_guideline_pdf(guideline_id)
    filename = f"SEO_Platform_{guideline_id.capitalize()}_Upload_Guidelines.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})

@router.get("/guidelines/{guideline_id}/template.csv")
def get_guideline_template(guideline_id: str):
    csv_str = GuidelineReportService.generate_sample_template_csv(guideline_id)
    filename = f"{guideline_id}-upload-template.csv"
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})
