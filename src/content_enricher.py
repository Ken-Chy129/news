"""Content enricher: fetch full article text for items with insufficient content."""

from __future__ import annotations

import concurrent.futures
from typing import List

import httpx
import trafilatura

from .collectors.base import RawItem

# Skip enrichment for these domains (API-based sources with structured data)
SKIP_DOMAINS = {
    "huggingface.co/api",
    "news.ycombinator.com",
}

# Minimum content length to consider "sufficient"
MIN_CONTENT_LENGTH = 200

# Max chars to keep from extracted article
MAX_CONTENT_LENGTH = 3000

# Concurrent fetch workers
MAX_WORKERS = 8

FETCH_TIMEOUT = 20


def _needs_enrichment(item: RawItem) -> bool:
    """Check if this item needs content fetching."""
    if len(item.content) >= MIN_CONTENT_LENGTH:
        return False
    if not item.url:
        return False
    for domain in SKIP_DOMAINS:
        if domain in item.url:
            return False
    return True


def _fetch_content(item: RawItem) -> RawItem:
    """Fetch and extract article content for a single item."""
    if not _needs_enrichment(item):
        return item

    try:
        downloaded = trafilatura.fetch_url(item.url)
        if not downloaded:
            return item

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )

        if text and len(text) > len(item.content):
            item.content = text[:MAX_CONTENT_LENGTH]

    except Exception as e:
        print(f"[enricher] Failed to fetch {item.url}: {e}")

    return item


def enrich_items(items: List[RawItem]) -> List[RawItem]:
    """Enrich items with full article content, fetched concurrently."""
    to_enrich = [i for i, item in enumerate(items) if _needs_enrichment(item)]

    if not to_enrich:
        print("[enricher] All items already have sufficient content")
        return items

    print(f"[enricher] Fetching full content for {len(to_enrich)}/{len(items)} items...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_content, items[i]): i
            for i in to_enrich
        }

        done_count = 0
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                items[idx] = future.result()
                done_count += 1
            except Exception as e:
                print(f"[enricher] Error processing item {idx}: {e}")

    enriched = sum(1 for i in to_enrich if len(items[i].content) >= MIN_CONTENT_LENGTH)
    print(f"[enricher] Done. {enriched}/{len(to_enrich)} items enriched with full content")
    return items
