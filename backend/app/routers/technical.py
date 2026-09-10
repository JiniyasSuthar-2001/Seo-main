import os
import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.models.project import Project
from app.models.page import Page
from app.models.audit_issue import AuditIssue
from app.models.crawl_session import CrawlSession
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.services.audit_rules import evaluate_site_audit_rules
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

@router.get("")
@router.get("/")
def get_technical_audit(
    project_id: str,
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {
            "health_score": None,
            "total_audited_pages": 0,
            "summary": {"critical_errors": 0, "errors": 0, "warnings": 0, "notices": 0, "passed_checks": 0},
            "issues": [],
            "category_breakdown": {}
        }

    domain = project.domain
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    pages = []
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)
        except Exception as e:
            print(f"[TECHNICAL API] Error loading pages: {e}", flush=True)

    # 2. Evaluate 15-category site audit rules
    audit_data = evaluate_site_audit_rules(pages)

    # Filter issues by category & severity
    filtered_issues = audit_data["issues"]
    if category and isinstance(category, str) and category.lower() != "all":
        filtered_issues = [i for i in filtered_issues if i.get("category", "").lower() == category.lower()]
    if severity and isinstance(severity, str) and severity.lower() != "all":
        filtered_issues = [i for i in filtered_issues if i.get("severity", "").lower() == severity.lower()]


    try:
        lim = int(limit)
    except (ValueError, TypeError):
        lim = 50
    try:
        off = int(offset)
    except (ValueError, TypeError):
        off = 0

    return {
        "project_id": project.id,
        "domain": domain,
        "health_score": audit_data["health_score"],
        "score_available": audit_data.get("score_available", True if audit_data.get("health_score") is not None else False),
        "total_audited_pages": audit_data["total_audited_pages"],
        "successful_html_pages_count": audit_data.get("successful_html_pages_count", 0),
        "blocked_pages_count": audit_data.get("blocked_pages_count", 0),
        "evaluated_rules_count": audit_data.get("evaluated_rules_count", 14),
        "total_evaluated_checks": audit_data.get("total_evaluated_checks", 0),
        "checks_explanation": audit_data.get("checks_explanation", ""),
        "crawl_timestamp": latest.get("completed_at") or latest.get("timestamp") if ('latest' in locals() and latest) else None,
        "crawl_status": latest.get("status", "completed") if os.path.exists(latest_path) else "no_crawl",
        "summary": audit_data["summary"],
        "category_breakdown": audit_data["category_breakdown"],
        "category_checks_table": audit_data.get("category_checks_table", []),
        "structured_data_summary": audit_data.get("structured_data_summary"),
        "issues": filtered_issues[off : off + lim],
        "total_issues": len(filtered_issues),
        "provenance": audit_data["provenance"]
    }



@router.get("/issue-history")
def get_audit_issue_history(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Compares recent crawl snapshots on disk to detect New, Resolved, Persistent, Worsened, and Improved issues.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {
            "has_history": False,
            "message": "No previous crawl data available for comparison.",
            "resolved_issues_count": 0,
            "new_issues_count": 0,
            "improved_issues_count": 0,
            "worsened_issues_count": 0,
            "still_open_issues_count": 0,
            "comparison_items": []
        }

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    crawls_dir = os.path.join(proj_dir, "crawls")

    if not os.path.exists(crawls_dir):
        return {
            "has_history": False,
            "message": "No previous crawl data available for comparison.",
            "resolved_issues_count": 0,
            "new_issues_count": 0,
            "improved_issues_count": 0,
            "worsened_issues_count": 0,
            "still_open_issues_count": 0,
            "comparison_items": []
        }

    # Find valid crawl directories sorted descending by folder name (timestamp)
    crawl_folders = sorted(
        [d for d in os.listdir(crawls_dir) if os.path.isdir(os.path.join(crawls_dir, d))],
        reverse=True
    )

    if len(crawl_folders) == 0:
        return {
            "has_history": False,
            "message": "No previous crawl data available for comparison.",
            "resolved_issues_count": 0,
            "new_issues_count": 0,
            "improved_issues_count": 0,
            "worsened_issues_count": 0,
            "still_open_issues_count": 0,
            "comparison_items": []
        }

    if len(crawl_folders) == 1:
        return {
            "has_history": False,
            "message": "This is the first crawl. A comparison will be available after the next completed crawl.",
            "current_snapshot": crawl_folders[0],
            "resolved_issues_count": 0,
            "new_issues_count": 0,
            "improved_issues_count": 0,
            "worsened_issues_count": 0,
            "still_open_issues_count": 0,
            "comparison_items": []
        }

    curr_dir = os.path.join(crawls_dir, crawl_folders[0])
    prev_dir = os.path.join(crawls_dir, crawl_folders[1])

    def load_snapshot_pages(cdir):
        pfile = os.path.join(cdir, "pages.json")
        if os.path.exists(pfile):
            try:
                with open(pfile, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    curr_pages = load_snapshot_pages(curr_dir)
    prev_pages = load_snapshot_pages(prev_dir)

    curr_audit = evaluate_site_audit_rules(curr_pages)
    prev_audit = evaluate_site_audit_rules(prev_pages)

    curr_issues_map = {i.get("title"): i for i in curr_audit.get("issues", [])}
    prev_issues_map = {i.get("title"): i for i in prev_audit.get("issues", [])}

    all_titles = set(curr_issues_map.keys()).union(set(prev_issues_map.keys()))

    comparison_items = []
    resolved_count = 0
    new_count = 0
    improved_count = 0
    worsened_count = 0
    still_open_count = 0

    for title in sorted(all_titles):
        curr_i = curr_issues_map.get(title)
        prev_i = prev_issues_map.get(title)

        curr_urls = set(curr_i.get("affected_urls", [])) if curr_i else set()
        prev_urls = set(prev_i.get("affected_urls", [])) if prev_i else set()

        curr_count = curr_i.get("count", len(curr_urls)) if curr_i else 0
        prev_count = prev_i.get("count", len(prev_urls)) if prev_i else 0

        category = (curr_i or prev_i).get("category", "Website Check")
        severity = (curr_i or prev_i).get("severity", "Notice")
        rule_id = (curr_i or prev_i).get("rule_id")

        if prev_count > 0 and curr_count == 0:
            status = "RESOLVED"
            resolved_count += 1
            s_suffix = "s" if prev_count != 1 else ""
            change_text = f"Resolved ({prev_count} page{s_suffix} fixed)"
        elif prev_count == 0 and curr_count > 0:
            status = "NEW"
            new_count += 1
            s_suffix = "s" if curr_count != 1 else ""
            change_text = f"New problem ({curr_count} page{s_suffix} affected)"
        elif curr_count < prev_count:
            status = "IMPROVED"
            improved_count += 1
            diff = prev_count - curr_count
            change_text = f"Improved ({diff} fixed, {curr_count} still affected)"
        elif curr_count > prev_count:
            status = "WORSENED"
            worsened_count += 1
            diff = curr_count - prev_count
            change_text = f"Worsened (+{diff} affected, total {curr_count})"
        else:
            status = "STILL OPEN"
            still_open_count += 1
            change_text = f"Unchanged ({curr_count} affected)"

        comparison_items.append({
            "title": title,
            "rule_id": rule_id,
            "category": category,
            "severity": severity,
            "status": status,
            "previous_affected_count": prev_count,
            "current_affected_count": curr_count,
            "change_summary": change_text,
            "resolved_urls": list(prev_urls - curr_urls),
            "new_urls": list(curr_urls - prev_urls),
            "still_affected_urls": list(curr_urls.intersection(prev_urls))
        })

    return {
        "has_history": True,
        "current_snapshot": crawl_folders[0],
        "previous_snapshot": crawl_folders[1],
        "resolved_issues_count": resolved_count,
        "new_issues_count": new_count,
        "improved_issues_count": improved_count,
        "worsened_issues_count": worsened_count,
        "still_open_issues_count": still_open_count,
        "total_compared_rules": len(all_titles),
        "comparison_items": comparison_items,
        "message": f"Comparing current scan ({crawl_folders[0]}) against previous scan ({crawl_folders[1]})."
    }


@router.get("/crawl-comparison")
def get_crawl_comparison(
    project_id: str,
    crawl_a: Optional[str] = Query(None, description="Snapshot ID / timestamp for Crawl A (defaults to latest)"),
    crawl_b: Optional[str] = Query(None, description="Snapshot ID / timestamp for Crawl B (defaults to previous)"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Comprehensive historical crawl comparison engine (Crawl A vs Crawl B).
    Computes exact differences across:
      - Issues: New (+X), Fixed (-Y), Still Present (Z)
      - Pages: New (+A), Removed (-B), Changed (C)
      - Links: Discovered, Lost
      - Metadata changes: Titles, Meta Descriptions, Canonicals, Status Codes
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    crawls_dir = os.path.join(proj_dir, "crawls")

    if not os.path.exists(crawls_dir):
        return {
            "has_comparison": False,
            "message": "No crawl history available for comparison."
        }

    crawl_folders = sorted(
        [d for d in os.listdir(crawls_dir) if os.path.isdir(os.path.join(crawls_dir, d))],
        reverse=True
    )

    if len(crawl_folders) < 2 and (not crawl_a or not crawl_b):
        return {
            "has_comparison": False,
            "message": "At least two completed crawls are required to perform a historical comparison.",
            "available_crawls": crawl_folders
        }

    selected_a = crawl_a if (crawl_a and crawl_a in crawl_folders) else crawl_folders[0]
    selected_b = crawl_b if (crawl_b and crawl_b in crawl_folders) else (crawl_folders[1] if len(crawl_folders) > 1 else crawl_folders[0])

    dir_a = os.path.join(crawls_dir, selected_a)
    dir_b = os.path.join(crawls_dir, selected_b)

    def _load_pages(cdir):
        p_file = os.path.join(cdir, "pages.json")
        if os.path.exists(p_file):
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    pages_a = _load_pages(dir_a)
    pages_b = _load_pages(dir_b)

    map_a = {p.get("url"): p for p in pages_a if p.get("url")}
    map_b = {p.get("url"): p for p in pages_b if p.get("url")}

    # 1. Page differences
    urls_a = set(map_a.keys())
    urls_b = set(map_b.keys())

    new_urls = list(urls_a - urls_b)
    removed_urls = list(urls_b - urls_a)
    common_urls = urls_a.intersection(urls_b)

    changed_pages = []
    for u in common_urls:
        pa = map_a[u]
        pb = map_b[u]
        changes = []
        if pa.get("title") != pb.get("title"):
            changes.append({"field": "title", "from": pb.get("title"), "to": pa.get("title")})
        if pa.get("meta_description") != pb.get("meta_description"):
            changes.append({"field": "meta_description", "from": pb.get("meta_description"), "to": pa.get("meta_description")})
        if pa.get("canonical") != pb.get("canonical"):
            changes.append({"field": "canonical", "from": pb.get("canonical"), "to": pa.get("canonical")})
        if pa.get("status_code") != pb.get("status_code"):
            changes.append({"field": "status_code", "from": pb.get("status_code"), "to": pa.get("status_code")})

        if changes:
            changed_pages.append({
                "url": u,
                "changes_count": len(changes),
                "changes": changes
            })

    # 2. Issue differences
    audit_a = evaluate_site_audit_rules(pages_a)
    audit_b = evaluate_site_audit_rules(pages_b)

    issues_a = {i["rule_id"]: i for i in audit_a.get("issues", [])}
    issues_b = {i["rule_id"]: i for i in audit_b.get("issues", [])}

    all_rule_ids = set(issues_a.keys()).union(set(issues_b.keys()))
    new_issues = []
    fixed_issues = []
    persistent_issues = []

    for rid in sorted(all_rule_ids):
        ia = issues_a.get(rid)
        ib = issues_b.get(rid)
        if ia and not ib:
            new_issues.append(ia)
        elif ib and not ia:
            fixed_issues.append(ib)
        else:
            persistent_issues.append({
                "rule_id": rid,
                "title": ia.get("title"),
                "category": ia.get("category"),
                "severity": ia.get("severity"),
                "current_count": ia.get("affected_count", 0),
                "previous_count": ib.get("affected_count", 0),
                "delta": ia.get("affected_count", 0) - ib.get("affected_count", 0)
            })

    return {
        "has_comparison": True,
        "project_id": project.id,
        "domain": project.domain,
        "crawl_a": selected_a,
        "crawl_b": selected_b,
        "pages_summary": {
            "total_pages_current": len(pages_a),
            "total_pages_previous": len(pages_b),
            "new_pages_count": len(new_urls),
            "removed_pages_count": len(removed_urls),
            "changed_pages_count": len(changed_pages),
            "new_pages": new_urls[:50],
            "removed_pages": removed_urls[:50],
            "changed_pages": changed_pages[:50]
        },
        "issues_summary": {
            "new_issues_count": len(new_issues),
            "fixed_issues_count": len(fixed_issues),
            "persistent_issues_count": len(persistent_issues),
            "new_issues": new_issues,
            "fixed_issues": fixed_issues,
            "persistent_issues": persistent_issues
        },
        "health_score_comparison": {
            "current_score": audit_a.get("health_score"),
            "previous_score": audit_b.get("health_score"),
            "score_change": (audit_a.get("health_score") or 0) - (audit_b.get("health_score") or 0) if (audit_a.get("health_score") is not None and audit_b.get("health_score") is not None) else None
        }
    }



@router.put("/issues/{issue_id}/status")
def update_issue_status(
    issue_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    issue = db.query(AuditIssue).filter(AuditIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Audit issue not found.")

    get_user_membership(db, user_id, issue.project_id)

    new_status = payload.get("status")
    if new_status not in ("Open", "In Progress", "Ignored", "Resolved"):
        raise HTTPException(status_code=400, detail="Invalid status value.")

    issue.status = new_status
    db.commit()
    return {"id": issue.id, "status": issue.status, "message": "Issue status updated successfully."}

from app.routers.reports import export_technical_csv

@router.get("/export.csv")
def technical_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_technical_csv(project_id, user_id, db)
