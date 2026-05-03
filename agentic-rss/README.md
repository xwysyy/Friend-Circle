# Agentic RSS

让 AI 给"没 RSS 或 RSS 被反爬"的站点写一份适配器代码，部署后输出标准 RSS，供下游消费方拉取。

不是自动化系统，是「人 + AI 」的一次性手工流程。

## 两类问题

一类是博客根本没 RSS：协议适配缺失，要靠 AI 看 HTML 或 JSON 推断结构、生成抽取代码。

另一类是博客有 RSS 但被反爬：网络出口问题，换 IP 段就行——CF Worker、自托管机器、商业代理任选。这一类不用 AI 判断结构，只用挑对部署位置。

## 4 种 adapter 模式

AI 探查站点后选一个：

| 模式 | 触发条件 |
|---|---|
| A. RSS Proxy | 源站有合法 RSS，出口友好 |
| B. RSS Parse + rebuild | RSS 结构破损 / 时间格式非标准 / 编码乱 |
| C. HTML Scrape | 没 RSS，但列表页 DOM 规则 |
| D. JSON API | 没 RSS，XHR 暴露文章数组 |

完整决策树见 `prompts/adapter-author.md`。

## 2 种 runtime

按出口 IP 决定。

| Runtime | 部署位置 | 出口 IP | 适用 |
|---|---|---|---|
| `runtime-worker/` | Cloudflare 边缘 | Cloudflare ASN | 默认，无运维 |
| `runtime-nodejs/` | 自托管机器（VPS / NAS / 树莓派） | 你机器的 IP | CF 段被反爬、需要重型解析库、需要长状态 |

两个 runtime 共用同一份 `Adapter` 接口（`fetch() → Article[]`）。同一份 adapter 逻辑可以两边迁移，差异只在 import 路径细节——worker 不带 `.js`，NodeNext 必须带 `.js`，AI 在生成时会自己处理。

## 用法

把 `prompts/adapter-author.md` 和目标 URL 一起喂给 AI，AI 会探查站点、选模式、选 runtime，输出 adapter 代码和部署命令。把模板拷到仓外目录、粘贴 adapter 代码：

```
# worker
npx wrangler deploy   → https://<slug>.<account>.workers.dev

# nodejs
docker compose up -d  → http://your-host:8080/feed
```

最后改下游消费方的源列表里那一行 URL。

每次部署的 adapter 代码是一次性产物，留在你自己的 Cloudflare 账户或 Docker host 上，不入仓。仓内只保留 runtime 模板和给 AI 看的操作手册。

## 目录

```
agentic-rss/
├── README.md
├── prompts/
│   └── adapter-author.md        # 给 AI 的探查→选模式→选 runtime→出代码全流程
├── runtime-worker/              # CF Worker template（4 模式都能跑）
│   ├── src/{index,adapter,types}.ts + lib/{fetch,rss,passthrough}.ts
│   ├── wrangler.toml.example
│   └── package.json + tsconfig.json
└── runtime-nodejs/              # Self-hosted Docker template
    ├── src/{server,adapter,types}.ts + lib/{fetch,rss}.ts
    ├── Dockerfile + docker-compose.yml
    └── package.json + tsconfig.json
```

## 跟 RSSHub 的差别

| | RSSHub | Agentic RSS |
|---|---|---|
| 适配器来源 | 社区 PR | AI 现场推断 |
| 部署粒度 | 单个大 service | 每站点一个独立实例 |
| 反爬处理 | 看部署服务那台机器 | 选对 runtime 即可 |
| 失效后 | 等 PR | 重跑一次 prompt |
| 用途 | 通用聚合 | 个人订阅补漏 |

不是替代 RSSHub。RSSHub 没收录或不便部署时，这套是更轻的自助方式。

## 都不行的时候

A/B/C/D 任一模式 + 任一 runtime 都失败的情形是有的——某些站点对所有非住宅 IP、所有结构化路径都打 challenge。这时工程方案已经穷尽，应该考虑联系作者要 allowlist、放弃这个源、或者商业住宅代理。`prompts/adapter-author.md § Step 6` 明确要求 AI 不要在这种时候硬塞代码。
