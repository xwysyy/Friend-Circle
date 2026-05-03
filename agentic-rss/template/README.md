# Adapter Template

每个反爬严重的站点 = 从这个模板拷一份独立的 Cloudflare Worker。

## 关键约定

**adapter 实例不放在 Friend-Circle 仓库内**。把 `template/` 拷到仓外某个目录（建议 `~/Code/ginblog/agentic-rss-instances/<site>/` 或你自定的路径），独立 `wrangler deploy`、独立维护。

仓内只保留**模板和 prompt**——它们是所有 adapter 共用的、版本化的"骨架"，会跟随 Friend-Circle 一起 commit。具体站点的 worker 是一次性产物，不入仓。

## 步骤

1. **拷贝**到仓外：
   ```bash
   cp -r agentic-rss/template/ ~/Code/ginblog/agentic-rss-instances/<site>/
   cd ~/Code/ginblog/agentic-rss-instances/<site>/
   ```
2. **改 wrangler.toml**：把 `wrangler.toml.example` 改名为 `wrangler.toml`，把 `name` 改成 `<site>-rss`（决定最终 URL 子域名）
3. **填 src/adapter.ts**：实现 `fetch(ctx)`，返回 `Article[]`。可参考 `prompts/adapter-author.md` 让 AI 帮忙
4. **本地预览**：
   ```bash
   npm install
   npx wrangler dev
   ```
   浏览器开 `http://localhost:8787/` 验证 RSS 输出
5. **部署**：
   ```bash
   npx wrangler deploy
   ```
   成功后会得到 `https://<site>-rss.<account>.workers.dev`
6. **接入 Friend-Circle**：把 `config/*.json` 里对应站点的 `feed_url` 替换成 worker URL，下一次 CI 就用 worker 抓

## 模板结构

```
template/
├── src/
│   ├── index.ts              # worker 入口（不要改）
│   ├── adapter.ts            # 你要填的部分
│   ├── types.ts              # Article / Adapter 接口定义（不要改）
│   └── lib/
│       ├── fetch.ts          # safeFetch（UA / 超时 / 重试，不要改）
│       ├── rss.ts            # Article[] → RSS XML（不要改）
│       └── passthrough.ts    # 纯透传上游 RSS 的快捷工具
├── wrangler.toml.example
├── package.json
└── tsconfig.json
```

`lib/` 和 `types.ts` 的修改请回到本仓库去改 —— 它们是 Friend-Circle 维护的公共代码。
