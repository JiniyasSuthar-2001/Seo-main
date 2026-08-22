import os
from urllib.parse import urlparse

def normalize_stored_path(path: str) -> str:
    if not path:
        return ""
    clean_path = str(path).replace("\\", "/")
    return os.path.normpath(clean_path)

def get_sanitized_domain(url_or_domain: str) -> str:
    if not url_or_domain:
        return "unknown_domain"
    
    clean_str = url_or_domain.strip()
    if not clean_str.startswith(("http://", "https://")):
        clean_str = "https://" + clean_str
        
    try:
        parsed = urlparse(clean_str)
        netloc = parsed.netloc.lower() or parsed.path.lower()
        netloc = netloc.split(":")[0]  # Remove port if present
        if netloc.startswith("www."):
            netloc = netloc[4:]
            
        safe_domain = "".join([c if c.isalnum() else "_" for c in netloc]).strip("_")
        return safe_domain if safe_domain else "unknown_domain"
    except Exception:
        # Fallback safe replace
        safe_domain = clean_str.replace("https://", "").replace("http://", "").replace("www.", "")
        return "".join([c if c.isalnum() else "_" for c in safe_domain]).strip("_")
