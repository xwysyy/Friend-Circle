# Adapter Author Prompt

> 用法：`results/errors.json` 里某个 `feed_url` 持续失败 → 把这份 prompt + 目标 URL 喂给 AI（Claude / Codex / GPT），让它生成一份能直接 deploy 的 adapter。

## 任务

给定一个**目标 URL**（站点首页或文章列表），生成一份完整的 Cloudflare Worker adapter（基于 `agentic-rss/template`），部署后暴露稳定的 RSS endpoint，供 Friend-Circle 主程序消费。

## 探查步骤（按优先级）

1. **试已知 RSS 路径**：`<site>/rss.xml`、`<site>/feed`、`<site>/atom.xml`、`<site>/index.xml`、`<site>/feed.xml`
2. **看 sitemap**：`<site>/sitemap.xml`、`<site>/sitemap_index.xml`、`<site>/sitemap-posts.xml`
3. **查 HTML 头**：访问首页，搜索 `<link rel="alternate" type="application/rss+xml">` / `application/atom+xml`
4. **抓列表页**：`<site>/posts`、`<site>/blog`、`<site>/articles`，看 HTML 结构是否容易抽
5. **查 XHR**：浏览器 F12 看文章列表的网络请求，常有 JSON API（最稳）

## 三种实现策略（按工作量从小到大）

### A — Proxy 模式（首选）

源站有 RSS、且本地能用 curl 拉到 → worker 拉一次源站 RSS、原样转发。

```ts
import { proxyFeed } from "./lib/passthrough";

export default {
  async fetch(_request: Request): Promise<Response> {
    return proxyFeed("https://<site>/rss.xml");
  },
};
```

> 注：proxy 模式直接覆盖 `index.ts` 的 fetch handler，不走 `adapter.ts` + `renderRss` 路径。最简、零解析、最快。

### B — Parse 模式

源站 RSS 有问题（结构破损 / 编码错误 / 时间格式非标准）→ worker 拉、解析、用 `renderRss` 重新输出标准 RSS 2.0。

```ts
const adapter: Adapter = {
  meta: { title: "...", link: "...", language: "zh-CN" },
  async fetch(ctx) {
    const resp = await ctx.fetchUrl("https://<site>/rss.xml");
    const xml = await resp.text();
    const items = parseItems(xml); // 自己写解析
    return items;
  },
};
```

### C — Scrape / API 模式

源站完全没 RSS → 抓 HTML 列表页或调 JSON API，构造 `Article[]`。

```ts
async fetch(ctx) {
  const resp = await ctx.fetchUrl("https://<site>/api/posts");
  const data = await resp.json<{ posts: ApiPost[] }>();
  return data.posts.slice(0, 30).map(p => ({
    id: p.slug,
    title: p.title,
    link: `https://<site>/posts/${p.slug}`,
    published: new Date(p.published_at),
    author: p.author,
  }));
}
```

## 硬约束

- **`Article.id` 必须稳定**：用 link 或 link 的 hash，绝不用时间戳或随机数（消费方 Friend-Circle 用它去重）
- **`Article.published` 解析失败时留空**（不要塞 `new Date()`，那会让所有文章都"现在"）
- **条数 ≤ 30**：避免单次响应过大
- **25s 内必须返回**：CF Worker 的 wall-time 上限，超时被强终
- **禁止改公共代码**：`lib/fetch.ts`、`lib/rss.ts`、`lib/passthrough.ts`、`types.ts`、`index.ts`（核心 fetch handler）—— 它们由 Friend-Circle 仓库统一维护
- **禁止硬编码 secret**：用 `npx wrangler secret put NAME` 注入

## 失败信号

如果你已经从模板代码层做了：UA 伪装、重试退避、HTTP/2，仍然被对端反爬挡住（worker 也 429 / 403）：

→ **不要硬上**。回头跟用户说："worker 也被挡了，这条路走不通，建议改用 self-hosted runner / 商业代理 / 从 friend.json 暂时移除"。

## 输出格式

最后给用户一个**可直接执行的清单**：

```
[1/4] template/src/adapter.ts 完整代码：
      <粘贴完整文件>

[2/4] template/wrangler.toml（改 name）：
      name = "<site>-rss"
      ...

[3/4] 部署命令：
      cp -r agentic-rss/template/ ~/Code/ginblog/agentic-rss-instances/<site>/
      cd ~/Code/ginblog/agentic-rss-instances/<site>/
      mv wrangler.toml.example wrangler.toml
      # 粘贴上面的 adapter.ts
      npm install
      npx wrangler deploy

[4/4] 改 friend.json:
      - "https://<old-feed-url>"
      + "https://<site>-rss.<account>.workers.dev/"
```
