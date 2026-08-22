from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.config.database import get_db
from app.importers.keyword_importer import KeywordImporter
from pydantic import BaseModel

router = APIRouter()

class ImportRequest(BaseModel):
    filename: str
    source: str
    data_type: str
    records: List[Dict[str, Any]]

@router.post("/")
def import_data(project_id: str, request: ImportRequest, db: Session = Depends(get_db)):
    if request.data_type == "keywords":
        importer = KeywordImporter(db=db, project_id=project_id, filename=request.filename, source=request.source)
    else:
        raise HTTPException(status_code=400, detail=f"Importer for {request.data_type} not implemented yet.")
        
    dataset = importer.start_import(request.data_type)
    success, errors = importer.process_records(request.records)
    dataset = importer.finish_import()
    
    report = importer.get_structured_import_report()
    return report

@router.get("/")
def get_imports(project_id: str, db: Session = Depends(get_db)):
    from app.models.dataset import Dataset
    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).order_by(Dataset.imported_at.desc()).all()
    return datasets
