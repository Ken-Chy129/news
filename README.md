# AI 日报 (Daily AI News)

每日自动采集、AI 摘要、生成经典报纸风格的 AI 新闻静态站点。

## 功能

- **多源采集**: 微博/抖音/知乎热榜、ArXiv 论文、AI 公司博客、Hacker News、Reddit、GitHub Trending、HuggingFace 模型
- **LLM 处理**: 自动去重、分类、中文摘要、每日要点提炼 (OpenAI)
- **报纸风格**: 经典双栏排版，serif 字体，响应式适配桌面和移动端
- **历史归档**: 每期自动存档，可浏览完整历史
- **消息推送**: 支持飞书、企业微信、邮件通知
- **自动化**: GitHub Actions 每日定时生成 + GitHub Pages 部署

## 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行（无 OpenAI Key 也可运行，使用 fallback 模式）
python3 -m src

# 查看结果
open site/index.html
```

### 配置 OpenAI

```bash
export OPENAI_API_KEY="sk-..."
python3 -m src
```

### GitHub Actions 部署

1. Fork 本仓库
2. 在 Settings → Secrets → Actions 中添加 `OPENAI_API_KEY`
3. 在 Settings → Pages 中开启 GitHub Pages（Source: GitHub Actions）
4. 手动触发: Actions → Daily AI News → Run workflow

自动调度: 每天北京时间 08:00 自动运行。

## 项目结构

```
daily-ai-news/
├── config.yaml                 # 数据源、LLM、通知等全部配置
├── requirements.txt
├── src/
│   ├── main.py                 # 入口: collect → process → generate → notify
│   ├── collectors/             # 数据采集器
│   │   ├── base.py             # BaseCollector + RawItem 数据结构
│   │   ├── rss.py              # 通用 RSS/Atom (ArXiv, AI 博客等)
│   │   ├── hackernews.py       # Hacker News Firebase API
│   │   ├── reddit.py           # Reddit JSON API
│   │   ├── github_trending.py  # GitHub Trending 页面
│   │   ├── huggingface.py      # HuggingFace 热门模型
│   │   └── newsnow.py          # NewsNow API (微博/抖音/知乎热榜)
│   ├── processor.py            # OpenAI 去重/分类/摘要/TL;DR
│   ├── generator.py            # Jinja2 报纸 HTML 生成
│   └── notifiers/              # 消息推送
│       ├── base.py
│       ├── feishu.py           # 飞书 Webhook
│       ├── weixin.py           # 企业微信 Webhook
│       └── email.py            # SMTP 邮件
├── templates/
│   ├── newspaper.html          # 报纸模板
│   └── archive.html            # 归档目录模板
├── data/                       # 每日 JSON 中间数据 (Git 追踪)
├── site/                       # 生成的静态 HTML (部署到 GitHub Pages)
│   ├── index.html              # 最新一期
│   ├── archive.html            # 历史归档
│   └── issues/YYYY-MM-DD.html  # 每期报纸
└── .github/workflows/
    └── daily.yml               # 定时 + 手动触发
```

## 数据源

| 数据源 | 类型 | 说明 |
|--------|------|------|
| 微博热搜 | NewsNow API | 实时热搜榜 |
| 抖音热榜 | NewsNow API | 实时热榜 |
| 知乎热榜 | NewsNow API | 实时热榜 |
| ArXiv CS.AI / CS.CL | RSS | AI 和 NLP 最新论文 |
| OpenAI Blog | RSS | OpenAI 官方博客 |
| Google AI Blog | RSS | Google AI 博客 |
| Hacker News | API | AI 相关热帖（关键词过滤） |
| Reddit r/MachineLearning | API | 机器学习社区热帖 |
| GitHub Trending | 爬取 | 每日热门 AI 仓库 |
| HuggingFace | API | 热门模型排行 |

在 `config.yaml` 中可自由增减数据源。

## 配置

所有配置集中在 `config.yaml`，主要部分：

- **sources**: 数据源列表，每个源指定 type/url/category
- **llm**: OpenAI 模型、temperature 等参数
- **categories**: 新闻分类和显示名称
- **notification**: 飞书/企业微信/邮件推送配置
- **site**: 站点标题、最大条目数等

### 通知配置示例

```yaml
notification:
  enabled: true
  feishu:
    enabled: true
    webhook_url_env: FEISHU_WEBHOOK_URL  # 从环境变量读取
```

## 技术栈

- Python 3.9+
- feedparser / httpx / beautifulsoup4 (采集)
- OpenAI API (LLM 处理)
- Jinja2 (模板渲染)
- GitHub Actions + GitHub Pages (CI/CD + 部署)

## License

MIT
