"""LLM processor: deduplicate, classify, summarize, generate TL;DR."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Dict, Any

from openai import OpenAI

from .collectors.base import RawItem

SYSTEM_PROMPT = """你是一个专业的 AI 新闻编辑。你的任务是处理一批从不同来源采集的新闻条目，生成一份高质量、信息丰富的中文日报数据。

请完成以下工作：
1. 去重：合并标题或内容高度相似的条目，保留信息最丰富的版本
2. 分类：将每条新闻归入以下类别之一：paper(论文)、blog(博客)、industry(行业动态)、open_source(开源项目)、model_release(模型发布)、tool_update(工具更新，如 Claude Code、OpenClaw 等开发工具的版本更新)、trending(热榜)
3. 评分：为每条新闻评估重要性(1-10)，依据：影响力、新颖性、与AI领域的相关性
4. 摘要：为每条新闻生成 3-5 句中文摘要，要求信息丰富，包含关键数据、核心观点和背景信息，让读者不点开链接也能了解要点
5. TL;DR：从所有新闻中提炼 3-5 条最重要的要点，每条 2-3 句话，包含具体细节

输出严格的 JSON 格式：
{
  "tldr": ["要点1（2-3句，含具体信息）", "要点2", "要点3"],
  "items": [
    {
      "title": "原始标题",
      "title_zh": "中文标题（如果原标题是英文则翻译，中文则保持原样）",
      "url": "原始URL",
      "source": "来源名称",
      "category": "分类",
      "summary_zh": "3-5句中文摘要，信息丰富，包含关键数据和背景",
      "importance": 8
    }
  ]
}

注意：
- 这是一份 AI/人工智能领域的专业日报
- TL;DR 只包含与 AI/人工智能/大模型/机器学习直接相关的要点，不要包含娱乐、体育、社会新闻等非 AI 内容
- 评分时，AI 相关内容的 importance 应显著高于非 AI 内容。热榜中与 AI 无关的条目 importance 不超过 4
- 追求质量而非数量，宁可条目少也要每条信息量充足
- items 按 importance 降序排列
- 去重后的条目不要重复出现
- 所有输出文本使用中文
- 只输出 JSON，不要其他内容"""


def _chunk_items(items: List[dict], max_per_batch: int) -> List[List[dict]]:
    """Split items into batches."""
    return [items[i:i + max_per_batch] for i in range(0, len(items), max_per_batch)]


def process_items(raw_items: List[RawItem], config: dict) -> Dict[str, Any]:
    """Process raw items through LLM and return structured data."""
    llm_config = config.get("llm", {})
    api_key = os.environ.get(llm_config.get("api_key_env", "OPENAI_API_KEY"), "")

    if not api_key:
        print("[processor] No API key found, returning items without LLM processing")
        return _fallback_process(raw_items, config)

    client = OpenAI(api_key=api_key)
    model = llm_config.get("model", "gpt-4o-mini")
    temperature = llm_config.get("temperature", 0.3)
    max_per_batch = llm_config.get("max_items_per_batch", 20)

    # Convert to dicts for serialization
    item_dicts = [item.to_dict() for item in raw_items]

    # Process in batches if needed
    batches = _chunk_items(item_dicts, max_per_batch)
    all_processed_items = []
    all_tldrs = []

    for i, batch in enumerate(batches):
        print(f"[processor] Processing batch {i + 1}/{len(batches)} ({len(batch)} items)...")
        user_content = json.dumps(batch, ensure_ascii=False)

        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )

            result = json.loads(response.choices[0].message.content)
            all_processed_items.extend(result.get("items", []))
            all_tldrs.extend(result.get("tldr", []))
        except Exception as e:
            print(f"[processor] LLM error on batch {i + 1}: {e}")
            # Fallback: include raw items without processing
            for item in batch:
                all_processed_items.append({
                    "title": item["title"],
                    "title_zh": item["title"],
                    "url": item["url"],
                    "source": item["source"],
                    "category": item["category"],
                    "summary_zh": item.get("content", "")[:200],
                    "importance": 5,
                })

    # If multiple batches, deduplicate and re-rank
    if len(batches) > 1:
        seen_urls = set()
        deduped = []
        for item in sorted(all_processed_items, key=lambda x: x.get("importance", 0), reverse=True):
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                deduped.append(item)
        all_processed_items = deduped
        # Keep only top 5 TL;DRs
        all_tldrs = all_tldrs[:5]

    max_items = config.get("site", {}).get("max_items", 30)
    all_processed_items = all_processed_items[:max_items]

    # Pick headlines: top 2 non-trending AI-related items
    headlines = []
    for item in all_processed_items:
        if item.get("category") != "trending" and item.get("importance", 0) >= 8:
            headlines.append(item)
            if len(headlines) >= 2:
                break

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "tldr": all_tldrs,
        "headlines": headlines,
        "items": all_processed_items,
        "stats": {
            "raw_count": len(raw_items),
            "processed_count": len(all_processed_items),
        },
    }


def _fallback_process(raw_items: List[RawItem], config: dict) -> Dict[str, Any]:
    """Fallback when no LLM is available."""
    items = []
    seen_urls = set()
    for item in raw_items:
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        items.append({
            "title": item.title,
            "title_zh": item.title,
            "url": item.url,
            "source": item.source,
            "category": item.category,
            "summary_zh": item.content[:200] if item.content else "",
            "importance": 5,
        })

    max_items = config.get("site", {}).get("max_items", 30)
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "tldr": [],
        "items": items[:max_items],
        "stats": {
            "raw_count": len(raw_items),
            "processed_count": len(items[:max_items]),
        },
    }
