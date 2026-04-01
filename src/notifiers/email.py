"""Email notifier using SMTP."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any

from .base import BaseNotifier


class EmailNotifier(BaseNotifier):

    def send(self, data: Dict[str, Any], site_url: str) -> bool:
        cfg = self.config
        username = os.environ.get(cfg.get("username_env", "EMAIL_USERNAME"), "")
        password = os.environ.get(cfg.get("password_env", "EMAIL_PASSWORD"), "")
        smtp_server = cfg.get("smtp_server", "")
        smtp_port = cfg.get("smtp_port", 465)
        from_addr = cfg.get("from_addr", "") or username
        to_addrs = cfg.get("to_addrs", [])

        if not all([username, password, smtp_server, to_addrs]):
            print("[email] Incomplete email configuration, skipping")
            return False

        date = data.get("date", "")
        message = self._build_message(data, site_url)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"AI \u65e5\u62a5 - {date}"
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)

        msg.attach(MIMEText(message, "plain", "utf-8"))

        # If we have the generated HTML, attach it
        html_content = self._build_html_email(data, site_url)
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                    server.login(username, password)
                    server.sendmail(from_addr, to_addrs, msg.as_string())
            else:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls(context=context)
                    server.login(username, password)
                    server.sendmail(from_addr, to_addrs, msg.as_string())

            print(f"[email] Notification sent to {len(to_addrs)} recipients")
            return True
        except Exception as e:
            print(f"[email] Send failed: {e}")
            return False

    def _build_html_email(self, data: Dict[str, Any], site_url: str) -> str:
        """Build a simple HTML email body."""
        date = data.get("date", "")
        tldr = data.get("tldr", [])
        items = data.get("items", [])

        tldr_html = ""
        if tldr:
            points = "".join(f"<li>{p}</li>" for p in tldr)
            tldr_html = f"<h3>今日要点</h3><ul>{points}</ul>"

        items_html = ""
        for item in items[:20]:
            title = item.get("title_zh") or item.get("title", "")
            url = item.get("url", "")
            source = item.get("source", "")
            summary = item.get("summary_zh", "")
            items_html += f'<li><a href="{url}">{title}</a> <small>[{source}]</small>'
            if summary:
                items_html += f"<br><small>{summary}</small>"
            items_html += "</li>"

        link = ""
        if site_url:
            issue_url = f"{site_url.rstrip('/')}/issues/{date}.html"
            link = f'<p><a href="{issue_url}">查看完整报纸</a></p>'

        return f"""<html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
<h2>AI 日报 - {date}</h2>
{tldr_html}
<h3>新闻列表</h3>
<ol>{items_html}</ol>
{link}
</body></html>"""
