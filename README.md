<div align="center">

# Friend Circle · 友链文章聚合器 ✨

[![CI - Friend Circle](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml/badge.svg)](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml)
![RSS](https://img.shields.io/badge/RSS-Feed-FFA500?logo=rss&logoColor=white)
![Go](https://img.shields.io/badge/Go-1.24%2B-00ADD8?logo=go&logoColor=white)
![Last commit](https://img.shields.io/github/last-commit/xwysyy/Friend-Circle?color=57A64A)
<br>
![Vercel](https://img.shields.io/badge/Vercel-333?logo=vercel)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xwysyy/Friend-Circle)

一个用 Go 写的友链文章聚合器。从 `config/*.json` 读取友链列表，并发抓取 RSS/Atom，输出 JSON 到 `results/`。`agentic-rss/` 存放 RSS adapter 模板，处理没有稳定 RSS 的站点。

</div>

---

## 🚀 功能

- 并发抓取：`max_workers` 控制并发数，HTTP 客户端复用连接并启用 HTTP/2。
- 请求重试：对 403、408、425、429、5xx 等状态码做指数回退重试。
- 时间统一：文章时间输出为 `YYYY-MM-DD HH:MM`，按时间倒序排列。
- RSS/Atom 解析：通过 [`gofeed`](https://github.com/mmcdole/gofeed) 转成统一结构。
- 多分类聚合：`json_url` 指向本地文件时，会合并同目录全部 `*.json`，文件名写入 `category`。
- 个人忽略列表：可选 `ignore_url` 或 `FRIEND_CIRCLE_IGNORE_URL`，生成 `all.personal.json`。
- 链接改写：可按友链名或域名匹配，执行前缀或正则替换。
- 自动更新：GitHub Actions 每 6 小时运行一次，也支持手动触发。

## 📦 快速开始

需要 Go 1.24+。

```bash
# 拉依赖
go mod download

# 一次性抓取（读取 config/conf.yaml）
go run .
```

完成后在 `results/` 下生成：`all.json`、`errors.json`、`all.personal.json`、`errors.personal.json`、`grab.log`。

## 🔧 配置（`config/conf.yaml`）

```yaml
spider_settings:
  enable: true                       # 是否启用爬虫
  json_url: "config/friend.json"     # 数据源（本地路径或 http(s)）
  article_count: 20                  # 每个博客最多抓取文章数
  max_workers: 5                     # 并发数，建议 ≤ 20

  # 可选：忽略列表（用于生成 all.personal.json）
  # 支持 http(s) 或本地 json；可被环境变量 FRIEND_CIRCLE_IGNORE_URL 覆盖
  ignore_url: "https://example.com/api/ignore/export"

  # 可选：链接改写（按 friend.json 中的 name 或域名匹配）
  link_rewrites:
    - match:
        name: "锦恢"
      rules:
        - type: "prefix"             # 或 "regex"
          from: "https://kirigaya.cn/api/rss/blog"
          to:   "https://kirigaya.cn/blog/article"
```

## 🤝 数据源（`friend.json`）

每条目固定四元组：`[name, blog_url, avatar, feed_url]`。`feed_url` 必须可访问 RSS/Atom，否则被记录到 `errors.json`。

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

## 🗂 分类与多 JSON

`json_url` 为本地路径时，程序会扫描其所在目录全部 `*.json`，按「文件名去扩展名」作为分类名自动合并；远程 URL 则按 URL basename 推断（兜底 `default`）。

```
config/
├── friend.json     # 分类：friend
├── ai.json         # 分类：ai
└── lang.json       # 分类：lang
```

## 📤 运行产物（`results/`）

- `all.json` / `errors.json`：全量抓取结果，及失败友链的原始 4 元组列表。
- `all.personal.json` / `errors.personal.json`：当 `ignore_url` 可达且非空时再跑一遍，跳过命中条目；否则与 `all.json` / `errors.json` 一致。
- `grab.log`：运行日志（`.gitignore` 中已忽略）。

输出 JSON 形如：

```json
{
  "statistical_data": {
    "friends_num": 42,
    "active_num": 40,
    "error_num": 2,
    "article_num": 760,
    "last_updated_time": "2026-05-02 18:50:00"
  },
  "article_data": [
    {
      "id": "...",
      "title": "...",
      "created": "2026-05-01 12:01",
      "link": "...",
      "author": "...",
      "avatar": "...",
      "category": "friend"
    }
  ]
}
```

## ☁️ Vercel 部署

仓库内 `vercel.json` 已映射常用静态路径：

- `/all.json`、`/errors.json` → `results/...`
- `/all.personal.json`、`/errors.personal.json` → `results/...`
- `/friend.json` → `config/friend.json`

把仓库部署为静态站点后，可以直接消费这些 JSON。

## 🧰 Agentic RSS

`agentic-rss/` 存放 RSS adapter 模板。目标站点缺少 RSS、RSS 结构异常或抓取不稳定时，可以用这些模板生成独立 RSS endpoint。

- `agentic-rss/prompts/adapter-author.md`：给 AI 的适配器编写说明。
- `agentic-rss/runtime-worker/`：Cloudflare Worker runtime。
- `agentic-rss/runtime-nodejs/`：自托管 Node.js runtime。

两个 runtime 使用同一份 `FeedAdapter` 接口：`build(ctx) -> RSS XML string`。用法见 `agentic-rss/README.md`。

## 🗓️ 自动化（GitHub Actions）

工作流 `.github/workflows/friend_circle.yml` 每 6 小时运行一次，也支持 `workflow_dispatch`。抓取结果以 `chore: update rss feeds` 提交回仓库。Fork 后需要在仓库 secrets 配置 `PAT_TOKEN`。

## 🧱 项目结构

```
.
├── main.go                # 入口：两段式抓取（all + personal）
├── scraper/               # 抓取核心
│   ├── types.go           # Article / Result / Config 等数据结构
│   ├── config.go          # YAML / JSON 加载、忽略列表、JSON 源发现
│   ├── fetcher.go         # HTTP/2 客户端、重试、并发处理
│   ├── feed.go            # RSS/Atom 解析、时间归一
│   └── rewriter.go        # 链接改写（prefix / regex）
├── config/
│   ├── conf.yaml          # 抓取配置
│   └── *.json             # 各分类友链列表
├── results/               # 运行产物（提交入库；仅日志被忽略）
├── agentic-rss/           # RSS adapter 编写提示与运行时模板
│   ├── prompts/
│   ├── runtime-worker/
│   └── runtime-nodejs/
├── vercel.json            # 静态路径 rewrites
└── .github/workflows/     # friend_circle.yml 定时抓取
```

## ❓ FAQ

- **没数据？** 检查 `json_url` 可达、`friend.json` 结构正确、`feed_url` 可访问。
- **某站抓取失败？** 查 `results/grab.log` 与 `errors.json`，必要时更新该站点 `feed_url`。
- **`all.personal.json` 与 `all.json` 一致？** 说明忽略列表不可用或为空，程序会复制全量抓取结果。
- **某站没有可用 RSS？** 先看 `agentic-rss/README.md`，用 runtime 模板生成一个 RSS endpoint，再把该 endpoint 写入对应 `config/*.json` 的第 4 项。

## 📝 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`type(scope)!: subject`，类型为 `build | chore | ci | docs | feat | fix | perf | refactor | revert | style | test`。CI 自动提交统一使用 `chore: update rss feeds`。

## 🪪 License

MIT，详见 `LICENSE`。

## 🙏 Acknowledgements

This project was originally inspired by [Qinyang Liu's project](https://github.com/willow-god/Friend-Circle-Lite) (MIT License), which provided the early scaffolding.

---
