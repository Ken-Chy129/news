"""HTML generator: renders newspaper pages and archive index."""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader

# Category display config
CATEGORY_ICONS = {
    "trending": "\U0001f525",
    "paper": "\U0001f4c4",
    "blog": "\U0001f4dd",
    "industry": "\U0001f4f0",
    "open_source": "\U0001f527",
    "model_release": "\U0001f680",
    "tool_update": "\U0001f504",
}


def _compute_issue_number(date_str: str) -> int:
    """Compute issue number as days since 2026-01-01."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    epoch = datetime(2026, 1, 1)
    return max(1, (d - epoch).days + 1)


def _format_date_zh(date_str: str) -> str:
    """Format date in Chinese style: 2026年3月31日 · 星期一"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{d.year}年{d.month}月{d.day}日 · {weekdays[d.weekday()]}"


def _group_by_category(items: List[dict], categories: dict, default_max: int = 5) -> Dict[str, dict]:
    """Group items by category, preserving config order, capped per section."""
    sections = {}
    for cat_id, cat_cfg in categories.items():
        # Support both "category: name" and "category: {name, max_items}"
        if isinstance(cat_cfg, str):
            cat_name = cat_cfg
            max_items = default_max
        else:
            cat_name = cat_cfg.get("name", cat_id)
            max_items = cat_cfg.get("max_items", default_max)

        icon = CATEGORY_ICONS.get(cat_id, "")
        cat_items = [item for item in items if item.get("category") == cat_id][:max_items]
        if cat_items:
            sections[cat_id] = {
                "name": cat_name,
                "icon": icon,
                "entries": cat_items,
            }
    return sections


def generate(data: Dict[str, Any], config: dict, project_root: str) -> str:
    """Generate HTML for a single issue and update archive. Returns the issue HTML path."""
    site_config = config.get("site", {})
    categories = config.get("categories", {})
    title = site_config.get("title", "AI \u65e5\u62a5")
    base_url = site_config.get("base_url", "")
    max_per_section = site_config.get("max_per_section", 5)

    # Build category name lookup for templates
    category_names = {}
    for cat_id, cat_cfg in categories.items():
        if isinstance(cat_cfg, str):
            category_names[cat_id] = cat_cfg
        else:
            category_names[cat_id] = cat_cfg.get("name", cat_id)

    date_str = data["date"]
    templates_dir = os.path.join(project_root, "templates")
    site_dir = os.path.join(project_root, "site")
    issues_dir = os.path.join(site_dir, "issues")
    os.makedirs(issues_dir, exist_ok=True)

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    # Render issue page
    template = env.get_template("newspaper.html")
    html = template.render(
        title=title,
        date=date_str,
        date_zh=_format_date_zh(date_str),
        issue_number=_compute_issue_number(date_str),
        tldr=data.get("tldr", []),
        headlines=data.get("headlines", []),
        items=data.get("items", []),
        sections=_group_by_category(data.get("items", []), categories, max_per_section),
        category_names=category_names,
        archive_url="../archive.html",
        assets_prefix="../",
    )

    issue_path = os.path.join(issues_dir, f"{date_str}.html")
    with open(issue_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[generator] Wrote issue: {issue_path}")

    # Copy latest issue as index.html
    index_html = template.render(
        title=title,
        date=date_str,
        date_zh=_format_date_zh(date_str),
        issue_number=_compute_issue_number(date_str),
        tldr=data.get("tldr", []),
        headlines=data.get("headlines", []),
        items=data.get("items", []),
        sections=_group_by_category(data.get("items", []), categories, max_per_section),
        category_names=category_names,
        archive_url="archive.html",
        assets_prefix="",
    )
    index_path = os.path.join(site_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"[generator] Wrote index: {index_path}")

    # Generate archive page
    _generate_archive(site_dir, title, env)

    return issue_path


def _generate_archive(site_dir: str, title: str, env: Environment) -> None:
    """Scan issues/ and generate archive.html."""
    issues_dir = os.path.join(site_dir, "issues")
    issues = []

    for f in sorted(Path(issues_dir).glob("*.html"), reverse=True):
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})\.html", f.name)
        if not date_match:
            continue

        date_str = date_match.group(1)
        # Try to get item count from corresponding JSON
        data_path = Path(site_dir).parent / "data" / f"{date_str}.json"
        count = 0
        if data_path.exists():
            try:
                with open(data_path) as jf:
                    d = json.load(jf)
                    count = len(d.get("items", []))
            except Exception:
                pass

        issues.append({
            "date": date_str,
            "url": f"issues/{f.name}",
            "count": count,
        })

    template = env.get_template("archive.html")
    html = template.render(title=title, issues=issues)
    archive_path = os.path.join(site_dir, "archive.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[generator] Wrote archive: {archive_path} ({len(issues)} issues)")
