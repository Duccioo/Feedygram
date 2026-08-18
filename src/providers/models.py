from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class FeedItem:
    id: str
    title: str
    link: str
    published: Optional[datetime] = None
    summary: Optional[str] = ""
    source_link: Optional[str] = None
    tags: List[str] = field(default_factory=list)
