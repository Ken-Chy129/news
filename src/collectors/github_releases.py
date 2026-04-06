"""GitHub releases collector for tracking project updates."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import httpx

from .base import BaseCollector, RawItem


class GitHubReleasesCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        repo = self.config.get("repo", "")
        if not repo:
            print(f"[{self.name}] No repo configured, skipping")
            return []

        max_age_days = self.config.get("max_age_days", 3)
        top_n = self.config.get("top_n", 5)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        url = f"https://api.github.com/repos/{repo}/releases"
        print(f"[{self.name}] Fetching releases for {repo}...")

        try:
            with httpx.Client(timeout=15, headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "daily-ai-news/1.0",
            }) as client:
                resp = client.get(url, params={"per_page": 10})
                resp.raise_for_status()
                releases = resp.json()
        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        items: List[RawItem] = []
        for rel in releases[:top_n]:
            published = rel.get("published_at", "")
            if published:
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except ValueError:
                    pass

            tag = rel.get("tag_name", "")
            name = rel.get("name", tag)
            body = rel.get("body", "")
            # Truncate long release notes
            if len(body) > 3000:
                body = body[:3000] + "..."

            items.append(self._make_item(
                title=f"{repo.split('/')[-1]} {name}",
                url=rel.get("html_url", ""),
                content=body,
                published_at=published,
                extra={"tag": tag, "repo": repo},
            ))

        print(f"[{self.name}] Collected {len(items)} releases")
        return items
