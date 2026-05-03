# Agentic RSS Adapter — Cloudflare Worker Runtime

部署在 Cloudflare 边缘的 RSS 适配器。

适用：源站有 RSS（A/B 模式）、或源站没 RSS 但 HTML/API 解析轻量（C/D 模式），且 **Cloudflare 边缘 IP 段对该源站不被反爬**。如果 CF 段被打 → 改用 `runtime-nodejs/`。

## 步骤

1. 拷到仓外：
   ```bash
   cp -r agentic-rss/runtime-worker/ ~/agentic-rss-instances/<site>/
   cd ~/agentic-rss-instances/<site>/
   ```
2. `mv wrangler.toml.example wrangler.toml`，把 `name` 改成 `<site>-rss`
3. 改 `src/adapter.ts`（让 AI 按 `prompts/adapter-author.md` 生成）
4. 本地预览：`npm install && npx wrangler dev`，访问 `http://localhost:8787/`
5. 部署：`npx wrangler deploy`，得到 `https://<site>-rss.<account>.workers.dev`
6. 接入消费方：把消费方源列表里对应行的 URL 改成 worker URL

## 结构

```
runtime-worker/
├── src/
│   ├── index.ts              # worker 入口（不要改）
│   ├── adapter.ts            # 你要填的部分
│   ├── types.ts              # Article / Adapter 接口（不要改）
│   └── lib/
│       ├── fetch.ts          # safeFetch（UA / 超时 / 重试，不要改）
│       ├── rss.ts            # Article[] → RSS XML（不要改）
│       └── passthrough.ts    # 模式 A 用：纯透传上游 RSS
├── wrangler.toml.example
├── package.json
└── tsconfig.json
```

`lib/` 和 `types.ts` 的修改请回到上游 `agentic-rss/runtime-worker/` 改 —— 它们是工具维护方持有的公共代码，所有 instance 共享。
