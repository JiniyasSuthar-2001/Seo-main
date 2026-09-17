import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.config.database import get_db
from app.importers.keyword_importer import KeywordImporter
from app.importers.ranking_importer import RankingImporter
from app.importers.backlink_importer import BacklinkImporter
from app.importers.competitor_importer import CompetitorImporter
from app.importers.competitor_ranking_importer import CompetitorRankingImporter

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
    elif clean_type in ("competitor_rankings", "competitor_ranking"):
        return CompetitorRankingImporter(db=db, project_id=project_id, filename=filename, source=source)
    elif clean_type == "backlinks":
        return BacklinkImporter(db=db, project_id=project_id, filename=filename, source=source)
    elif clean_type in ("competitors", "competitor"):
        return CompetitorImporter(db=db, project_id=project_id, filename=filename, source=source)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported data_type '{data_type}'. Must be keywords, rankings, competitor_rankings, backlinks, or competitors.")

def parse_xlsx_stdlib(contents: bytes) -> List[Dict[str, Any]]:
    import zipfile
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_data = z.read("xl/sharedStrings.xml")
            ss_root = ET.fromstring(ss_data)
            for si in ss_root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                t_el = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                if t_el is not None and t_el.text:
                    shared_strings.append(t_el.text)
                else:
                    parts = [t.text for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text]
                    shared_strings.append("".join(parts))

        ws_name = "xl/worksheets/sheet1.xml"
        if ws_name not in z.namelist():
            sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
            if not sheets:
                return []
            ws_name = sheets[0]

        sheet_data = z.read(ws_name)
        sheet_root = ET.fromstring(sheet_data)

        rows = []
        sheetData = sheet_root.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData")
        if sheetData is None:
            return []

        for row in sheetData.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            row_vals = []
            for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                cell_type = c.get("t")
                v_el = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = ""
                if v_el is not None and v_el.text is not None:
                    raw_v = v_el.text
                    if cell_type == "s" and raw_v.isdigit():
                        idx = int(raw_v)
                        val = shared_strings[idx] if idx < len(shared_strings) else raw_v
                    else:
                        val = raw_v
                row_vals.append(val)
            if any(row_vals):
                rows.append(row_vals)

        if not rows:
            return []

        headers = [str(h or "").strip() for h in rows[0]]
        records = []
        for r in rows[1:]:
            rec = {}
            for i, val in enumerate(r):
                if i < len(headers) and headers[i]:
                    rec[headers[i]] = str(val or "").strip()
            if any(rec.values()):
                records.append(rec)
        return records

def parse_uploaded_file(filename: str, contents: bytes) -> List[Dict[str, Any]]:
    lower_fn = filename.lower()

    if lower_fn.endswith(".json"):
        try:
            decoded = contents.decode("utf-8-sig")
            data = json.loads(decoded)
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
            elif isinstance(data, dict):
                for key in ("records", "data", "items", "rows", "keywords", "rankings", "backlinks", "competitors"):
                    if isinstance(data.get(key), list):
                        return [r for r in data[key] if isinstance(r, dict)]
                return [data]
            return []
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {e}")

    elif lower_fn.endswith((".xlsx", ".xls")):
        records = []
        parsed = False
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if rows:
                headers = [str(cell or "").strip() for cell in rows[0]]
                for r in rows[1:]:
                    if any(cell is not None for cell in r):
                        rec = {}
                        for h, val in zip(headers, r):
                            if h:
                                rec[h] = str(val) if val is not None else ""
                        if rec:
                            records.append(rec)
                parsed = True
        except Exception as ex:
            print(f"[IMPORT] openpyxl check: {ex}", flush=True)

        if not parsed:
            try:
                records = parse_xlsx_stdlib(contents)
                parsed = True
            except Exception as ex:
                print(f"[IMPORT] stdlib xlsx parser check: {ex}", flush=True)

        if not parsed:
            raise HTTPException(status_code=400, detail="Unable to parse Excel file. Please ensure it is a valid .xlsx or .xls file.")
        return records

    else:
        # Default CSV parser
        try:
            decoded = contents.decode("utf-8-sig")
        except Exception:
            decoded = contents.decode("latin-1")
        reader = csv.DictReader(io.StringIO(decoded))
        return [row for row in reader]

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
async def upload_file(
    project_id: str,
    data_type: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    allowed_exts = (".csv", ".xlsx", ".xls", ".json")
    if not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a .csv, .xlsx, .xls, or .json file."
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit of 10MB.")

    records = parse_uploaded_file(file.filename, contents)

    importer = get_importer(data_type, db, project_id, file.filename, f"{data_type.capitalize()} Upload ({file.filename.split('.')[-1].upper()})")
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
