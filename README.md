<div align="center">

# Friend Circle · 友链文章聚合器 ✨

[![CI - Friend Circle](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml/badge.svg)](https://github.com/xwysyy/Friend-Circle/actions/workflows/friend_circle.yml)
![RSS](https://img.shields.io/badge/RSS-Feed-FFA500?logo=rss&logoColor=white)
![Go](https://img.shields.io/badge/Go-1.24%2B-00ADD8?logo=go&logoColor=white)
![Last commit](https://img.shields.io/github/last-commit/xwysyy/Friend-Circle?color=57A64A)
<br>
![Vercel](https://img.shields.io/badge/Vercel-333?logo=vercel)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/xwysyy/Friend-Circle)

一个简洁稳健的「友链文章聚合器」，用 Go 编写。从 `config/*.json` 读取友链列表，并发抓取 RSS/Atom，输出统一 JSON 到 `results/` 目录。

</div>

---

## 🚀 特性亮点

- ⚡ 并发抓取：`max_workers` 可调，HTTP/2 + 连接池复用。
- 🔁 请求重试：指数回退，覆盖 429 / 5xx 等可重试状态码。
- 🧭 时间统一：输出 `YYYY-MM-DD HH:MM`，缺失时合理兜底并按时间排序。
- 🧩 RSS/Atom 兼容：基于 [`gofeed`](https://github.com/mmcdole/gofeed) 解析为统一结构。
- 🗂 多分类聚合：同目录多个 JSON 自动合并，文件名作为 `category`。
- 🙈 个人忽略列表：可选 `ignore_url`，二次输出 `all.personal.json`。
- ✂️ 链接改写：按友链名 / 域名做前缀或正则替换，统一文章链接。
- 🛰️ 自动化：GitHub Actions 每 6 小时定时更新，可手动触发。

## 📦 快速开始

需要 Go 1.24+。

```bash
# 拉依赖
go mod download

# 一次性抓取（读取 config/conf.yaml）
go run .
```

完成后在 `results/` 下生成：`all.json`、`errors.json`、`all.personal.json`、`errors.personal.json`、`grab.log`。

## 🔧 配置详解（`config/conf.yaml`）

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

- `all.json` / `errors.json`：完整抓取结果，及失败友链的原始 4 元组列表。
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

直接以仓库为静态站点部署即可消费这些 JSON。

## 🗓️ 自动化（GitHub Actions）

工作流 `.github/workflows/friend_circle.yml` 每 6 小时运行一次（也支持 `workflow_dispatch`），抓取结果以 `chore: update rss feeds` 提交回仓库。Fork 后需在仓库 secrets 配置 `PAT_TOKEN`。

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
├── vercel.json            # 静态路径 rewrites
└── .github/workflows/     # 定时抓取
```

## ❓ FAQ

- **没数据？** 检查 `json_url` 可达、`friend.json` 结构正确、`feed_url` 可访问。
- **某站抓取失败？** 查 `results/grab.log` 与 `errors.json`，必要时更新该站点 `feed_url`。
- **`all.personal.json` 与 `all.json` 完全一致？** 说明 `ignore_url` 不可达或返回空列表，已退化为单段输出。

## 📝 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`type(scope)!: subject`，类型为 `build | chore | ci | docs | feat | fix | perf | refactor | revert | style | test`。CI 自动提交统一使用 `chore: update rss feeds`。

## 🪪 License

MIT，详见 `LICENSE`。

## 🙏 Acknowledgements

This project was originally inspired by [Qinyang Liu's project](https://github.com/willow-god/Friend-Circle-Lite) (MIT License), which provided the early scaffolding.

---

如果你觉得有用，欢迎点亮 ⭐ Star、提 Issue/PR！
