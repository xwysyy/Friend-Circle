# Adapter Author Prompt

> Audience：AI agent（Claude / Codex / GPT），被人类要求把一个没 RSS 或 RSS 被反爬的站点变成可订阅的 RSS endpoint，供下游 RSS 消费方拉取。
>
> Output：完整的 adapter 代码 + runtime 选择 + 部署命令清单。

## 你拿到的输入

人类会给你两件东西。一是目标 URL，可能是首页、文章列表、或直接的 RSS URL。二是已知现象，比如 "RSS 被反爬，本地 curl 也 429"，或者 "压根没 RSS，HTML 结构看着规则"。

## 你要交付的输出

一份可执行清单：adapter 模式判断（A/B/C/D）、runtime 选择（worker / nodejs）、完整的 `src/adapter.ts` 代码、部署命令、消费方源列表里那一行 URL 的 diff。

---

## Step 1：探查站点

按优先级试，找到能用的就停。不必每条都跑。

```
1. <site>/rss.xml, /feed, /atom.xml, /index.xml, /feed.xml      ← 已知 RSS 路径
2. <site>/sitemap.xml, /sitemap_index.xml                        ← sitemap 列出文章
3. 抓 <site>/ 主页，grep '<link rel="alternate" type="application/(rss|atom)+xml"'  ← HTML 头可能藏 RSS 路径
4. <site>/blog, /posts, /articles, /writings                    ← 列表页是否结构规则
5. F12 / curl 主页查 XHR，找 /api/posts.json /api/feed 等        ← JSON API 最稳
6. 在 GitHub 搜 "site-domain.com user:<author>"                 ← 作者博客 source 可能开源
```

诊断要做一步：用两个不同 IP 段测同一个 URL（你本机 + 一个公开 worker），看反应是否一致。

- 都 200：出口友好，A 模式 + worker runtime
- 你本机 200 / worker 429：CF 段被打，B/C/D 模式 + nodejs runtime
- 都 429：站点反爬范围广，跟人类说这条不可行——要么作者白名单、要么放弃、要么住宅代理

---

## Step 2：选 adapter 模式

| 模式 | 触发条件 | 工作量 |
|---|---|---|
| A. RSS Proxy | 源站有合法 RSS + 出口友好 | XS（10 行） |
| B. RSS Parse + rebuild | 源站 RSS 结构破损 / 时间格式非标准 / 编码乱 | S（30 行解析） |
| C. HTML Scrape | 源站没 RSS，但列表页 DOM 规则 | M（cheerio / regex 抽 selector） |
| D. JSON API | 源站没 RSS，但 XHR 暴露文章数组 | XS-S（直接 fetch + map） |

优先级 A > D > B > C。HTML scrape 是最后选——脆弱、易失效、上游改版直接挂。

---

## Step 3：选 runtime

| 维度 | runtime-worker（CF） | runtime-nodejs（Docker） |
|---|---|---|
| 出口 IP | Cloudflare 边缘段 | 你部署机器的 IP |
| 运维 | 无（serverless） | 要维护机器、Docker、反代 |
| CPU 预算 | free 10ms / paid 30s 单请求 | 不限 |
| 复杂解析（cheerio / playwright） | 难（free CPU 撑不住） | 适合 |
| 冷启动 | < 100ms | 持续运行 |
| 公网暴露 | 自动（`*.workers.dev`） | 需要 Cloudflare Tunnel / Caddy / 公网 IP |

默认选 worker。改选 nodejs 的情形有三种：CF 段被反爬（A 模式但 worker 出口 429）、HTML scrape 要重型解析库（cheerio / jsdom）、需要长状态或大缓存。

---

## Step 4：生成代码

### 4.1 worker runtime（默认）

把 `agentic-rss/runtime-worker/` 完整拷到仓外目录，改 `src/adapter.ts`。imports 不带 `.js` 扩展（worker bundler 处理）。

#### 模式 A 模板（RSS Proxy via passthrough）

```ts
// runtime-worker/src/adapter.ts
import { proxyFeed } from "./lib/passthrough";

// 注意：proxy 模式直接覆盖 index.ts 的 fetch handler。
// 不走 adapter.ts + renderRss 链路；直接转发上游 XML。
// → 在 src/index.ts 顶层把 default export 改成：
//
//   export default {
//     async fetch(_request: Request): Promise<Response> {
//       return proxyFeed("https://<site>/rss.xml");
//     },
//   };
```

#### 模式 C 模板（HTML Scrape）

```ts
// runtime-worker/src/adapter.ts
import type { Adapter, Article } from "./types";
import { safeFetch } from "./lib/fetch";

const adapter: Adapter = {
  meta: {
    title: "<site title>",
    link: "https://<site>",
    language: "zh-CN",  // or "en"
  },

  async fetch(ctx) {
    const resp = await ctx.fetchUrl("https://<site>/blog");
    const html = await resp.text();
    return extractArticles(html);
  },
};

function extractArticles(html: string): Article[] {
  // 优先用 HTMLRewriter（worker 原生，无依赖、流式）。
  // 但跨 chunk 状态比较绕，简单站点用 regex 更快出代码。
  const items: Article[] = [];
  const re = /<article[^>]*>[\s\S]*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)<\/a>[\s\S]*?<time[^>]*datetime="([^"]+)"/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null && items.length < 30) {
    const [, link, title, datetime] = m;
    if (!link || !title) continue;
    items.push({
      id: link,                               // link 即稳定 id
      title: title.trim(),
      link: link.startsWith("http") ? link : `https://<site>${link}`,
      published: new Date(datetime ?? ""),    // 解析失败 → Invalid Date → 由 renderRss 跳过
    });
  }
  return items;
}

export default adapter;
```

#### 模式 D 模板（JSON API）

```ts
// runtime-worker/src/adapter.ts
import type { Adapter } from "./types";

interface ApiPost {
  slug: string;
  title: string;
  published_at: string;
  author?: string;
  excerpt?: string;
}

const adapter: Adapter = {
  meta: {
    title: "<site title>",
    link: "https://<site>",
    language: "zh-CN",
  },

  async fetch(ctx) {
    const resp = await ctx.fetchUrl("https://<site>/api/posts.json");
    const data = (await resp.json()) as { posts: ApiPost[] };
    return data.posts.slice(0, 30).map((p) => ({
      id: p.slug,
      title: p.title,
      link: `https://<site>/posts/${p.slug}`,
      published: new Date(p.published_at),
      author: p.author,
      summary: p.excerpt,
    }));
  },
};

export default adapter;
```

### 4.2 nodejs runtime（CF 段被打 / 重解析）

把 `agentic-rss/runtime-nodejs/` 完整拷到仓外目录，改 `src/adapter.ts`。imports 必须带 `.js` 扩展（NodeNext 要求）。

```ts
// runtime-nodejs/src/adapter.ts
import type { Adapter } from "./types.js";
import { safeFetch } from "./lib/fetch.js";

const adapter: Adapter = {
  meta: { ... },
  async fetch() {                  // 注意：nodejs 版没有 ctx 参数
    const resp = await safeFetch("https://<site>/rss.xml");
    // 同模式 A/B/C/D 之一
    return [];
  },
};

export default adapter;
```

要 cheerio 做 HTML scrape：

```bash
cd runtime-nodejs/<your-instance>
npm install cheerio
```

```ts
import * as cheerio from "cheerio";

async function fetch() {
  const resp = await safeFetch("https://<site>/blog");
  const $ = cheerio.load(await resp.text());
  return $("article.post").slice(0, 30).map((_, el) => ({
    id: $(el).find("a").attr("href")!,
    title: $(el).find("h2").text().trim(),
    link: new URL($(el).find("a").attr("href")!, "https://<site>").toString(),
    published: new Date($(el).find("time").attr("datetime") ?? ""),
  })).get();
}
```

---

## Step 5：硬约束（不管哪个 runtime、哪个模式都得遵守）

- `Article.id` 必须稳定：用 link 或 sha1(link)。不要用 timestamp 或随机数，消费方按 id 去重
- `Article.published` 解析失败时留空。不要塞 `new Date()`，那会让所有文章都被标"刚发"，污染时间排序
- 条数 ≤ 30，单次响应不要过大
- 25s 内必须返回（worker wall-time / 反代 timeout）
- 不改公共代码：`lib/fetch.ts`、`lib/rss.ts`、`types.ts`、`server.ts`、`index.ts`、`passthrough.ts`，这些归 agentic-rss 模板维护，改了未来 instance 都受影响
- secret 不硬编码：worker 用 `wrangler secret put`，nodejs 用环境变量加 `docker compose` 的 `environment:` 字段

---

## Step 6：都不行的时候

如果 Step 1 的诊断显示 A/B/C/D 全部不通——任意 IP、任意路径都被反爬，或者站点根本没结构化数据——直接告诉人类工程方案已穷尽，推荐选项是联系作者要白名单、接受现状从源列表移除、或商业住宅代理。

不要把 50% 把握的代码塞给人类还说"应该能跑"。

---

## Step 7：输出格式

```
探查诊断
- 已知 RSS 路径：<HTTP 状态汇总>
- 出口对比：本机=<status> / CF Worker 测试=<status>
- 选定模式：<A/B/C/D>
- 选定 runtime：<worker / nodejs>，理由：<一句话>

代码：<runtime>/src/adapter.ts
<完整文件，包括 imports>

配置：<runtime>/wrangler.toml or docker-compose.yml
<填好 name / port 等>

部署命令
# worker:
cp -r agentic-rss/runtime-worker/ ~/agentic-rss-instances/<slug>/
cd ~/agentic-rss-instances/<slug>/
mv wrangler.toml.example wrangler.toml  # 改 name
# (paste adapter.ts)
npm install && npx wrangler deploy

# nodejs:
cp -r agentic-rss/runtime-nodejs/ ~/agentic-rss-instances/<slug>/
cd ~/agentic-rss-instances/<slug>/
# (paste adapter.ts)
docker compose up -d --build
# 公网暴露见 runtime-nodejs/README.md

消费方接入
在下游消费方源列表里改一行：
- "https://<old-feed-url>"
+ "https://<new-endpoint>"
```
