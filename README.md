<div align="center">

# Friend Circle · 友链文章聚合器 ✨

[![CI - Friend Circle](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml/badge.svg)](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml)
![RSS](https://img.shields.io/badge/RSS-Feed-FFA500?logo=rss&logoColor=white)
![uv](https://img.shields.io/badge/Package%20Manager-uv-5C6EE3)
![Last commit](https://img.shields.io/github/last-commit/xwysyy/Friend-Circle?color=57A64A)
<br>
![Vercel](https://img.shields.io/badge/Vercel-333?logo=vercel)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xwysyy/Friend-Circle)

一个简洁稳健的「友链文章聚合器」，从 `config/conf.yaml` 读取数据源，抓取各博客的 RSS/Atom，输出统一 JSON：`results/all.json`。

</div>

---

## 🚀 特性亮点

- ⚡ 并发抓取：可配置 `max_workers`，快且稳。
- 🔁 请求重试：`requests.Session` + 指数回退，提升成功率。
- 🧭 时间统一：输出时间格式 `YYYY-MM-DD HH:MM`，缺失时合理兜底。
- 🧩 RSS/Atom 兼容：多源解析，结构化为统一 JSON。
- 🧪 可本地/远程数据源：`json_url` 支持文件或 HTTP(S)。
- 🛰️ 自动化：GitHub Actions 每 6 小时定时更新，可手动触发。

## 📦 快速开始

1) 安装依赖（使用 `uv`）

- 安装 uv（推荐）：https://docs.astral.sh/uv/
- 安装项目依赖：

```
uv pip install -r requirements.txt
```

2) 配置抓取参数（`config/conf.yaml`）

- `spider_settings.enable`：是否启用抓取（`true/false`）
- `spider_settings.json_url`：你的 `friend.json`（本地路径或 HTTP/HTTPS，默认 `config/friend.json`）
- `spider_settings.article_count`：每个博客抓取的最大文章数
- `spider_settings.max_workers`：抓取并发（建议 5–20，视机器与友链规模）

3) 一次性抓取生成 JSON

```
uv run python run.py
```

完成后在 `results/` 下生成：`all.json`、`errors.json`、`grab.log`。

## 🔧 配置详解（conf.yaml）

```yaml
spider_settings:
  enable: true              # 是否启用爬虫
  json_url: "config/friend.json" # 数据源（本地/远程 JSON）
  article_count: 10         # 每个博客最多抓取文章数
  max_workers: 5            # 并发数，建议 ≤ 20
```

## 🤝 数据源（friend.json）

- 条目顺序固定：`[name, blog_url, avatar, feed_url]`
- `feed_url` 必须可访问 RSS/Atom，否则会被记录到 `errors.json`

示例：

```json
{
  "friends": [
    [
      "xwysyy",
      "https://www.xwysyy.cn/",
      "https://www.xwysyy.cn/avatar.webp",
      "https://www.xwysyy.cn/rss.xml"
    ]
  ]
}
```

## 📤 运行产物与日志（`results/`）

- `all.json`：聚合后的文章数据
- `errors.json`：抓取失败的友链条目（原始 4 元组）
- `grab.log`：运行日志（抓取进度、错误摘要等）

## 🗓️ 自动化（GitHub Actions）

- 工作流：`.github/workflows/friend_circle.yml`
- 计划任务：每 6 小时执行一次（可手动 `workflow_dispatch`）
- 你也可以 Fork 后在自己仓库开启同名 Workflow 并配置 `PAT_TOKEN`

## 🧱 项目结构

```
.
├── app/
│   └── core.py           # 配置加载、RSS/Atom 抓取、解析与聚合（核心逻辑）
├── config/
│   ├── conf.yaml         # 抓取配置（开关、并发、文章数、数据源）
│   └── friend.json       # 友链列表（数据源）
├── results/              # 运行时生成：all.json, errors.json, grab.log
├── run.py                # 一次性抓取入口
├── requirements.txt      # 依赖列表
└── .github/workflows/    # CI 定时抓取
```

## ❓常见问题（FAQ）

- 抓取不到/没数据？
  - 检查 `json_url` 可达性及 `friend.json` 结构是否符合规范；确保每条目包含有效 `feed_url`。
- 某个 RSS 失败？
  - 查看 `results/grab.log` 中对应错误与 HTTP 状态码；必要时更新该站点的 `feed_url`。
- 时间字段缺失？
  - 会记录警告并采用默认值，以保证排序稳定；建议源头补齐时间信息。

## 🧪 开发

- 依赖安装：`uv pip install -r requirements.txt`
- 本地运行：`uv run python run.py`

## 🪪 许可协议

本项目使用 MIT License，详见 `LICENSE`。

---

如果你觉得有用，欢迎点亮 ⭐ Star、提 Issue/PR！
