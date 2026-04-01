"""NewsNow API collector for platform trending/hot lists.

Uses the same API as TrendRadar: https://github.com/ourongxing/newsnow
Supports: weibo, douyin, zhihu, toutiao, bilibili, baidu, etc.
"""

from __future__ import annotations

from typing import List

import httpx

from .base import BaseCollector, RawItem

DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"


class NewsNowCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        platform_id = self.config.get("platform_id", "")
        if not platform_id:
            print(f"[{self.name}] No platform_id configured, skipping")
            return []

        api_url = self.config.get("api_url", DEFAULT_API_URL)
        top_n = self.config.get("top_n", 30)
        url = f"{api_url}?id={platform_id}&latest"

        print(f"[{self.name}] Fetching {platform_id} via NewsNow API...")
        try:
            with httpx.Client(timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; daily-ai-news/1.0)",
                "Accept": "application/json",
            }) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        status = data.get("status", "")
        if status not in ("success", "cache"):
            print(f"[{self.name}] Unexpected status: {status}")
            return []

        items: List[RawItem] = []
        for i, entry in enumerate(data.get("items", [])[:top_n], 1):
            title = entry.get("title", "")
            if not title or not isinstance(title, str):
                continue

            entry_url = entry.get("url", "")
            mobile_url = entry.get("mobileUrl", "")

            items.append(self._make_item(
                title=title.strip(),
                url=entry_url or mobile_url,
                extra={"rank": i, "platform": platform_id},
            ))

        print(f"[{self.name}] Collected {len(items)} items")
        return items
