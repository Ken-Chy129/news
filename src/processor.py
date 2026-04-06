"""LLM processor: deduplicate, classify, summarize, generate TL;DR."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Dict, Any

from openai import OpenAI

from .collectors.base import RawItem

SYSTEM_PROMPT = """你是一个专业的 AI 新闻编辑。你的任务是处理一批从不同来源采集的新闻条目，生成一份高质量、信息丰富的中文日报数据。

每条新闻都附带了从原文抓取的正文内容（content 字段），请基于正文生成摘要，不要凭标题臆测。

请完成以下工作：
1. 去重：合并标题或内容高度相似的条目，保留信息最丰富的版本
2. 分类：将每条新闻归入以下类别之一：paper(论文)、blog(博客)、industry(行业动态)、open_source(开源项目)、model_release(模型发布)、tool_update(工具更新，如 Claude Code、OpenClaw 等开发工具的版本更新)、trending(热榜)
3. 评分：为每条新闻评估重要性(1-10)，依据：影响力、新颖性、与AI领域的相关性
4. 摘要：为每条新闻生成中文摘要（150-300字），要求信息密度高、读完摘要就能掌握新闻核心内容。摘要必须包含：
   - 事件本身：具体发生了什么，涉及哪些组织/人物/产品
   - 关键细节：核心技术指标、数据、对比（如性能提升百分比、参数量、benchmark 得分等）
   - 意义/影响：为什么这件事重要，对行业或开发者意味着什么
   禁止使用"值得关注"、"引发热议"等空话套话。所有信息必须来自提供的正文内容，不要编造。

输出严格的 JSON 格式：
{
  "items": [
    {
      "title": "原始标题",
      "title_zh": "中文标题（如果原标题是英文则翻译，中文则保持原样）",
      "url": "原始URL",
      "source": "来源名称",
      "category": "分类",
      "summary_zh": "150-300字摘要",
      "importance": 8
    }
  ]
}

注意：
- 这是一份 AI/人工智能领域的专业日报
- 评分时，AI 相关内容的 importance 应显著高于非 AI 内容。热榜中与 AI 无关的条目 importance 不超过 4
- 追求质量而非数量，宁可条目少也要每条信息量充足
- items 按 importance 降序排列
- 去重后的条目不要重复出现
- 所有输出文本使用中文
- 如果 content 字段为空或信息不足，仍基于标题和来源生成摘要，但要标注"原文内容有限"
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
    max_per_batch = llm_config.get("max_items_per_batch", 10)

    # Convert to dicts for serialization, cap content length for LLM
    item_dicts = []
    for item in raw_items:
        d = item.to_dict()
        if len(d.get("content", "")) > 2000:
            d["content"] = d["content"][:2000] + "..."
        item_dicts.append(d)

    # Process in batches if needed
    batches = _chunk_items(item_dicts, max_per_batch)
    all_processed_items = []

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
                    "summary_zh": item.get("content", "")[:300],
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

    max_items = config.get("site", {}).get("max_items", 30)
    all_processed_items = all_processed_items[:max_items]

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
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
        "items": items[:max_items],
        "stats": {
            "raw_count": len(raw_items),
            "processed_count": len(items[:max_items]),
        },
    }
