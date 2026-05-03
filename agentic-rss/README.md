# Agentic RSS

让 AI 给"没 RSS 或 RSS 被反爬"的站点**现场生成一份适配器代码**，部署后产出可订阅的 RSS endpoint，供任何 RSS 消费方拉取。

不在自动化里——这是**手动一次性**的「人 + AI」配合工作流。

## 解决的两类问题

| 场景 | 本质 | 核心动作 |
|---|---|---|
| **博客没 RSS** | 协议适配缺失 | AI 看 HTML / JSON 推断结构 → 生成抽取代码 |
| **博客有 RSS 但反爬** | 网络出口问题 | 换出口 IP（CF Worker / 自托管机器 / 商业代理） |

第二类不需要 AI 判断结构，只需要选**对的部署位置**。

## 4 种 adapter 模式（AI 在探查后挑一个）

| 模式 | 触发条件 |
|---|---|
| **A. RSS Proxy** | 源站有合法 RSS，出口友好 |
| **B. RSS Parse + rebuild** | 源站 RSS 结构破损 / 时间格式非标准 / 编码乱 |
| **C. HTML Scrape** | 没 RSS，但列表页 DOM 规则 |
| **D. JSON API** | 没 RSS，XHR 暴露文章数组 |

详细决策树见 `prompts/adapter-author.md`。

## 2 种 runtime（按出口 IP 决定）

| Runtime | 部署位置 | 出口 IP | 适用 |
|---|---|---|---|
| **`runtime-worker/`** | Cloudflare 边缘 | Cloudflare ASN | 默认，零运维 |
| **`runtime-nodejs/`** | 自托管机器（VPS / NAS / 树莓派） | 你机器的 IP | CF 段被反爬 / 需要重型解析库 / 需要长状态 |

两个 runtime 共享 `Adapter` 接口（`fetch() → Article[]`）—— 同一份 adapter 代码逻辑可以在两个 runtime 间迁移，只有 import 路径细节不同（worker 不带 `.js`、NodeNext 必须带 `.js`），AI 在生成时会自适应。

## 标准工作流

```
1. 用户：发现某站点没 RSS 或 RSS 持续抓不到
2. 用户：把 prompts/adapter-author.md + 目标 URL 喂给 AI
3. AI：探查 → 选模式（A/B/C/D）→ 选 runtime（worker/nodejs）→ 输出代码 + 部署清单
4. 用户：拷模板到仓外目录，粘贴 adapter.ts
        - worker: npx wrangler deploy   → https://<slug>.<account>.workers.dev
        - nodejs: docker compose up -d  → http://your-host:8080/feed
5. 用户：把消费方的源列表里对应行的 URL 改成新 endpoint
```

**实例不入仓**：每次部署的具体 adapter 代码是一次性产物，留在用户自己的本机目录 / Cloudflare 账户 / Docker host 上。仓内只保留 runtime 模板和 AI 操作手册。

## 目录

```
agentic-rss/
├── README.md                    # 本文件
├── prompts/
│   └── adapter-author.md        # 给 AI 的探查 → 选模式 → 选 runtime → 出代码全流程
├── runtime-worker/              # CF Worker template（4 模式都能跑）
│   ├── src/{index,adapter,types}.ts + lib/{fetch,rss,passthrough}.ts
│   ├── wrangler.toml.example
│   └── package.json + tsconfig.json
└── runtime-nodejs/              # Self-hosted Docker template
    ├── src/{server,adapter,types}.ts + lib/{fetch,rss}.ts
    ├── Dockerfile + docker-compose.yml
    └── package.json + tsconfig.json
```

## 与 RSSHub 的差别

| | RSSHub | Agentic RSS |
|---|---|---|
| 适配器来源 | 社区 PR | AI 现场推断 |
| 部署粒度 | 单个大 service | 每站点一个独立实例 |
| 反爬策略 | 通过部署服务的人解决 | runtime 选择即解决 |
| 失效自愈 | 等 PR | 重跑一次 prompt |
| 用途 | 通用聚合 | 个人站点订阅补充 |

不是替代 RSSHub —— 它是 RSSHub 没收录或不便部署时的**轻量自助方式**。

## 失败兜底

任何模式 + 任何 runtime 都失败时：

→ 工程方案已穷尽。考虑联系作者请求 allowlist、接受现状、或商业住宅代理。`prompts/adapter-author.md § Step 6` 明确规定 AI 在这种情况下**不要硬编代码**。
