"""Feishu (Lark) webhook notifier - interactive card with link."""

from __future__ import annotations

import os
from typing import Dict, Any

import httpx

from .base import BaseNotifier


class FeishuNotifier(BaseNotifier):

    def send(self, data: Dict[str, Any], site_url: str) -> bool:
        webhook_url = os.environ.get(
            self.config.get("webhook_url_env", "FEISHU_WEBHOOK_URL"), ""
        )
        if not webhook_url:
            print("[feishu] No webhook URL configured, skipping")
            return False

        date = data.get("date", "")
        tldr = data.get("tldr", [])
        count = data.get("display_count", len(data.get("items", [])))
        issue_url = f"{site_url.rstrip('/')}/issues/{date}.html" if site_url else ""

        # Build markdown content
        lines = []
        if tldr:
            for point in tldr[:3]:
                # Truncate long points
                if len(point) > 60:
                    point = point[:60] + "..."
                lines.append(f"- {point}")

        lines.append(f"\n**共 {count} 条新闻**")

        md_content = "\n".join(lines)

        # Feishu interactive card
        payload = {
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
                        "content": md_content,
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

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(webhook_url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    print("[feishu] Notification sent successfully")
                    return True
                else:
                    print(f"[feishu] API error: {result}")
                    return False
        except Exception as e:
            print(f"[feishu] Send failed: {e}")
            return False
