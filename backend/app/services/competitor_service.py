import re
import json
import uuid
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.competitor import Competitor
from app.models.keyword import Keyword
from app.models.page import Page


def normalize_domain(url_or_domain: str) -> str:
    """
    Normalizes any URL or domain string down to a clean root domain without
    protocol, www, ports, paths, or query parameters.
    """
    if not url_or_domain:
        return ""
    
    val = url_or_domain.strip().lower()
    
    if not val.startswith(("http://", "https://")):
        val = "http://" + val
        
    try:
        parsed = urllib.parse.urlparse(val)
        netloc = parsed.netloc or parsed.path
        host = netloc.split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        val = re.sub(r"^https?://", "", val)
        val = re.sub(r"^www\.", "", val)
        val = val.split("/")[0].split(":")[0].split("?")[0]
        return val.strip()


from app.services.location_resolver import resolve_location, LocationConfidence


def extract_location_info(project: Project) -> Dict[str, Any]:
    """
    Extracts location details from project metadata using data-driven evidence resolution.
    Never defaults country-code TLDs (.au, .uk, etc.) to arbitrary cities like Brisbane.
    """
    resolved = resolve_location(
        project_url=getattr(project, "url", None) or getattr(project, "domain", None),
        target_country=getattr(project, "target_country", None),
        notes=getattr(project, "notes", None),
        description=getattr(project, "description", None)
    )

    return {
        "city": resolved["city"] or "Unknown",
        "state": resolved["region"] or "Unknown",
        "country": resolved["country"] or "Global",
        "confidence": resolved["confidence"],
        "sources": resolved["sources"]
    }



import os
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, get_project_storage_dir
from app.providers.datasources import DataSourceManager
from app.models.external_connection import ExternalConnection

def check_serp_provider_status(project: Project, db: Session = None) -> Dict[str, Any]:
    """
    Determines whether a real SERP/search-data provider or imported SERP dataset exists.
    Checks (in priority order):
      1. Imported SERP/competitor/rankings files on disk.
      2. ExternalConnection database record for provider='serp_provider' (set via Integrations).
      3. SERP_API_KEY environment variable.
      4. DataSourceManager file-based config (legacy fallback).
    Production rule: Groq/LLM alone is an AI analysis engine, NOT a SERP data provider.
    """
    if not project or not project.domain:
        return {
            "has_serp_provider": False,
            "provider_name": "None",
            "message": "No project domain configured."
        }

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)

    # 1. Check if an imported SERP / competitor dataset exists on disk
    comp_file = os.path.join(proj_dir, "competitors.json")
    serp_file = os.path.join(proj_dir, "serp_results.json")
    rankings_file = os.path.join(proj_dir, "rankings.json")

    if os.path.exists(comp_file) or os.path.exists(serp_file) or os.path.exists(rankings_file):
        return {
            "has_serp_provider": True,
            "provider_name": "Imported SERP Dataset",
            "source_type": "Imported Data",
            "message": "Imported SERP data available."
        }

    # 2. Check ExternalConnection database table for a connected SERP provider
    #    This is the primary source of truth set via Settings -> Integrations.
    if db is not None:
        try:
            serp_conn = db.query(ExternalConnection).filter(
                ExternalConnection.provider.in_(["serp_provider", "serp"])
            ).first()
            if serp_conn:
                serp_key = serp_conn.get_api_key()
                if serp_key and serp_key.strip():
                    provider_name = serp_conn.provider_account_name or "SERP Provider"
                    return {
                        "has_serp_provider": True,
                        "provider_name": provider_name,
                        "source_type": "API Key",
                        "message": f"{provider_name} connected and active."
                    }
        except Exception as e:
            print(f"[SERP STATUS] DB check error: {e}", flush=True)

    # 3. Check SERP_API_KEY environment variable as fallback
    env_serp_key = os.environ.get("SERP_API_KEY", "").strip()
    if env_serp_key:
        return {
            "has_serp_provider": True,
            "provider_name": "SERP Provider (Env)",
            "source_type": "Environment Variable",
            "message": "SERP provider configured via environment variable."
        }

    # 4. Check DataSourceManager file-based config (legacy fallback)
    ds_mgr = DataSourceManager()
    datasources = ds_mgr.get_project_datasources(project.id, project.domain)
    rank_tracker = datasources.get("rank_tracker", {})

    if rank_tracker.get("implemented") and rank_tracker.get("status", "").startswith("Active"):
        return {
            "has_serp_provider": True,
            "provider_name": rank_tracker.get("name", "SERP Data Provider"),
            "source_type": "SERP Data",
            "message": "Active SERP provider configured."
        }

    return {
        "has_serp_provider": False,
        "provider_name": "None",
        "message": "Competitor discovery requires search-result data. Connect a supported SERP/search provider or import ranking/SERP data."
    }


def discover_competitors_for_project(project: Project, db: Session, location: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Discovers real competitors for the project using live SERP data from the configured provider.

    Priority:
      1. Live SerpApi / OpenSERP discovery (requires ExternalConnection or SERP_API_KEY env var).
      2. Fallback: imported competitors.json on disk (legacy/static import).
      3. No provider -> return existing DB records with a clear configuration message.

    Args:
      location: Optional dict with keys: country, country_code, state, city.
                When provided, overrides project-level country/language settings and
                adds a SerpApi location= parameter for city/region targeting.

    NEVER fabricates competitors. NEVER overwrites Confirmed or Ignored user decisions.
    """
    from app.providers.serp_adapter import SERPAdapterFactory
    import urllib.request
    import urllib.error
    import urllib.parse as _urlparse
    import json as _json

    # ── Non-competitor domain blacklist ─────────────────────────────────────────
    # Covers universal SERP noise. Not exhaustive — extend here as needed.
    _BLACKLISTED_DOMAINS = frozenset({
        # Google properties
        "google.com", "google.co.uk", "google.ca", "google.com.au",
        "google.co.in", "google.de", "google.fr", "google.co.jp",
        "accounts.google.com", "support.google.com", "maps.google.com",
        "play.google.com", "news.google.com",
        # Meta / social
        "facebook.com", "instagram.com", "threads.net",
        "linkedin.com", "twitter.com", "x.com",
        "tiktok.com", "snapchat.com", "pinterest.com",
        # Video
        "youtube.com", "youtu.be", "vimeo.com",
        # Reference / encyclopedic / dictionary giants
        "wikipedia.org", "wikimedia.org", "wikihow.com", "wiktionary.org",
        "dictionary.com", "thesaurus.com", "merriam-webster.com",
        "cambridge.org", "dictionary.cambridge.org", "collinsdictionary.com",
        "britannica.com", "vocabulary.com", "investopedia.com",
        "reverso.net", "wordreference.com", "linguee.com", "dictionary.reverso.net",
        # Q&A
        "reddit.com", "quora.com", "stackoverflow.com",
        # E-commerce / directory behemoths
        "amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au",
        "amazon.de", "amazon.fr", "amazon.co.jp", "amazon.in",
        "ebay.com", "etsy.com",
        "yelp.com", "tripadvisor.com", "trustpilot.com",
        "yellowpages.com", "whitepages.com",
        # Apple / Microsoft ecosystem
        "apple.com", "microsoft.com", "office.com",
        # News giants
        "bbc.com", "bbc.co.uk", "cnn.com", "forbes.com",
        "theguardian.com", "nytimes.com", "huffpost.com",
        # Search / aggregators
        "bing.com", "yahoo.com", "duckduckgo.com", "ask.com",
        "msn.com", "aol.com",
    })

    _GENERIC_SINGLE_WORDS = frozenset({
        "digital", "website", "web", "design", "services", "service", "agency", "company", "online",
        "best", "top", "free", "cheap", "near", "me", "home", "about", "contact", "login", "signup",
        "uis", "uisdigitalcom", "marketing", "development", "solutions", "business", "media"
    })

    _STOPWORDS = frozenset({
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "of", "about", "is", "are"
    })

    # ── Country / language code mapping for SerpApi ─────────────────────────────
    _COUNTRY_MAP = {
        "united states": "us", "united kingdom": "gb", "canada": "ca",
        "australia": "au", "india": "in", "germany": "de", "france": "fr",
        "spain": "es", "italy": "it", "japan": "jp", "brazil": "br",
        "mexico": "mx", "netherlands": "nl", "singapore": "sg",
    }
    _LANG_MAP = {
        "english": "en", "spanish": "es", "french": "fr", "german": "de",
        "italian": "it", "portuguese": "pt", "japanese": "ja",
        "chinese": "zh", "dutch": "nl", "hindi": "hi",
    }

    def _normalize_country(val: str) -> str:
        return _COUNTRY_MAP.get((val or "").strip().lower(), "us")

    def _normalize_lang(val: str) -> str:
        return _LANG_MAP.get((val or "").strip().lower(), "en")

    def _extract_root_domain(url_or_domain: str) -> str:
        """Strip protocol, www prefix, path, port. Returns clean root domain."""
        s = (url_or_domain or "").strip().lower()
        if not s:
            return ""
        if "://" in s:
            s = s.split("://", 1)[1]
        s = s.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
        if s.startswith("www."):
            s = s[4:]
        return s.strip()

    def _is_blacklisted(domain: str) -> bool:
        if not domain:
            return True
        d = domain.lower().strip()
        # Exact match or subdomain match
        for bl in _BLACKLISTED_DOMAINS:
            if d == bl or d.endswith("." + bl):
                return True
        # TLD-agnostic match for google.*, amazon.*, wikipedia, dictionary domains
        parts = d.split(".")
        if len(parts) >= 2:
            base = parts[-2]
            if base in ("google", "amazon", "facebook", "apple", "microsoft", "wikipedia", "wikihow", "wiktionary", "dictionary", "cambridge", "merriam-webster", "britannica"):
                return True
        return False

    def _is_valid_competitor_keyword(kw: str) -> bool:
        if not kw:
            return False
        clean = kw.strip().lower()
        if len(clean) < 3:
            return False
        if any(clean.endswith(ext) for ext in [".com", ".org", ".net", ".in", ".io", ".co"]):
            return False
        words = clean.split()
        if len(words) == 1:
            w = words[0]
            if len(w) < 4 or w in _GENERIC_SINGLE_WORDS or w in _STOPWORDS:
                return False
            # Reject generic single words without search intent
            return False
        meaningful = [w for w in words if w not in _STOPWORDS and len(w) > 1]
        if not meaningful:
            return False
        return True

    # ── Resolve SERP adapter ────────────────────────────────────────────────────
    serp_status = check_serp_provider_status(project, db)

    existing_competitors = db.query(Competitor).filter(
        Competitor.project_id == project.id
    ).order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()

    suggested = [c for c in existing_competitors if c.status == "Suggested"]
    confirmed = [c for c in existing_competitors if c.status == "Confirmed"]

    if not serp_status["has_serp_provider"]:
        # No provider at all → return what we have from the DB
        return {
            "has_serp_provider": False,
            "provider_name": serp_status["provider_name"],
            "message": serp_status["message"],
            "suggested_competitors": suggested,
            "confirmed_competitors": confirmed,
            "all_competitors": existing_competitors,
        }

    # ── Determine if this is a live-API provider or a static file import ─────────
    source_type = serp_status.get("source_type", "")
    is_live_api = source_type in ("API Key", "Environment Variable")

    # ── LIVE SERP DISCOVERY ─────────────────────────────────────────────────────
    if is_live_api:
        # Load the decrypted API key
        serp_api_key = ""
        serp_provider_name = "serpapi"  # default; map display name → adapter id

        if db is not None:
            try:
                serp_conn = db.query(ExternalConnection).filter(
                    ExternalConnection.provider.in_(["serp_provider", "serp"])
                ).first()
                if serp_conn:
                    serp_api_key = serp_conn.get_api_key() or ""
                    display_name = (serp_conn.provider_account_name or "SerpApi").strip().lower()
                    if "openserp" in display_name:
                        serp_provider_name = "openserp"
                    else:
                        serp_provider_name = "serpapi"
            except Exception as e:
                print(f"[COMPETITOR DISCOVERY] DB key load error: {e}", flush=True)

        if not serp_api_key:
            serp_api_key = os.environ.get("SERP_API_KEY", "").strip()

        if not serp_api_key:
            return {
                "has_serp_provider": False,
                "provider_name": "None",
                "message": "SERP provider is configured but the API key could not be loaded. Please re-save your SERP integration.",
                "suggested_competitors": suggested,
                "confirmed_competitors": confirmed,
                "all_competitors": existing_competitors,
            }

        # ── Load project keywords (cap at 20 to control API spend) ───────────────
        MAX_KEYWORDS = 20
        keywords_records = db.query(Keyword).filter(
            Keyword.project_id == project.id
        ).limit(MAX_KEYWORDS * 2).all()
        # Filter for genuine search-intent keywords (BUG 3)
        keyword_list = [
            k.keyword.strip() for k in keywords_records
            if k.keyword and k.keyword.strip() and _is_valid_competitor_keyword(k.keyword.strip())
        ][:MAX_KEYWORDS]

        target_domain = _extract_root_domain(project.domain or "")

        # ── Project discovery metadata & SERP credit cooldown check (BUG 5) ────────
        import hashlib
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
        meta_file = os.path.join(proj_dir, "discovery_meta.json")
        COOLDOWN_HOURS = 12.0
        now_ts = datetime.utcnow().timestamp()

        kw_hash_src = "|".join(sorted(keyword_list)) + "|" + str(location or {})
        kw_hash = hashlib.md5(kw_hash_src.encode("utf-8")).hexdigest()

        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    meta_data = _json.load(mf)
                last_run = meta_data.get("last_discovery_run_at", 0)
                last_hash = meta_data.get("last_keyword_hash", "")
                elapsed_hours = (now_ts - last_run) / 3600.0
                if elapsed_hours < COOLDOWN_HOURS and last_hash == kw_hash:
                    remaining_hours = round(COOLDOWN_HOURS - elapsed_hours, 1)
                    cooldown_msg = f"Competitor discovery was recently run for this keyword/location set. Cooldown active for another {remaining_hours} hour(s) to preserve SERP credits."
                    print(f"[COMPETITOR DISCOVERY] {cooldown_msg}", flush=True)
                    return {
                        "has_serp_provider": True,
                        "provider_name": serp_status["provider_name"],
                        "message": cooldown_msg,
                        "suggested_competitors": suggested,
                        "confirmed_competitors": confirmed,
                        "all_competitors": existing_competitors,
                    }
            except Exception as meta_err:
                print(f"[COMPETITOR DISCOVERY] Meta file read error: {meta_err}", flush=True)

        print(
            f"[COMPETITOR DISCOVERY] Project: {project.name!r} | Domain: {target_domain} | "
            f"Provider: {serp_provider_name} | Keywords: {len(keyword_list)}",
            flush=True
        )

        if not keyword_list:
            return {
                "has_serp_provider": True,
                "provider_name": serp_status["provider_name"],
                "message": "No tracked keywords found for this project. Add keywords first, then run Find Competitors again.",
                "suggested_competitors": suggested,
                "confirmed_competitors": confirmed,
                "all_competitors": existing_competitors,
            }

        # Instantiate adapter
        try:
            adapter = SERPAdapterFactory.get(serp_provider_name, serp_api_key)
        except Exception as e:
            return {
                "has_serp_provider": False,
                "provider_name": serp_status["provider_name"],
                "message": f"Failed to initialise SERP adapter: {e}",
                "suggested_competitors": suggested,
                "confirmed_competitors": confirmed,
                "all_competitors": existing_competitors,
            }

        # -- Resolve country / language: location payload > project settings --------
        # Location from the user's modal selection takes priority over project defaults.
        loc_country_code = None
        serp_location_string = None  # e.g. "Ahmedabad,Gujarat,India" for SerpApi location= param

        if location:
            loc_country_code = (location.get("country_code") or "").strip().upper() or None
            loc_country_name = (location.get("country") or "").strip()
            loc_state = (location.get("state") or "").strip()
            loc_city = (location.get("city") or "").strip()

            # Build SerpApi location= string (city, state, country order)
            loc_parts = [p for p in [loc_city, loc_state, loc_country_name] if p]
            if loc_parts:
                serp_location_string = ",".join(loc_parts)

            # Derive country code from location payload if not directly provided
            if not loc_country_code and loc_country_name:
                _NAME_CODE = {
                    "india": "in", "united states": "us", "usa": "us", "united kingdom": "gb",
                    "uk": "gb", "canada": "ca", "australia": "au", "germany": "de",
                    "france": "fr", "spain": "es", "italy": "it", "japan": "jp",
                    "brazil": "br", "mexico": "mx", "netherlands": "nl", "singapore": "sg",
                    "united arab emirates": "ae", "uae": "ae", "new zealand": "nz",
                    "south africa": "za", "pakistan": "pk", "bangladesh": "bd",
                    "indonesia": "id", "malaysia": "my", "thailand": "th",
                    "vietnam": "vn", "philippines": "ph", "south korea": "kr",
                    "china": "cn", "russia": "ru", "turkey": "tr", "poland": "pl",
                    "sweden": "se", "norway": "no", "denmark": "dk", "finland": "fi",
                    "switzerland": "ch", "austria": "at", "belgium": "be",
                    "portugal": "pt", "greece": "gr", "czech republic": "cz",
                    "argentina": "ar", "chile": "cl", "colombia": "co", "peru": "pe",
                    "kenya": "ke", "nigeria": "ng", "egypt": "eg", "ghana": "gh",
                }
                loc_country_code = _NAME_CODE.get(loc_country_name.lower())

        country_code = (loc_country_code or _normalize_country(project.target_country or "")).lower()
        lang_code = _normalize_lang(project.target_language or "")
        device = (project.target_device or "Desktop").strip()

        print(
            f"[COMPETITOR DISCOVERY] Location: {serp_location_string!r} | "
            f"gl={country_code} | hl={lang_code}",
            flush=True
        )

        # -- GSC supplemental keywords (honest: GSC returns YOUR site's queries, not competitors) --
        # These are real queries your site appears for in Google Search.
        # We add them as extra keywords to run through SERP discovery, expanding coverage.
        gsc_supplemental_keywords = []
        try:
            gsc_conn = db.query(ExternalConnection).filter(
                ExternalConnection.provider.in_(["google", "gsc", "google_search_console"])
            ).first()
            if gsc_conn:
                gsc_token = gsc_conn.get_api_key() or ""
                if gsc_token:
                    from app.providers.gsc_provider import GoogleSearchConsoleProvider
                    gsc = GoogleSearchConsoleProvider(timeout=15.0)
                    site_url = f"sc-domain:{_extract_root_domain(project.domain or '')}"
                    gsc_rows = gsc.get_search_analytics(
                        site_url=site_url,
                        days=30,
                        access_token=gsc_token,
                        dimensions=["query"]
                    )
                    gsc_queries = [
                        r["query"] for r in gsc_rows
                        if r.get("query") and isinstance(r["query"], str) and r["query"].strip()
                    ]
                    gsc_supplemental_keywords = list(dict.fromkeys(gsc_queries))[:10]
                    if gsc_supplemental_keywords:
                        print(
                            f"[COMPETITOR DISCOVERY] GSC supplemental keywords: "
                            f"{len(gsc_supplemental_keywords)} added to SERP keyword list",
                            flush=True
                        )
        except Exception as gsc_err:
            print(f"[COMPETITOR DISCOVERY] GSC supplemental query (non-fatal): {gsc_err}", flush=True)

        # ── Per-keyword SERP fetch → collect all organic domains ─────────────────
        # Structure: { domain: { "appearances": int, "best_position": int,
        #                        "keywords": [str], "title": str, "url": str } }
        # Merge GSC supplemental keywords into keyword list (deduplicated, cap still at MAX_KEYWORDS)
        for gsc_kw in gsc_supplemental_keywords:
            if gsc_kw not in keyword_list and len(keyword_list) < MAX_KEYWORDS:
                keyword_list.append(gsc_kw)

        domain_candidates: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        for kw in keyword_list:
            print(f"[COMPETITOR DISCOVERY] Querying SERP for keyword: {kw!r}", flush=True)
            try:
                # Build raw SerpApi request to retrieve ALL organic results.
                # We cannot reuse adapter.search() directly because it filters to
                # a specific domain.  We call the same endpoint with num=10 (top 10
                # results) to keep credit usage minimal.
                if serp_provider_name == "serpapi":
                    params = {
                        "engine": "google",
                        "q": kw,
                        "api_key": serp_api_key,
                        "gl": country_code,
                        "hl": lang_code,
                        "num": "10",
                        "device": device.lower(),
                    }
                    # Add city/region targeting when a location was selected by the user
                    if serp_location_string:
                        params["location"] = serp_location_string
                    url = "https://serpapi.com/search.json?" + _urlparse.urlencode(params)
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "SEO-Intelligence-Platform/1.0"},
                        method="GET"
                    )
                    with urllib.request.urlopen(req, timeout=25.0) as resp:
                        data = _json.loads(resp.read().decode("utf-8"))
                    organic = data.get("organic_results", [])
                else:
                    # OpenSERP path — reuse adapter.search() with a dummy domain,
                    # but parse the raw result differently.
                    # For OpenSERP we must call the underlying endpoint directly.
                    endpoint = f"{adapter.base_url}/api/v1/google/search"
                    payload_os = _json.dumps({
                        "query": kw,
                        "country": country_code,
                        "language": lang_code,
                        "limit": 10,
                    }).encode("utf-8")
                    headers_os = {
                        "Content-Type": "application/json",
                        "User-Agent": "SEO-Intelligence-Platform/1.0",
                    }
                    if serp_api_key:
                        headers_os["Authorization"] = f"Bearer {serp_api_key}"
                    req_os = urllib.request.Request(endpoint, data=payload_os, headers=headers_os, method="POST")
                    with urllib.request.urlopen(req_os, timeout=25.0) as resp:
                        data = _json.loads(resp.read().decode("utf-8"))
                    raw = data.get("results") or data.get("organic") or []
                    # Normalise OpenSERP result schema to match SerpApi style
                    organic = [
                        {
                            "link": r.get("url") or r.get("link") or "",
                            "title": r.get("title") or r.get("name") or "",
                            "displayed_link": r.get("displayed_link") or r.get("url") or "",
                        }
                        for r in raw
                    ]

                print(f"[COMPETITOR DISCOVERY]   -> {len(organic)} organic results for {kw!r}", flush=True)

                # Extract domains from results
                for idx, result in enumerate(organic, start=1):
                    result_url = result.get("link") or result.get("url") or ""
                    dom = _extract_root_domain(result_url)
                    if not dom:
                        continue
                    if dom == target_domain:
                        continue
                    if _is_blacklisted(dom):
                        continue

                    if dom not in domain_candidates:
                        domain_candidates[dom] = {
                            "appearances": 0,
                            "best_position": idx,
                            "keywords": [],
                            "title": result.get("title") or dom,
                            "url": result_url,
                        }

                    entry = domain_candidates[dom]
                    entry["appearances"] += 1
                    entry["keywords"].append(kw)
                    if idx < entry["best_position"]:
                        entry["best_position"] = idx

            except urllib.error.HTTPError as http_err:
                body = ""
                try:
                    body = http_err.read().decode("utf-8", errors="replace")[:200]
                except Exception:
                    pass
                msg = f"SERP HTTP {http_err.code} for keyword '{kw}': {body}"
                print(f"[COMPETITOR DISCOVERY] ERROR: {msg}", flush=True)
                errors.append(msg)

            except Exception as ex:
                msg = f"SERP error for keyword '{kw}': {ex}"
                print(f"[COMPETITOR DISCOVERY] ERROR: {msg}", flush=True)
                errors.append(msg)

        # ── All keywords failed → surface error instead of silent empty list ─────
        if errors and not domain_candidates:
            error_summary = errors[0] if len(errors) == 1 else f"{len(errors)} keyword queries failed. First error: {errors[0]}"
            return {
                "has_serp_provider": True,
                "provider_name": serp_status["provider_name"],
                "message": f"SERP discovery failed: {error_summary}",
                "serp_errors": errors,
                "suggested_competitors": suggested,
                "confirmed_competitors": confirmed,
                "all_competitors": existing_competitors,
            }

        print(
            f"[COMPETITOR DISCOVERY] Candidates before DB upsert: {len(domain_candidates)} domains "
            f"(errors for {len(errors)} keyword(s))",
            flush=True
        )

        # ── Score candidates: appearances × (11 - best_position), clamped ────────
        def _score(entry: Dict[str, Any]) -> float:
            pos_factor = max(1, 11 - entry["best_position"])  # top-10 range → 10..1
            return float(entry["appearances"] * pos_factor)

        sorted_candidates = sorted(
            domain_candidates.items(),
            key=lambda kv: _score(kv[1]),
            reverse=True,
        )

        # ── Upsert Competitor records ─────────────────────────────────────────────
        now = datetime.utcnow()
        created_count = 0
        updated_count = 0

        for dom, info in sorted_candidates:
            existing_comp = db.query(Competitor).filter(
                Competitor.project_id == project.id,
                Competitor.domain == dom,
            ).first()

            kw_json = _json.dumps(list(dict.fromkeys(info["keywords"])))  # deduplicated
            score = round(_score(info), 1)

            if existing_comp:
                # Preserve Confirmed and Ignored — never overwrite user decisions
                if existing_comp.status in ("Confirmed", "Ignored", "Removed"):
                    print(
                        f"[COMPETITOR DISCOVERY]   Preserving {existing_comp.status} competitor: {dom}",
                        flush=True
                    )
                    continue

                # Update Suggested with fresh discovery metadata
                existing_comp.discovered_keywords = kw_json
                existing_comp.search_appearances = info["appearances"]
                existing_comp.relevance_score = score
                existing_comp.last_checked = now
                existing_comp.discovery_source = "SERP Analysis"
                db.commit()
                updated_count += 1
                print(f"[COMPETITOR DISCOVERY]   Updated Suggested: {dom}", flush=True)
            else:
                # Require minimum relevance threshold for new Suggested competitors (BUG 4)
                # appearance count >= 2 OR score >= 15.0
                if info["appearances"] < 2 and score < 15.0:
                    print(
                        f"[COMPETITOR DISCOVERY]   Skipped low-relevance domain: {dom} "
                        f"(appearances={info['appearances']}, score={score})",
                        flush=True
                    )
                    continue

                # Create new Suggested competitor
                new_comp = Competitor(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    name=info.get("title") or dom,
                    domain=dom,
                    url=info.get("url") or f"https://{dom}",
                    location=serp_location_string or "Market Candidate",
                    geographic_level="City" if (location and location.get("city")) else ("State" if (location and location.get("state")) else "Global"),
                    relevance_score=score,
                    keyword_overlap=None,
                    search_appearances=info["appearances"],
                    status="Suggested",
                    is_primary=False,
                    discovery_source="SERP Analysis",
                    discovered_keywords=kw_json,
                    notes=f"Auto-discovered via SERP Analysis - appeared for: {', '.join(info['keywords'][:3])}",
                    first_discovered=now,
                    last_checked=now,
                )
                db.add(new_comp)
                db.commit()
                db.refresh(new_comp)
                suggested.append(new_comp)
                created_count += 1
                print(f"[COMPETITOR DISCOVERY]   Created Suggested: {dom} (score={score})", flush=True)

        # Save project discovery metadata timestamp and keyword hash (BUG 5)
        try:
            os.makedirs(proj_dir, exist_ok=True)
            with open(meta_file, "w", encoding="utf-8") as mf:
                _json.dump({
                    "last_discovery_run_at": now_ts,
                    "last_location": location,
                    "last_keyword_hash": kw_hash
                }, mf)
        except Exception as meta_err:
            print(f"[COMPETITOR DISCOVERY] Meta file write error: {meta_err}", flush=True)

        print(
            f"[COMPETITOR DISCOVERY] Complete. Created: {created_count}, Updated: {updated_count}, "
            f"SERP errors: {len(errors)}",
            flush=True
        )

        # Refresh suggested list from DB to include any updates
        suggested = db.query(Competitor).filter(
            Competitor.project_id == project.id,
            Competitor.status == "Suggested"
        ).order_by(Competitor.relevance_score.desc()).all()

        confirmed = db.query(Competitor).filter(
            Competitor.project_id == project.id,
            Competitor.status == "Confirmed"
        ).order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()

        all_competitors = db.query(Competitor).filter(
            Competitor.project_id == project.id
        ).order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()

        message = f"Discovered {created_count} new competitor(s) via SERP Analysis."
        if updated_count:
            message += f" Updated {updated_count} existing suggestion(s)."
        if errors:
            message += f" ({len(errors)} keyword(s) could not be queried.)"
        if not keyword_list:
            message = "No keywords found."

        return {
            "has_serp_provider": True,
            "provider_name": serp_status["provider_name"],
            "message": message,
            "serp_errors": errors if errors else None,
            "suggested_competitors": suggested,
            "confirmed_competitors": confirmed,
            "all_competitors": all_competitors,
        }

    # ── FALLBACK: static imported competitors.json on disk ──────────────────────
    if not suggested:
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
        comp_file = os.path.join(proj_dir, "competitors.json")
        if os.path.exists(comp_file):
            try:
                with open(comp_file, "r") as cf:
                    imported_comps = _json.load(cf)
                target_dom = normalize_domain(project.domain)
                for item in imported_comps:
                    dom = normalize_domain(item.get("domain") or item.get("url") or "")
                    if dom and dom != target_dom:
                        existing_check = db.query(Competitor).filter(
                            Competitor.project_id == project.id,
                            Competitor.domain == dom
                        ).first()
                        if not existing_check:
                            rel_val = float(item["relevance_score"]) if item.get("relevance_score") is not None else None
                            kw_val = int(item["keyword_overlap"]) if item.get("keyword_overlap") is not None else None
                            search_val = int(item["search_appearances"]) if item.get("search_appearances") is not None else None
                            new_comp = Competitor(
                                id=str(uuid.uuid4()),
                                project_id=project.id,
                                name=item.get("name") or dom,
                                domain=dom,
                                url=item.get("url") or f"https://{dom}",
                                location=item.get("location") or "Market Candidate",
                                geographic_level=item.get("geographic_level") or "City",
                                relevance_score=rel_val,
                                keyword_overlap=kw_val,
                                search_appearances=search_val,
                                status="Suggested",
                                is_primary=False,
                                discovery_source="Imported SERP Dataset",
                                notes=item.get("notes") or "Imported competitor candidate",
                                first_discovered=datetime.utcnow(),
                                last_checked=datetime.utcnow()
                            )
                            db.add(new_comp)
                            db.commit()
                            suggested.append(new_comp)
            except Exception as e:
                print(f"[COMPETITOR DISCOVERY ERROR] Fallback import failed: {e}", flush=True)

    return {
        "has_serp_provider": serp_status["has_serp_provider"],
        "provider_name": serp_status["provider_name"],
        "message": serp_status["message"],
        "suggested_competitors": suggested,
        "confirmed_competitors": confirmed,
        "all_competitors": existing_competitors,
    }


from app.models.competitor_ranking import CompetitorRanking

from sqlalchemy import func

def perform_keyword_gap_analysis(project: Project, db: Session, competitor_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs Keyword Gap Analysis comparing Target Website keywords against Confirmed Competitors.
    Production rule: Based 100% on actual project database data and verified CompetitorRanking records.
    Never fabricates keywords, positions, or search metrics.
    """
    comp_query = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        func.lower(Competitor.status) == "confirmed"
    )
    if competitor_id:
        comp_query = comp_query.filter(Competitor.id == competitor_id)
        
    confirmed_competitors = comp_query.all()

    # Load all project keywords
    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    
    # Load all competitor rankings for this project
    comp_rankings_query = db.query(CompetitorRanking).filter(
        CompetitorRanking.project_id == project.id
    )
    if competitor_id:
        comp_rankings_query = comp_rankings_query.filter(CompetitorRanking.competitor_id == competitor_id)
        
    comp_rankings = comp_rankings_query.order_by(CompetitorRanking.checked_at.desc()).all()

    # Map latest competitor ranking by (keyword.lower(), competitor_id)
    latest_comp_rankings: Dict[Tuple[str, str], CompetitorRanking] = {}
    for cr in comp_rankings:
        key = (cr.keyword.strip().lower(), cr.competitor_id)
        if key not in latest_comp_rankings:
            latest_comp_rankings[key] = cr

    # Map confirmed competitors by ID
    comp_map = {c.id: c for c in confirmed_competitors}

    gap_data = []
    processed_keys = set()

    # 1. Process target website keywords
    for kw_record in keywords:
        if not kw_record.keyword:
            continue
        
        kw_clean = kw_record.keyword.strip()
        kw_lower = kw_clean.lower()
        target_pos = kw_record.position  # 1-indexed int or None

        # For each confirmed competitor, evaluate the gap
        if confirmed_competitors:
            for comp in confirmed_competitors:
                processed_keys.add((kw_lower, comp.id))
                comp_ranking = latest_comp_rankings.get((kw_lower, comp.id))
                comp_pos = comp_ranking.position if comp_ranking else None

                # Calculate mathematical gap: competitor_pos - target_pos
                # Positive (+8) => You are 8 spots ahead (e.g. You #1, Comp #9)
                # Negative (-8) => Competitor is 8 spots ahead (e.g. You #9, Comp #1)
                pos_diff = None
                diff_display = "N/A"
                if target_pos is not None and comp_pos is not None:
                    pos_diff = comp_pos - target_pos
                    diff_display = f"+{pos_diff}" if pos_diff > 0 else str(pos_diff)

                # Determine opportunity level
                if comp_pos is not None and (target_pos is None or target_pos > comp_pos):
                    opportunity = "HIGH"  # Competitor ranks ahead or you are unranked
                elif target_pos is not None and comp_pos is not None and target_pos <= comp_pos:
                    opportunity = "LOW"   # You outrank the competitor
                elif target_pos is not None and comp_pos is None:
                    opportunity = "MEDIUM" # You rank, competitor is unranked
                else:
                    opportunity = "NOT_CHECKED"

                gap_data.append({
                    "keyword": kw_clean,
                    "competitor_id": comp.id,
                    "competitor_name": comp.name,
                    "competitor_domain": comp.domain,
                    "target_position": target_pos,
                    "target_position_display": f"#{target_pos}" if target_pos is not None else "Not Ranking",
                    "competitor_position": comp_pos,
                    "competitor_position_display": f"#{comp_pos}" if comp_pos is not None else "Data Unavailable",
                    "position_difference": pos_diff,
                    "position_difference_display": diff_display,
                    "search_volume": kw_record.search_volume or 0,
                    "keyword_difficulty": kw_record.difficulty or 0,
                    "opportunity_level": opportunity,
                    "ranking_url": comp_ranking.ranking_url if comp_ranking else None,
                    "source": comp_ranking.source if comp_ranking else "None",
                    "source_display": (comp_ranking.source.replace("_", " ").title() if comp_ranking else "Not Checked"),
                    "checked_at": comp_ranking.checked_at.isoformat() if (comp_ranking and comp_ranking.checked_at) else None,
                    "recommended_action": f"Optimize page content targeting '{kw_clean}'"
                })
        else:
            # No confirmed competitors configured
            gap_data.append({
                "keyword": kw_clean,
                "competitor_id": None,
                "competitor_name": "No Competitor Configured",
                "competitor_domain": None,
                "target_position": target_pos,
                "target_position_display": f"#{target_pos}" if target_pos is not None else "Not Ranking",
                "competitor_position": None,
                "competitor_position_display": "Data Unavailable",
                "position_difference": None,
                "position_difference_display": "N/A",
                "search_volume": kw_record.search_volume or 0,
                "keyword_difficulty": kw_record.difficulty or 0,
                "opportunity_level": "NOT_CHECKED",
                "ranking_url": None,
                "source": "None",
                "source_display": "Not Checked",
                "checked_at": None,
                "recommended_action": f"Confirm competitors to compare rankings for '{kw_clean}'"
            })

    # 2. Add any keywords that competitors rank for which are NOT yet in the project's keywords table
    for (kw_lower, comp_id), comp_ranking in latest_comp_rankings.items():
        if (kw_lower, comp_id) in processed_keys:
            continue
        
        comp = comp_map.get(comp_id)
        if not comp:
            continue

        comp_pos = comp_ranking.position
        gap_data.append({
            "keyword": comp_ranking.keyword,
            "competitor_id": comp.id,
            "competitor_name": comp.name,
            "competitor_domain": comp.domain,
            "target_position": None,
            "target_position_display": "Not Ranking",
            "competitor_position": comp_pos,
            "competitor_position_display": f"#{comp_pos}" if comp_pos is not None else "Data Unavailable",
            "position_difference": None,
            "position_difference_display": "N/A",
            "search_volume": 0,
            "keyword_difficulty": 0,
            "opportunity_level": "HIGH" if comp_pos is not None else "NOT_CHECKED",
            "ranking_url": comp_ranking.ranking_url,
            "source": comp_ranking.source,
            "source_display": comp_ranking.source.replace("_", " ").title(),
            "checked_at": comp_ranking.checked_at.isoformat() if comp_ranking.checked_at else None,
            "recommended_action": f"Create targeted content to compete for '{comp_ranking.keyword}'"
        })

    # Summary metrics
    missing_count = sum(1 for g in gap_data if g["opportunity_level"] == "HIGH")
    winning_count = sum(1 for g in gap_data if g["opportunity_level"] == "LOW")
    shared_count = sum(1 for g in gap_data if g["target_position"] is not None and g["competitor_position"] is not None)
    
    return {
        "project_id": project.id,
        "target_domain": normalize_domain(project.domain or project.url or ""),
        "confirmed_competitors_count": len(confirmed_competitors),
        "confirmed_competitors": [
            {
                "id": c.id,
                "name": c.name,
                "domain": c.domain,
                "location": c.location,
                "is_primary": c.is_primary
            } for c in confirmed_competitors
        ],
        "summary": {
            "total_keywords_analyzed": len(gap_data),
            "high_opportunity_keywords": missing_count,
            "winning_keywords": winning_count,
            "shared_keywords": shared_count,
        },
        "keyword_gap": gap_data,
        "gap_items": gap_data,
        "message": "Keyword gap analysis complete." if gap_data else "No keyword dataset or verified competitor data available for gap analysis."
    }


def store_competitor_ranking(
    db: Session,
    project_id: str,
    competitor_id: str,
    keyword: str,
    position: Optional[int],
    ranking_url: Optional[str] = None,
    search_engine: str = "google",
    country: Optional[str] = None,
    location: Optional[str] = None,
    device: str = "desktop",
    source: str = "serp_provider",
    checked_at: Optional[datetime] = None,
) -> CompetitorRanking:
    """
    Persist a single verified competitor ranking record.
    """
    if checked_at is None:
        checked_at = datetime.utcnow()

    rec = CompetitorRanking(
        id=str(uuid.uuid4()),
        project_id=project_id,
        competitor_id=competitor_id,
        keyword=keyword.strip(),
        position=position,
        ranking_url=ranking_url,
        search_engine=search_engine.lower() if search_engine else "google",
        country=country,
        location=location,
        device=device.lower() if device else "desktop",
        source=source,
        checked_at=checked_at,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def bulk_store_competitor_rankings(
    db: Session,
    rankings: List[Dict[str, Any]]
) -> int:
    """
    Bulk persist verified competitor ranking records.
    """
    count = 0
    now = datetime.utcnow()
    for r in rankings:
        rec = CompetitorRanking(
            id=str(uuid.uuid4()),
            project_id=r["project_id"],
            competitor_id=r["competitor_id"],
            keyword=r["keyword"].strip(),
            position=r.get("position"),
            ranking_url=r.get("ranking_url"),
            search_engine=r.get("search_engine", "google").lower(),
            country=r.get("country"),
            location=r.get("location"),
            device=r.get("device", "desktop").lower(),
            source=r.get("source", "serp_provider"),
            checked_at=r.get("checked_at") or now,
        )
        db.add(rec)
        count += 1
    db.commit()
    return count

