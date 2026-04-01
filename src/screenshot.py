"""Generate a full-page screenshot of the newspaper HTML."""

from __future__ import annotations

import os


def take_screenshot(html_path: str, output_path: str) -> bool:
    """Take a full-page screenshot of the given HTML file. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[screenshot] playwright not installed, skipping")
        return False

    abs_path = os.path.abspath(html_path)
    file_url = f"file://{abs_path}"

    print(f"[screenshot] Capturing {html_path}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1000, "height": 800}, device_scale_factor=2)
            page.goto(file_url, wait_until="networkidle")
            page.screenshot(path=output_path, full_page=True)
            browser.close()

        print(f"[screenshot] Saved: {output_path}")
        return True
    except Exception as e:
        print(f"[screenshot] Failed: {e}")
        return False
