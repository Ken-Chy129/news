"""WeChat Work (WeCom) webhook notifier."""

from __future__ import annotations

import os
from typing import Dict, Any

import httpx

from .base import BaseNotifier


class WeixinNotifier(BaseNotifier):

    def send(self, data: Dict[str, Any], site_url: str) -> bool:
        webhook_url = os.environ.get(
            self.config.get("webhook_url_env", "WEIXIN_WEBHOOK_URL"), ""
        )
        if not webhook_url:
            print("[weixin] No webhook URL configured, skipping")
            return False

        message = self._build_message(data, site_url)

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": message},
        }

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(webhook_url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                if result.get("errcode") == 0:
                    print("[weixin] Notification sent successfully")
                    return True
                else:
                    print(f"[weixin] API error: {result}")
                    return False
        except Exception as e:
            print(f"[weixin] Send failed: {e}")
            return False
