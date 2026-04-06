"""Reddit collector using the public JSON API (no auth required)."""

from __future__ import annotations

from typing import List

import httpx

from .base import BaseCollector, RawItem


class RedditCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        subreddit = self.config.get("subreddit", "MachineLearning")
        top_n = self.config.get("top_n", 15)
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={top_n}"

        print(f"[{self.name}] Fetching r/{subreddit}...")
        try:
            with httpx.Client(timeout=15, headers={"User-Agent": "daily-ai-news/1.0"}) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        items: List[RawItem] = []
        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})
            if d.get("stickied"):
                continue

            title = d.get("title", "").strip()
            permalink = d.get("permalink", "")
            post_url = f"https://www.reddit.com{permalink}" if permalink else ""
            if not title or not post_url:
                continue

            items.append(self._make_item(
                title=title,
                url=post_url,
                content=d.get("selftext", "")[:2000],
                extra={"score": d.get("score", 0), "comments": d.get("num_comments", 0)},
            ))

        print(f"[{self.name}] Collected {len(items)} items")
        return items
