import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.models.project import Project
from app.services.crawl_data.crawl_dataset_service import CrawlDatasetService
from app.services.crawl_data.crawl_tab_export_service import CrawlTabExportService
from app.routers.reports import build_export_filename, record_report_generation

router = APIRouter()


@router.get("/crawls")
def list_available_crawls(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns list of all completed crawl snapshots available for the authorized project.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    crawls = CrawlDatasetService.get_available_crawls(project.id, project.domain)
    return {"crawls": crawls, "total": len(crawls)}


@router.get("/export.xlsx")
def export_crawl_data_xlsx(
    project_id: str,
    crawl_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Exports the complete multi-worksheet Excel workbook (SEO_Crawl_Data.xlsx) containing all 16 tabs.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    xlsx_bytes = CrawlTabExportService.export_crawl_data_xlsx(
        project_id=project.id,
        domain=project.domain,
        crawl_id=crawl_id,
        project_name=project.name
    )

    domain_clean = project.domain or "website"
    filename = build_export_filename(domain_clean, "crawl-data", "xlsx")
    record_report_generation(db, project, "Complete Crawl Data Workbook", "xlsx", filename, None, "Crawl Data Output Layer")

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{tab_name}/export.csv")
def export_tab_csv(
    project_id: str,
    tab_name: str,
    crawl_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Exports the complete CSV dataset for a specific crawl data tab.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        csv_str = CrawlTabExportService.export_tab_csv(
            project_id=project.id,
            domain=project.domain,
            tab_name=tab_name,
            crawl_id=crawl_id
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

    domain_clean = project.domain or "website"
    clean_tab = tab_name.strip().lower().replace("_", "-")
    filename = build_export_filename(domain_clean, f"crawl-{clean_tab}", "csv")
    record_report_generation(db, project, f"Crawl Data ({clean_tab.capitalize()}) CSV", "csv", filename, None, "Crawl Data Output Layer")

    return Response(
        content=csv_str.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{tab_name}")
def get_crawl_data_tab(
    project_id: str,
    tab_name: str,
    crawl_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    filter_field: Optional[str] = Query(None),
    filter_value: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("asc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns filtered, sorted, and paginated rows for any of the 16 Screaming-Frog-style crawl data tabs.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        data = CrawlDatasetService.get_paginated_tab_data(
            project_id=project.id,
            domain=project.domain,
            tab_name=tab_name,
            crawl_id=crawl_id,
            search=search,
            filter_field=filter_field,
            filter_value=filter_value,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset
        )
        return data
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
