"""GitHub Trending collector by scraping the trending page."""

from __future__ import annotations

from typing import List

import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, RawItem

TRENDING_URL = "https://github.com/trending"


class GitHubTrendingCollector(BaseCollector):

    def collect(self) -> List[RawItem]:
        topics = self.config.get("topics", [])
        # Use spoken_language_code for Chinese if needed
        params = {"since": "daily"}
        if topics:
            # GitHub trending doesn't support topic filtering via URL params,
            # we'll filter by description keywords instead
            pass

        print(f"[{self.name}] Fetching GitHub Trending...")
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(TRENDING_URL, params=params)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as e:
            print(f"[{self.name}] HTTP error: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.Box-row")

        ai_keywords = {"machine-learning", "deep-learning", "llm", "nlp", "ai",
                        "neural", "transformer", "gpt", "diffusion", "ml", "agent",
                        "langchain", "rag", "embedding", "fine-tune", "lora"}

        items: List[RawItem] = []
        for article in articles:
            h2 = article.select_one("h2 a")
            if not h2:
                continue

            repo_path = h2.get("href", "").strip().lstrip("/")
            if not repo_path:
                continue

            repo_url = f"https://github.com/{repo_path}"
            repo_name = repo_path

            desc_el = article.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # Filter for AI-related repos if topics are configured
            if topics:
                text = f"{repo_name} {desc}".lower()
                if not any(kw in text for kw in ai_keywords):
                    continue

            # Get stars today
            stars_el = article.select_one("span.d-inline-block.float-sm-right")
            stars_today = stars_el.get_text(strip=True) if stars_el else ""

            # Get language
            lang_el = article.select_one("span[itemprop='programmingLanguage']")
            lang = lang_el.get_text(strip=True) if lang_el else ""

            items.append(self._make_item(
                title=repo_name,
                url=repo_url,
                content=desc,
                extra={"stars_today": stars_today, "language": lang},
            ))

        print(f"[{self.name}] Collected {len(items)} items")
        return items
