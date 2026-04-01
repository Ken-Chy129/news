"""Generic web page scraper for sites without RSS feeds.

Configured via CSS selectors in config.yaml to extract article links and titles.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, RawItem


class WebScraperCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        url = self.config.get("url", "")
        if not url:
            print(f"[{self.name}] No URL configured, skipping")
            return []

        link_selector = self.config.get("link_selector", "a")
        base_url = self.config.get("base_url", "")
        top_n = self.config.get("top_n", 10)

        print(f"[{self.name}] Scraping: {url}")
        try:
            with httpx.Client(timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; daily-ai-news/1.0)",
            }) as client:
                resp = client.get(url)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(link_selector)

        items: List[RawItem] = []
        seen_urls = set()

        for el in elements:
            if len(items) >= top_n:
                break

            # Get the link - either the element itself or find an <a> inside it
            if el.name == "a":
                a_tag = el
            else:
                a_tag = el.find("a")

            if not a_tag:
                continue

            href = a_tag.get("href", "").strip()
            if not href:
                continue

            # Resolve relative URLs
            if href.startswith("/"):
                href = base_url.rstrip("/") + href

            if href in seen_urls:
                continue
            seen_urls.add(href)

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            items.append(self._make_item(
                title=title,
                url=href,
            ))

        print(f"[{self.name}] Collected {len(items)} items")
        return items
