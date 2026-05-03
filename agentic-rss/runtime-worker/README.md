# Agentic RSS Adapter — Cloudflare Worker Runtime

部署在 Cloudflare 边缘的 RSS 适配器。

适合 RSS proxy、RSS 修复、轻量 HTML/API 解析。重解析或自托管出口用 `runtime-nodejs/`。

## 步骤

1. 拷到仓外：

   ```bash
   cp -r agentic-rss/runtime-worker/ ~/agentic-rss-instances/<site>/
   cd ~/agentic-rss-instances/<site>/
   ```

2. `mv wrangler.toml.example wrangler.toml`，把 `name` 改成 `<site>-rss`
3. 改 `src/adapter.ts`（让 AI 按 `prompts/adapter-author.md` 生成）
4. 本地预览：`npm install && npm run dev`，访问 `http://localhost:8787/`
5. 检查类型：`npm run typecheck`
6. 部署：`npm run deploy`，得到 `https://<site>-rss.<account>.workers.dev`
7. 接入消费方：把消费方源列表里那一行的 URL 改成 worker URL

## 结构

```
runtime-worker/
├── src/
│   ├── index.ts              # worker 入口（不要改）
│   ├── adapter.ts            # 你要填的部分
│   ├── types.ts              # Article / FeedMeta / FeedAdapter（不要改）
│   └── lib/
│       ├── fetch.ts          # safeFetch（UA / 超时 / 重试，不要改）
│       ├── rss.ts            # Article[] → RSS XML（不要改）
│       └── passthrough.ts    # 模式 A 用：纯透传上游 RSS
├── wrangler.toml.example
├── package.json
└── tsconfig.json
```

`src/adapter.ts` 是站点适配代码。`lib/`、`types.ts`、`index.ts` 是 runtime 公共代码，只有更新模板时才改。
