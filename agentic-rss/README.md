# Agentic RSS

让 AI 给没有稳定 RSS 的站点写适配器代码。部署后输出标准 RSS，供下游消费方拉取。

这里放的是适配器模板和编写说明。

## 适用范围

- 站点没有 RSS，需要从 HTML 或 JSON 接口生成 RSS。
- 站点有 RSS，但结构不标准、时间格式异常或抓取不稳定。

## Adapter 模式

AI 探查站点后选一个：

| 模式 | 触发条件 |
|---|---|
| A. RSS Proxy | 源站有合法 RSS，出口友好 |
| B. RSS Parse + rebuild | RSS 结构破损 / 时间格式非标准 / 编码乱 |
| C. HTML Scrape | 没 RSS，但列表页 DOM 规则 |
| D. JSON API | 没 RSS，XHR 暴露文章数组 |

决策树见 `prompts/adapter-author.md`。

## Runtime

按部署位置和解析成本选择 runtime。

| Runtime | 部署位置 | 出口 IP | 适用 |
|---|---|---|---|
| `runtime-worker/` | Cloudflare 边缘 | Cloudflare ASN | 默认，无运维 |
| `runtime-nodejs/` | 自托管机器（VPS / NAS / 树莓派） | 你机器的 IP | CF 段被反爬、需要重型解析库、需要长状态 |

两个 runtime 共用同一份 `FeedAdapter` 接口：

```ts
interface FeedAdapter {
  build(ctx: AdapterContext): Promise<string>;
}
```

`build` 返回 RSS XML 字符串。adapter 通常先生成 `Article[]`，再调用 `renderRss(meta, articles)`。

## 用法

把 `prompts/adapter-author.md` 和目标 URL 一起给 AI。输出应包含：adapter 模式、runtime、`src/adapter.ts`、部署命令、消费方 URL 修改。

先把模板拷到仓外目录，再填入 adapter：

```bash
# worker
cp -r agentic-rss/runtime-worker/ ~/agentic-rss-instances/<site>/
cd ~/agentic-rss-instances/<site>/
mv wrangler.toml.example wrangler.toml
npm install
npm run deploy

# nodejs
cp -r agentic-rss/runtime-nodejs/ ~/agentic-rss-instances/<site>/
cd ~/agentic-rss-instances/<site>/
docker compose up -d --build
```

部署完成后，把下游源列表里的原 URL 改为新 endpoint。

仓内保留公共模板和编写说明。具体站点的 adapter 实例放在仓外。

## 目录

```
agentic-rss/
├── README.md
├── prompts/
│   └── adapter-author.md        # 适配器编写说明
├── runtime-worker/              # Cloudflare Worker runtime
│   ├── src/{index,adapter,types}.ts + lib/{fetch,rss,passthrough}.ts
│   ├── wrangler.toml.example
│   └── package.json + tsconfig.json
└── runtime-nodejs/              # Node.js runtime
    ├── src/{server,adapter,types}.ts + lib/{fetch,rss}.ts
    ├── Dockerfile + docker-compose.yml
    └── package.json + tsconfig.json
```

## Runtime 约束

- `Article.id` 必须稳定，优先使用文章链接。
- `published` 只能写入有效 `Date`。
- 单次返回条数建议不超过 30。
- 不把 secret 写进源码。
- 默认只改 `src/adapter.ts`；公共 runtime 文件保持一致。
- Worker import 不带 `.js` 后缀；Node.js runtime 使用 `.js` 后缀。
