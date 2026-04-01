"""Feishu (Lark) webhook notifier."""

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

        message = self._build_message(data, site_url)

        payload = {
            "msg_type": "text",
            "content": {"text": message},
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
