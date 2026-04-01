"""Feishu (Lark) webhook notifier - interactive card with link."""

from __future__ import annotations

import os
from typing import Dict, Any, List

import httpx

from .base import BaseNotifier


class FeishuNotifier(BaseNotifier):

    def send(self, data: Dict[str, Any], site_url: str) -> bool:
        webhook_urls = self._get_webhook_urls()
        if not webhook_urls:
            print("[feishu] No webhook URLs configured, skipping")
            return False

        payload = self._build_card(data, site_url)
        success = True

        for i, url in enumerate(webhook_urls):
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    result = resp.json()
                    if result.get("code") == 0 or result.get("StatusCode") == 0:
                        print(f"[feishu] Webhook {i + 1}/{len(webhook_urls)} sent successfully")
                    else:
                        print(f"[feishu] Webhook {i + 1} API error: {result}")
                        success = False
            except Exception as e:
                print(f"[feishu] Webhook {i + 1} send failed: {e}")
                success = False

        return success

    def _get_webhook_urls(self) -> List[str]:
        """Get webhook URLs from config, supporting both old and new format."""
        urls = []

        # New format: webhook_urls array
        for item in self.config.get("webhook_urls", []):
            env_key = item.get("env", "")
            if env_key:
                url = os.environ.get(env_key, "")
                if url:
                    urls.append(url)

        # Fallback: old single webhook_url_env format
        if not urls:
            env_key = self.config.get("webhook_url_env", "")
            if env_key:
                url = os.environ.get(env_key, "")
                if url:
                    urls.append(url)

        return urls

    def _build_card(self, data: Dict[str, Any], site_url: str) -> dict:
        date = data.get("date", "")
        tldr = data.get("tldr", [])
        count = data.get("display_count", len(data.get("items", [])))
        issue_url = f"{site_url.rstrip('/')}/issues/{date}.html" if site_url else ""

        lines = []
        if tldr:
            for point in tldr[:3]:
                if len(point) > 60:
                    point = point[:60] + "..."
                lines.append(f"- {point}")

        lines.append(f"\n**\u5171 {count} \u6761\u65b0\u95fb**")

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"AI \u65e5\u62a5 - {date}",
                    },
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": "\n".join(lines),
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "\u67e5\u770b\u5b8c\u6574\u62a5\u7eb8",
                                },
                                "type": "primary",
                                "url": issue_url or site_url,
                            },
                        ],
                    },
                ],
            },
        }
