"""Base notifier."""

from __future__ import annotations

import abc
from typing import Dict, Any


class BaseNotifier(abc.ABC):
    """Abstract base class for notification channels."""

    def __init__(self, config: dict):
        self.config = config

    @abc.abstractmethod
    def send(self, data: Dict[str, Any], site_url: str) -> bool:
        """Send notification. Returns True on success."""
        ...

    def _build_message(self, data: Dict[str, Any], site_url: str) -> str:
        """Build a plain text message from processed data."""
        date = data.get("date", "")
        tldr = data.get("tldr", [])
        items = data.get("items", [])

        lines = [f"AI \u65e5\u62a5 - {date}", ""]

        if tldr:
            lines.append("\u2022 " + "\n\u2022 ".join(tldr))
            lines.append("")

        lines.append(f"\u5171 {len(items)} \u6761\u65b0\u95fb")

        if site_url:
            issue_url = f"{site_url.rstrip('/')}/issues/{date}.html"
            lines.append(f"\u67e5\u770b\u5b8c\u6574\u62a5\u7eb8: {issue_url}")

        return "\n".join(lines)
