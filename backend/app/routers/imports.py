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
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported data_type '{data_type}'. Must be keywords, rankings, or backlinks.")

@router.post("/")
def import_data(project_id: str, request: ImportRequest, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
):
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

@router.get("/")
def get_imports(project_id: str, db: Session = Depends(get_db)):
    from app.models.dataset import Dataset
    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).order_by(Dataset.imported_at.desc()).all()
    return datasets
