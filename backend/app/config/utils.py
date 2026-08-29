import os
from typing import Any, List
from urllib.parse import urlparse


def normalize_stored_path(path: str) -> str:
    if not path:
        return ""
    clean_path = str(path).replace("\\", "/")
    return os.path.normpath(clean_path)

def get_sanitized_domain(url_or_domain: str) -> str:
    """
    Centralized, bulletproof URL/domain -> filesystem-safe storage directory name converter.
    Strips scheme (http://, https://), port, path, query params, fragment, and unsafe chars.
    Guarantees no Windows invalid path characters (WinError 123) or reserved device names.
    """
    if not url_or_domain:
        return "unknown_domain"

    clean_str = str(url_or_domain).strip()

    # Remove protocol if present
    if "://" in clean_str:
        clean_str = clean_str.split("://", 1)[1]

    # Remove auth info if present (user:pass@host)
    if "@" in clean_str:
        clean_str = clean_str.split("@", 1)[1]

    # Truncate at path, port, query, fragment separators
    for sep in ("/", "\\", ":", "?", "#", " ", "\t", "\n", "\r"):
        if sep in clean_str:
            clean_str = clean_str.split(sep, 1)[0]

    clean_str = clean_str.lower().strip()

    if clean_str.startswith("www."):
        clean_str = clean_str[4:]

    # Keep alphanumeric, hyphens, underscores, dots
    safe_chars = []
    for char in clean_str:
        if char.isalnum() or char in ("-", "_", "."):
            safe_chars.append(char)
        else:
            safe_chars.append("_")

    safe_domain = "".join(safe_chars).strip("._")

    # Guard against Windows reserved device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    reserved_names = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if safe_domain in reserved_names:
        safe_domain = f"site_{safe_domain}"

    return safe_domain if safe_domain else "unknown_domain"

def get_project_storage_key(domain_or_url: Any, project_id: Any = None) -> str:
    """
    Constructs a project-isolated storage directory key.
    Format: '{sanitized_domain}__{project_id}' when project_id is present.
    Example: 'example_com__proj_a1b2'
    """
    safe_dom = get_sanitized_domain(str(domain_or_url)) if domain_or_url else "unknown_domain"
    if project_id and str(project_id).strip():
        safe_pid = str(project_id).strip().replace("/", "_").replace("\\", "_")
        return f"{safe_dom}__{safe_pid}"
    return safe_dom

def get_project_storage_dir(base_dir: str, domain_or_url: Any = None, project_id: Any = None, db: Any = None) -> str:
    """
    Returns the absolute directory path for project storage, enforcing strict multi-tenant isolation.
    1. Primary: base_dir / {sanitized_domain}__{project_id}
    2. Check: base_dir / {project_id}
    3. Legacy Check (Single Tenant Only): If legacy base_dir / {sanitized_domain} exists,
       it is ONLY used if NO OTHER project shares that domain.
    """
    safe_dom = get_sanitized_domain(str(domain_or_url)) if domain_or_url else "unknown_domain"
    safe_pid = str(project_id).strip().replace("/", "_").replace("\\", "_") if project_id and str(project_id).strip() else None

    if safe_pid and domain_or_url:
        primary_key = f"{safe_dom}__{safe_pid}"
        primary_dir = os.path.join(base_dir, primary_key)
        if os.path.exists(primary_dir):
            return primary_dir
        
        # Check if project_id folder exists directly
        pid_dir = os.path.join(base_dir, safe_pid)
        if os.path.exists(pid_dir):
            return pid_dir

        # Check backward compatibility legacy domain directory
        legacy_dir = os.path.join(base_dir, safe_dom)
        if os.path.exists(legacy_dir):
            is_shared = False
            if db is not None:
                try:
                    from app.models.project import Project
                    q = db.query(Project)
                    res_count = q.filter(Project.url.ilike(f"%{safe_dom}%")).count()
                    if callable(res_count):
                        res_count = res_count()
                    if isinstance(res_count, (int, float)) and res_count > 1:
                        is_shared = True
                except Exception as e:
                    pass
            if not is_shared:
                return legacy_dir

        return primary_dir

    elif safe_pid:
        pid_dir = os.path.join(base_dir, safe_pid)
        if os.path.exists(pid_dir):
            return pid_dir
        return os.path.join(base_dir, safe_pid)

    elif domain_or_url:
        return os.path.join(base_dir, safe_dom)

    return os.path.join(base_dir, "unknown_project")

def sanitize_csv_cell(val: Any) -> Any:
    """
    Sanitizes values written to CSV files to prevent CSV Formula Injection vulnerability.
    Neutralizes values starting with dangerous formula triggers (=, +, -, @, \t, \r).
    """
    if val is None:
        return ""
    s_val = str(val)
    if s_val and s_val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s_val}"
    return s_val

def sanitize_csv_row(row: List[Any]) -> List[Any]:
    return [sanitize_csv_cell(item) for item in row]

