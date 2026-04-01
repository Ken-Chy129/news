"""Feishu (Lark) webhook notifier - interactive card with embedded image."""

from __future__ import annotations

import os
from typing import Dict, Any, List, Optional

import httpx

from .base import BaseNotifier


class FeishuNotifier(BaseNotifier):

    def send(self, data: Dict[str, Any], site_url: str) -> bool:
        webhook_urls = self._get_webhook_urls()
        if not webhook_urls:
            print("[feishu] No webhook URLs configured, skipping")
            return False

        # Upload screenshot if enabled and available
        image_key = None
        if self.config.get("send_image", False):
            screenshot_path = data.get("screenshot_path", "")
            if screenshot_path and os.path.exists(screenshot_path):
                image_key = self._upload_image(screenshot_path)

        payload = self._build_card(data, site_url, image_key)
        success = True

        for i, url in enumerate(webhook_urls):
            try:
                with httpx.Client(timeout=10) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    result = resp.json()
                    if result.get("code") == 0 or result.get("StatusCode") == 0:
                        print(f"[feishu] Webhook {i + 1}/{len(webhook_urls)} sent")
                    else:
                        print(f"[feishu] Webhook {i + 1} error: {result}")
                        success = False
            except Exception as e:
                print(f"[feishu] Webhook {i + 1} failed: {e}")
                success = False

        return success

    def _get_webhook_urls(self) -> List[str]:
        env_key = self.config.get("webhook_url_env", "FEISHU_WEBHOOK_URL")
        raw = os.environ.get(env_key, "")
        if not raw:
            return []
        return [u.strip() for u in raw.split(";") if u.strip()]

    def _get_tenant_token(self) -> Optional[str]:
        app_id = os.environ.get("FEISHU_APP_ID", "")
        app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        if not app_id or not app_secret:
            return None

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret},
                )
                result = resp.json()
                if result.get("code") == 0:
                    return result.get("tenant_access_token")
                print(f"[feishu] Token error: {result}")
        except Exception as e:
            print(f"[feishu] Token request failed: {e}")
        return None

    def _upload_image(self, image_path: str) -> Optional[str]:
        token = self._get_tenant_token()
        if not token:
            print("[feishu] No tenant token, skipping image upload")
            return None

        try:
            with httpx.Client(timeout=30) as client:
                with open(image_path, "rb") as f:
                    resp = client.post(
                        "https://open.feishu.cn/open-apis/im/v1/images",
                        headers={"Authorization": f"Bearer {token}"},
                        data={"image_type": "message"},
                        files={"image": (os.path.basename(image_path), f, "image/png")},
                    )
                result = resp.json()
                if result.get("code") == 0:
                    image_key = result.get("data", {}).get("image_key", "")
                    print(f"[feishu] Image uploaded: {image_key}")
                    return image_key
                print(f"[feishu] Image upload error: {result}")
        except Exception as e:
            print(f"[feishu] Image upload failed: {e}")
        return None

    def _build_card(self, data: Dict[str, Any], site_url: str, image_key: Optional[str] = None) -> dict:
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

        elements = [
            {"tag": "markdown", "content": "\n".join(lines)},
        ]

        if image_key:
            elements.append({
                "tag": "img",
                "img_key": image_key,
                "alt": {"tag": "plain_text", "content": ""},
            })

        # Button
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "\u67e5\u770b\u5b8c\u6574\u62a5\u7eb8"},
                "type": "primary",
                "url": issue_url or site_url,
            }],
        })

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"AI \u65e5\u62a5 - {date}"},
                    "template": "red",
                },
                "elements": elements,
            },
        }
