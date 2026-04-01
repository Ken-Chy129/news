"""Hacker News collector using the official Firebase API."""

from __future__ import annotations

from typing import List

import httpx

from .base import BaseCollector, RawItem

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


class HackerNewsCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        top_n = self.config.get("top_n", 30)
        filter_keywords = [kw.lower() for kw in self.config.get("filter_keywords", [])]

        print(f"[{self.name}] Fetching top stories...")
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(HN_TOP_URL)
                resp.raise_for_status()
                story_ids = resp.json()

                # Fetch more stories than needed since we'll filter
                fetch_count = min(len(story_ids), top_n * 3 if filter_keywords else top_n)
                items: List[RawItem] = []

                for sid in story_ids[:fetch_count]:
                    if len(items) >= top_n:
                        break

                    item_resp = client.get(HN_ITEM_URL.format(sid))
                    if item_resp.status_code != 200:
                        continue

                    story = item_resp.json()
                    if not story or story.get("type") != "story":
                        continue

                    title = story.get("title", "")
                    url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")

                    if filter_keywords:
                        text = f"{title} {url}".lower()
                        if not any(kw in text for kw in filter_keywords):
                            continue

                    items.append(self._make_item(
                        title=title,
                        url=url,
                        extra={"score": story.get("score", 0), "comments": story.get("descendants", 0)},
                    ))

        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        print(f"[{self.name}] Collected {len(items)} items")
        return items
