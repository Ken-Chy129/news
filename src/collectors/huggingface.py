"""HuggingFace trending models collector."""

from __future__ import annotations

from typing import List

import httpx

from .base import BaseCollector, RawItem

HF_API_URL = "https://huggingface.co/api/models"


class HuggingFaceCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        top_n = self.config.get("top_n", 10)

        print(f"[{self.name}] Fetching trending models...")
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(HF_API_URL, params={
                    "sort": "trendingScore",
                    "limit": top_n,
                })
                resp.raise_for_status()
                models = resp.json()
        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        items: List[RawItem] = []
        for m in models:
            model_id = m.get("modelId", m.get("id", ""))
            if not model_id:
                continue

            items.append(self._make_item(
                title=model_id,
                url=f"https://huggingface.co/{model_id}",
                content=m.get("pipeline_tag", ""),
                extra={
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                },
            ))

        print(f"[{self.name}] Collected {len(items)} items")
        return items
