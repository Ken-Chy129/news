"""HTML generator: renders newspaper pages and archive index."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader

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
    """Compute issue number as days since 2026-04-01 (first issue)."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    epoch = datetime(2026, 4, 1)
    return max(1, (d - epoch).days + 1)


def _format_date_zh(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{d.year}年{d.month}月{d.day}日 · {weekdays[d.weekday()]}"


def _group_by_category(items: List[dict], categories: dict, default_max: int = 5) -> Dict[str, dict]:
    """Group items by category, preserving config order, capped per section."""
    sections = {}
    for cat_id, cat_cfg in categories.items():
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
    max_per_section = site_config.get("max_per_section", 5)

    date_str = data["date"]
    templates_dir = os.path.join(project_root, "templates")
    site_dir = os.path.join(project_root, "site")
    issues_dir = os.path.join(site_dir, "issues")
    os.makedirs(issues_dir, exist_ok=True)

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    template = env.get_template("newspaper.html")
    sections = _group_by_category(data.get("items", []), categories, max_per_section)
    display_count = sum(len(s["entries"]) for s in sections.values())
    data["display_count"] = display_count

    render_kwargs = dict(
        title=title,
        date=date_str,
        date_zh=_format_date_zh(date_str),
        issue_number=_compute_issue_number(date_str),
        items=data.get("items", []),
        sections=sections,
        display_count=display_count,
    )

    # Issue page
    html = template.render(**render_kwargs, archive_url="../archive.html", assets_prefix="../")
    issue_path = os.path.join(issues_dir, f"{date_str}.html")
    with open(issue_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[generator] Wrote issue: {issue_path}")

    # Index page
    index_html = template.render(**render_kwargs, archive_url="archive.html", assets_prefix="")
    index_path = os.path.join(site_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"[generator] Wrote index: {index_path}")

    # Archive page
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
        data_path = Path(site_dir).parent / "data" / f"{date_str}.json"
        count = 0
        if data_path.exists():
            try:
                with open(data_path) as jf:
                    d = json.load(jf)
                    count = d.get("display_count", len(d.get("items", [])))
            except Exception:
                pass

        issues.append({
            "date": date_str,
            "url": f"issues/{f.name}",
            "count": count,
        })

    # Group by month
    from collections import OrderedDict
    months_dict = OrderedDict()
    for issue in issues:
        month_key = issue["date"][:7]  # "2026-04"
        if month_key not in months_dict:
            year, mon = month_key.split("-")
            months_dict[month_key] = {
                "label": f"{year}\u5e74{int(mon)}\u6708",
                "issues": [],
            }
        months_dict[month_key]["issues"].append(issue)

    months = list(months_dict.values())

    template = env.get_template("archive.html")
    html = template.render(title=title, total=len(issues), months=months)
    archive_path = os.path.join(site_dir, "archive.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[generator] Wrote archive: {archive_path} ({len(issues)} issues)")
