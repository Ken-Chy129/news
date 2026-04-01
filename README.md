# AI 日报

每日自动采集多平台 AI 资讯，通过 LLM 生成中文摘要，输出经典报纸风格的静态网站。

## 功能

- **16+ 数据源**: ArXiv 论文、AI 公司博客 (OpenAI/Anthropic/Google)、Hacker News、Reddit、GitHub Trending、HuggingFace、MIT Technology Review、微博/知乎热榜等
- **LLM 智能处理**: 自动去重、分类、中文摘要、每日要点提炼，AI 内容优先
- **报纸风格排版**: 头条区 + AI 专区 + 全网热榜三层架构，响应式适配桌面和移动端
- **工具动态追踪**: Claude Code、OpenClaw 等开发工具的版本更新
- **历史归档**: 每期自动存档，可浏览完整历史
- **消息推送**: 飞书、企业微信、邮件通知
- **零运维**: GitHub Actions 每日定时 + GitHub Pages 自动部署

## 快速开始

### 本地运行

```bash
pip install -r requirements.txt

# 无 OpenAI Key 也可运行（fallback 模式，不做摘要）
python3 -m src

open site/index.html
```

### 配置 OpenAI

```bash
export OPENAI_API_KEY="sk-..."
python3 -m src
```

### GitHub 部署

1. Fork 本仓库
2. Settings → Secrets → Actions → 添加 `OPENAI_API_KEY`
3. Settings → Pages → Source → 选择 **GitHub Actions**
4. Actions → Daily AI News → Run workflow（手动触发）

自动调度: 每天北京时间 08:00。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                       config.yaml                           │
│            数据源 / LLM / 分类 / 通知 / 站点配置               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌──────────────────── 1. collect ─────────────────────────────┐
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌───────────────┐   │
│  │  RSS    │ │NewsNow  │ │ HN/Reddit│ │GitHub Releases│   │
│  │ ArXiv   │ │ 微博     │ │  API     │ │ Claude Code   │   │
│  │ OpenAI  │ │ 知乎     │ │          │ │ OpenClaw      │   │
│  │ Google  │ │          │ │          │ │               │   │
│  │ HF Blog │ │          │ │          │ │               │   │
│  │ MIT TR  │ │          │ │          │ │               │   │
│  └────┬────┘ └────┬────┘ └────┬─────┘ └──────┬────────┘   │
│       └───────────┴──────────┴───────────────┘             │
│                        │                                    │
│               List[RawItem]                                 │
│     { source, title, url, content, published_at }           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌──────────────────── 2. process ─────────────────────────────┐
│                                                             │
│  OpenAI API (gpt-4o-mini)                                   │
│                                                             │
│  去重 → 分类(7类) → 评分 → 中文摘要(3-5句) → TL;DR          │
│                                                             │
│  AI 内容优先，热榜降权                                        │
│                                                             │
│  输出: data/YYYY-MM-DD.json                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌──────────────────── 3. generate ────────────────────────────┐
│                                                             │
│  Jinja2 模板渲染                                             │
│                                                             │
│  ┌──────────────────────────────┐                           │
│  │  头条区（重要 AI 新闻大标题）   │                           │
│  ├──────────────────────────────┤                           │
│  │  今日要点 (TL;DR)             │                           │
│  ├──────────────────────────────┤                           │
│  │  AI 专区（论文/模型/行业/     │                           │
│  │   开源/博客/工具更新，双栏）    │                           │
│  ├──────────────────────────────┤                           │
│  │  全网热榜（灰色背景，按平台）   │                           │
│  └──────────────────────────────┘                           │
│                                                             │
│  → site/index.html + site/issues/ + site/archive.html       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌──────────────────── 4. notify ──────────────────────────────┐
│                                                             │
│  飞书 Webhook  /  企业微信 Webhook  /  SMTP 邮件              │
│  推送 TL;DR + 报纸链接                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌──────────────────── 5. deploy ──────────────────────────────┐
│                                                             │
│  GitHub Actions                                             │
│    cron: 每天 UTC 0:00 (北京 8:00)                           │
│    workflow_dispatch: 手动触发                                │
│                                                             │
│  → git commit data/ site/ → GitHub Pages 自动部署             │
└─────────────────────────────────────────────────────────────┘
```

## 项目结构

```
news/
├── config.yaml                    # 全部配置（数据源/LLM/分类/通知）
├── requirements.txt
├── src/
│   ├── main.py                    # 入口: collect → process → generate → notify
│   ├── collectors/                # 数据采集器
│   │   ├── base.py                # BaseCollector + RawItem
│   │   ├── rss.py                 # 通用 RSS（ArXiv/OpenAI/Google/HF/MIT TR）
│   │   ├── hackernews.py          # Hacker News Firebase API
│   │   ├── reddit.py              # Reddit JSON API
│   │   ├── github_trending.py     # GitHub Trending 爬取
│   │   ├── github_releases.py     # GitHub Releases API（Claude Code/OpenClaw）
│   │   ├── huggingface.py         # HuggingFace 热门模型 API
│   │   ├── newsnow.py             # NewsNow API（微博/知乎热榜）
│   │   └── web_scraper.py         # 通用网页爬取（Anthropic Engineering 等）
│   ├── processor.py               # OpenAI 去重/分类/摘要/TL;DR
│   ├── generator.py               # Jinja2 报纸 HTML + 归档目录
│   └── notifiers/                 # 消息推送
│       ├── base.py                # BaseNotifier
│       ├── feishu.py              # 飞书 Webhook
│       ├── weixin.py              # 企业微信 Webhook
│       └── email.py               # SMTP 邮件
├── templates/
│   ├── newspaper.html             # 报纸模板（头条/AI专区/热榜三层）
│   └── archive.html               # 归档目录模板
├── data/                          # 每日 JSON 数据（Git 追踪，可溯源）
├── site/                          # 静态 HTML → GitHub Pages
│   ├── index.html                 # 最新一期
│   ├── archive.html               # 历史归档
│   ├── assets/style.css           # 报纸样式
│   └── issues/YYYY-MM-DD.html     # 每期报纸
└── .github/workflows/
    └── daily.yml                  # cron + 手动触发
```

## 数据源

| 数据源 | 类型 | 分类 |
|--------|------|------|
| ArXiv CS.AI / CS.CL | RSS | 论文 |
| OpenAI Blog | RSS | 博客 |
| Anthropic Engineering | 网页爬取 | 博客 |
| Google AI Blog | RSS | 博客 |
| Implicator AI | RSS | 博客 |
| MIT Technology Review | RSS | 博客 |
| HuggingFace Blog | RSS | 博客 |
| Hacker News | API | 行业动态 |
| Reddit r/MachineLearning | API | 行业动态 |
| GitHub Trending | 爬取 | 开源项目 |
| HuggingFace Models | API | 模型发布 |
| Claude Code | GitHub Releases | 工具更新 |
| OpenClaw | GitHub Releases | 工具更新 |
| 微博热搜 | NewsNow API | 热榜 |
| 知乎热榜 | NewsNow API | 热榜 |

所有数据源在 `config.yaml` 中配置，可自由增减。每个分类可独立控制最大展示条数。

## 配置

所有配置集中在 `config.yaml`：

- **sources**: 数据源列表（type/url/category/max_age_days）
- **categories**: 分类名称 + 每个分类的最大条目数
- **llm**: OpenAI 模型参数
- **notification**: 推送渠道开关和凭证
- **site**: 站点标题、全局最大条目数

### 添加数据源

```yaml
sources:
  # RSS 源
  - name: "My Feed"
    type: rss
    url: "https://example.com/feed"
    category: blog
    max_age_days: 1

  # 网页爬取
  - name: "My Site"
    type: web_scraper
    url: "https://example.com/news"
    base_url: "https://example.com"
    link_selector: "a.article-link"
    category: industry

  # GitHub 版本追踪
  - name: "My Tool"
    type: github_releases
    repo: "owner/repo"
    category: tool_update
    max_age_days: 3
```

## 技术栈

- Python 3.9+
- feedparser / httpx / beautifulsoup4（采集）
- OpenAI API gpt-4o-mini（LLM 处理）
- Jinja2（模板渲染）
- GitHub Actions + GitHub Pages（CI/CD + 部署）

## License

MIT
