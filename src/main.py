"""Main entry point: collect -> process -> generate -> notify."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List

import yaml

from .collectors.base import RawItem
from .collectors.rss import RSSCollector
from .collectors.hackernews import HackerNewsCollector
from .collectors.reddit import RedditCollector
from .collectors.github_trending import GitHubTrendingCollector
from .collectors.huggingface import HuggingFaceCollector
from .collectors.newsnow import NewsNowCollector
from .collectors.github_releases import GitHubReleasesCollector
from .collectors.web_scraper import WebScraperCollector
from .processor import process_items
from .generator import generate
from .notifiers.feishu import FeishuNotifier
from .notifiers.weixin import WeixinNotifier
from .notifiers.email import EmailNotifier

COLLECTOR_MAP = {
    "rss": RSSCollector,
    "hackernews": HackerNewsCollector,
    "reddit": RedditCollector,
    "github_trending": GitHubTrendingCollector,
    "huggingface": HuggingFaceCollector,
    "newsnow": NewsNowCollector,
    "github_releases": GitHubReleasesCollector,
    "web_scraper": WebScraperCollector,
}


def load_config(project_root: str) -> dict:
    config_path = os.path.join(project_root, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    print(f"Config loaded: {config_path}")
    return config


def collect_all(config: dict) -> List[RawItem]:
    """Run all configured collectors and merge results."""
    sources = config.get("sources", [])
    newsnow_config = config.get("newsnow", {})
    all_items: List[RawItem] = []

    for source in sources:
        source_type = source.get("type", "")
        collector_cls = COLLECTOR_MAP.get(source_type)
        if not collector_cls:
            print(f"[main] Unknown source type: {source_type}, skipping")
            continue

        # Inject global newsnow config
        if source_type == "newsnow" and "api_url" not in source:
            source["api_url"] = newsnow_config.get("api_url", "")

        try:
            collector = collector_cls(source)
            items = collector.collect()
            all_items.extend(items)
        except Exception as e:
            print(f"[main] Collector {source.get('name', source_type)} failed: {e}")
            continue

    print(f"\n[main] Total collected: {len(all_items)} items from {len(sources)} sources")
    return all_items


def notify_all(config: dict, data: dict) -> None:
    """Send notifications through enabled channels."""
    notification_config = config.get("notification", {})
    if not notification_config.get("enabled", False):
        print("[main] Notifications disabled")
        return

    site_url = config.get("site", {}).get("base_url", "")

    notifiers = []
    if notification_config.get("feishu", {}).get("enabled", False):
        notifiers.append(("feishu", FeishuNotifier(notification_config["feishu"])))
    if notification_config.get("weixin", {}).get("enabled", False):
        notifiers.append(("weixin", WeixinNotifier(notification_config["weixin"])))
    if notification_config.get("email", {}).get("enabled", False):
        notifiers.append(("email", EmailNotifier(notification_config["email"])))

    for name, notifier in notifiers:
        try:
            notifier.send(data, site_url)
        except Exception as e:
            print(f"[main] Notifier {name} failed: {e}")


def main():
    project_root = str(Path(__file__).resolve().parent.parent)
    config = load_config(project_root)

    # Step 1: Collect
    print("=" * 60)
    print("Step 1: Collecting data from all sources...")
    print("=" * 60)
    raw_items = collect_all(config)

    if not raw_items:
        print("[main] No items collected, exiting")
        sys.exit(0)

    # Separate trending items (skip LLM, pass through directly)
    ai_items = [item for item in raw_items if item.category != "trending"]
    trending_items = [item for item in raw_items if item.category == "trending"]
    print(f"[main] AI items: {len(ai_items)}, Trending items: {len(trending_items)}")

    # Step 2: Process AI items with LLM
    print("\n" + "=" * 60)
    print("Step 2: Processing with LLM...")
    print("=" * 60)
    processed_data = process_items(ai_items, config)

    # Add trending items back as-is
    for item in trending_items:
        processed_data["items"].append({
            "title": item.title,
            "title_zh": item.title,
            "url": item.url,
            "source": item.source,
            "category": "trending",
            "summary_zh": "",
            "importance": 3,
        })

    # Step 3: Generate HTML
    print("\n" + "=" * 60)
    print("Step 3: Generating HTML...")
    print("=" * 60)
    issue_path = generate(processed_data, config, project_root)

    # Save JSON (after generate, which adds display_count)
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, f"{processed_data['date']}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"[main] Saved data: {json_path}")

    # Step 3.5: Screenshot (only if any notifier needs it)
    need_screenshot = config.get("notification", {}).get("feishu", {}).get("send_image", False)
    if need_screenshot:
        from .screenshot import take_screenshot
        screenshot_path = os.path.join(project_root, "site", "screenshots", f"{processed_data['date']}.png")
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        if take_screenshot(issue_path, screenshot_path):
            processed_data["screenshot_path"] = screenshot_path

    # Step 4: Notify
    print("\n" + "=" * 60)
    print("Step 4: Sending notifications...")
    print("=" * 60)
    notify_all(config, processed_data)

    print("\n" + "=" * 60)
    print(f"Done! Generated {processed_data['stats']['processed_count']} items")
    print(f"  Data: {json_path}")
    print(f"  HTML: {issue_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
