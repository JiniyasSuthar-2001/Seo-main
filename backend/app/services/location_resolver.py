import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

class LocationConfidence:
    HIGH = "HIGH"         # Explicit structured Schema (LocalBusiness / PostalAddress)
    MEDIUM = "MEDIUM"     # Explicit text signal / address pattern in project notes/metadata
    LOW = "LOW"           # Weak inferred signal (e.g. ccTLD -> Country only)
    UNKNOWN = "UNKNOWN"   # Insufficient evidence

# Standard country-code TLD mapping for Country inference ONLY (never infers city)
CCTLD_COUNTRY_MAP = {
    "au": "Australia",
    "uk": "United Kingdom",
    "co.uk": "United Kingdom",
    "ca": "Canada",
    "nz": "New Zealand",
    "de": "Germany",
    "fr": "France",
    "jp": "Japan",
    "us": "United States"
}

def extract_tld(url_or_domain: str) -> Optional[str]:
    if not url_or_domain:
        return None
    val = url_or_domain.strip().lower()
    if not val.startswith(("http://", "https://")):
        val = "http://" + val
    try:
        netloc = urlparse(val).netloc or val.split("/")[0]
        host = netloc.split(":")[0]
        parts = host.split(".")
        if len(parts) >= 2:
            if len(parts) >= 3 and f"{parts[-2]}.{parts[-1]}" in CCTLD_COUNTRY_MAP:
                return f"{parts[-2]}.{parts[-1]}"
            return parts[-1]
    except Exception:
        pass
    return None

def resolve_location(
    project_url: Optional[str] = None,
    target_country: Optional[str] = None,
    notes: Optional[str] = None,
    description: Optional[str] = None,
    crawl_data: Optional[Dict[str, Any]] = None,
    schema_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Data-driven location resolution engine.
    Extracts and normalizes location evidence without hardcoding city lists or inventing facts.
    """
    sources = []
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = target_country if target_country and target_country.strip() else None
    postal_code: Optional[str] = None
    confidence = LocationConfidence.UNKNOWN

    if country:
        sources.append("project_target_country")
        confidence = LocationConfidence.MEDIUM

    # 1. Inspect Structured Schema Data (HIGH Confidence)
    if schema_data and isinstance(schema_data, list):
        for item in schema_data:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("@type", "")).lower()
            if "business" in item_type or "organization" in item_type or "store" in item_type or "place" in item_type:
                addr = item.get("address")
                if isinstance(addr, dict):
                    schema_city = addr.get("addressLocality")
                    schema_region = addr.get("addressRegion")
                    schema_country = addr.get("addressCountry")
                    schema_zip = addr.get("postalCode")

                    if schema_city or schema_region or schema_country:
                        city = str(schema_city).strip() if schema_city else city
                        region = str(schema_region).strip() if schema_region else region
                        country = str(schema_country).strip() if schema_country else country
                        postal_code = str(schema_zip).strip() if schema_zip else postal_code
                        sources.append("schema_json_ld")
                        confidence = LocationConfidence.HIGH
                        break

    # 2. Inspect Textual Evidence / Address Signals in Notes & Description (MEDIUM Confidence)
    combined_text = f"{notes or ''} {description or ''}".strip()
    if combined_text:
        # Pattern match explicit address key-values (e.g. "Location: Sydney, NSW, Australia" or "City: Perth")
        city_match = re.search(r"\b(?:City|Location|Headquarters|Address):\s*([A-Za-z\s]+?)(?:,|\n|$)", combined_text, re.IGNORECASE)
        if city_match and not city:
            found_city = city_match.group(1).strip()
            if found_city and len(found_city) > 2 and found_city.lower() not in ("unknown", "global", "none"):
                city = found_city
                sources.append("project_notes_text")
                if confidence != LocationConfidence.HIGH:
                    confidence = LocationConfidence.MEDIUM

    # 3. Country-Code TLD Inference (LOW Confidence for Country ONLY)
    if project_url and not country:
        tld = extract_tld(project_url)
        if tld and tld in CCTLD_COUNTRY_MAP:
            country = CCTLD_COUNTRY_MAP[tld]
            sources.append("domain_cctld")
            if confidence == LocationConfidence.UNKNOWN:
                confidence = LocationConfidence.LOW

    return {
        "city": city,
        "region": region,
        "country": country,
        "postal_code": postal_code,
        "confidence": confidence,
        "sources": sources
    }
