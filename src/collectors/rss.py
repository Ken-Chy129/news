"""Generic RSS/Atom feed collector with freshness filtering."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Optional

import feedparser

from .base import BaseCollector, RawItem


def _parse_published(date_str: str) -> Optional[datetime]:
    """Try to parse a date string from RSS into a timezone-aware datetime."""
    if not date_str:
        return None
    # feedparser's time struct
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    # ISO 8601 fallback
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


class RSSCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        url = self.config.get("url", "")
        if not url:
            print(f"[{self.name}] No URL configured, skipping")
            return []

        # max_age_days: only include items published within this many days (default 2)
        max_age_days = self.config.get("max_age_days", 2)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        print(f"[{self.name}] Fetching RSS: {url}")
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            print(f"[{self.name}] Failed to parse feed: {feed.bozo_exception}")
            return []

        items: List[RawItem] = []
        skipped_old = 0
        max_items = self.config.get("top_n", 30)

        for entry in feed.entries[:max_items * 2]:  # scan more to account for filtered items
            if len(items) >= max_items:
                break

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            published_str = entry.get("published", entry.get("updated", ""))
            published_dt = _parse_published(published_str)

            # Freshness filter: skip items older than cutoff
            if published_dt and published_dt < cutoff:
                skipped_old += 1
                continue

            summary = entry.get("summary", "")
            if "<" in summary:
                from bs4 import BeautifulSoup
                summary = BeautifulSoup(summary, "html.parser").get_text(separator=" ", strip=True)
            if len(summary) > 500:
                summary = summary[:500] + "..."

            items.append(self._make_item(
                title=title,
                url=link,
                content=summary,
                published_at=published_str,
            ))

        if skipped_old:
            print(f"[{self.name}] Skipped {skipped_old} items older than {max_age_days} days")
        print(f"[{self.name}] Collected {len(items)} items")
        return items
