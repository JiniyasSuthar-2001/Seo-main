import uuid
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class LinkRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    crawl_id: Optional[str] = None
    source_url: str = ""
    target_url: str = ""
    normalized_source_url: str = ""
    normalized_target_url: str = ""
    link_scope: str = "internal"  # internal | external
    link_type: str = "hyperlink"  # hyperlink | image_link | nav_link | button | social | email | telephone
    anchor_text: str = ""
    rel: str = "follow"
    status_code: Optional[int] = None
    status_text: Optional[str] = None
    redirect_target: Optional[str] = None
    redirect_chain: List[str] = field(default_factory=list)
    final_target_url: Optional[str] = None
    content_type: Optional[str] = None
    is_internal: bool = True
    is_external: bool = False
    is_broken: bool = False
    is_redirect: bool = False
    is_nofollow: bool = False
    is_sponsored: bool = False
    is_ugc: bool = False

    # Semantic DOM location
    source_section: str = "other"  # navigation | header | main | article | sidebar | footer | other
    nearest_heading: Optional[str] = None
    heading_level: Optional[int] = None
    paragraph_index: Optional[int] = None
    sentence_index: Optional[int] = None
    link_index_on_page: Optional[int] = None

    # Context surrounding the link
    context_before: str = ""
    context_text: str = ""
    context_after: str = ""
    html_snippet: str = ""

    # Timestamps
    discovered_at: Optional[str] = field(default_factory=lambda: datetime.utcnow().isoformat())
    checked_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinkRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
