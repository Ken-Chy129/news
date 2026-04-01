"""Base collector and data structures."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class RawItem:
    """A single news item collected from any source."""
    title: str
    url: str
    source: str  # e.g. "Hacker News", "ArXiv CS.AI"
    category: str  # e.g. "paper", "trending", "blog"
    content: str = ""  # optional snippet / abstract
    published_at: Optional[str] = None  # ISO 8601 string
    extra: dict = field(default_factory=dict)  # rank, score, stars, etc.

    def to_dict(self) -> dict:
        return asdict(self)


class BaseCollector(abc.ABC):
    """Abstract base class for all collectors."""

    def __init__(self, source_config: dict):
        self.config = source_config
        self.name = source_config.get("name", self.__class__.__name__)
        self.category = source_config.get("category", "industry")

    @abc.abstractmethod
    def collect(self) -> List[RawItem]:
        """Collect items from the source. Returns a list of RawItem."""
        ...

    def _make_item(self, title: str, url: str, **kwargs) -> RawItem:
        return RawItem(
            title=title.strip(),
            url=url.strip(),
            source=self.name,
            category=self.category,
            **kwargs,
        )
