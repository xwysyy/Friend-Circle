# Adapter Author Prompt

> Audience：AI agent（Claude / Codex / GPT），被人类要求把一个没 RSS 或 RSS 被反爬的站点变成可订阅的 RSS endpoint，供下游 RSS 消费方拉取。
>
> Output：adapter 代码 + runtime 选择 + 部署命令清单。

## 你拿到的输入

人类会给你两件东西。一是目标 URL，可能是首页、文章列表、或直接的 RSS URL。二是已知现象，比如 "RSS 被反爬，本地 curl 也 429"，或者 "压根没 RSS，HTML 结构看着规则"。

## 你要交付的输出

一份可执行清单：adapter 模式判断（A/B/C/D）、runtime 选择（worker / nodejs）、`src/adapter.ts` 代码、部署命令、消费方源列表里那一行 URL 的 diff。

---

## Step 1：探查站点

按优先级试，找到能用的就停。

```
1. <site>/rss.xml, /feed, /atom.xml, /index.xml, /feed.xml      ← 已知 RSS 路径
2. <site>/sitemap.xml, /sitemap_index.xml, /sitemap-0.xml        ← sitemap 列出文章
3. 抓 <site>/ 主页，grep '<link rel="alternate" type="application/(rss|atom)+xml"'
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
| A. RSS Proxy | 源站有合法 RSS + 出口友好 | XS（3 行） |
| B. RSS Parse + rebuild | 源站 RSS 结构破损 / 时间格式非标准 / 编码乱 | S（30 行解析） |
| C. HTML Scrape | 源站没 RSS，但列表页 DOM 规则 | M（cheerio / regex 抽 selector） |
| D. JSON API | 源站没 RSS，但 XHR 暴露文章数组 | XS-S（直接 fetch + map） |

优先级 A > D > B > C。

---

## Step 3：选 runtime

| 维度 | runtime-worker（CF） | runtime-nodejs（Docker） |
|---|---|---|
| 出口 IP | Cloudflare 边缘段 | 你部署机器的 IP |
| 运维 | 无（serverless） | 要维护机器、Docker、反代 |
| CPU 预算 | free 10ms / paid 30s 单请求 | 不限 |
| 复杂解析（cheerio / playwright） | 难（free CPU 撑不住） | 适合 |
| 公网暴露 | 自动（`*.workers.dev`） | 需要 Cloudflare Tunnel / Caddy / 公网 IP |

默认选 worker。改选 nodejs 的情形：CF 段被反爬、HTML scrape 要重型解析库、需要长状态。

---

## Step 4：Adapter 接口（两 runtime 完全一致）

```ts
// types.ts (两个 runtime 同形态)
export interface AdapterContext {
  request: Request;
  fetchUrl: (url: string, opts?: SafeFetchOptions) => Promise<Response>;
}

export interface FeedAdapter {
  build(ctx: AdapterContext): Promise<string>;  // 返回 RSS 2.0 XML body
}
```

填 `src/adapter.ts`：

- worker imports 不带 `.js`：`import type { FeedAdapter } from "./types";`
- nodejs imports 带 `.js`：`import type { FeedAdapter } from "./types.js";`

这是两个 runtime 间唯一差异。`build(ctx)` 签名、可用工具（`ctx.fetchUrl`、`renderRss`、`passthrough`）完全相同。

---

## Step 5：四种模式代码模板

### 模式 A：RSS Proxy

```ts
import type { FeedAdapter } from "./types";
import { passthrough } from "./lib/passthrough";

const adapter: FeedAdapter = {
  build(_ctx) {
    return passthrough("https://<site>/rss.xml");
  },
};

export default adapter;
```

### 模式 B：RSS Parse + rebuild

```ts
import type { FeedAdapter, Article } from "./types";
import { renderRss } from "./lib/rss";

const adapter: FeedAdapter = {
  async build(ctx) {
    const resp = await ctx.fetchUrl("https://<site>/rss.xml");
    if (!resp.ok) throw new Error(`upstream HTTP ${resp.status}`);
    const xml = await resp.text();
    const items = parseUpstreamItems(xml);  // 自己写解析
    return renderRss(
      { title: "<site title>", link: "https://<site>", description: "" },
      items,
    );
  },
};

function parseUpstreamItems(_xml: string): Article[] {
  // 自定义 RSS/Atom 解析
  return [];
}

export default adapter;
```

### 模式 C：HTML Scrape

```ts
import type { FeedAdapter, Article } from "./types";
import { renderRss } from "./lib/rss";

const adapter: FeedAdapter = {
  async build(ctx) {
    const resp = await ctx.fetchUrl("https://<site>/blog");
    if (!resp.ok) throw new Error(`upstream HTTP ${resp.status}`);
    const html = await resp.text();
    return renderRss(
      { title: "<site title>", link: "https://<site>", description: "", language: "zh-CN" },
      extractArticles(html),
    );
  },
};

function extractArticles(html: string): Article[] {
  const items: Article[] = [];
  const re = /<article[^>]*>[\s\S]*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)<\/a>[\s\S]*?<time[^>]*datetime="([^"]+)"/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null && items.length < 30) {
    const [, link, title, datetime] = m;
    if (!link || !title) continue;
    const article: Article = {
      id: link,
      title: title.trim(),
      link: link.startsWith("http") ? link : `https://<site>${link}`,
    };
    if (datetime) {
      const d = new Date(datetime);
      if (!Number.isNaN(d.getTime())) article.published = d;
    }
    items.push(article);
  }
  return items;
}

export default adapter;
```

### 模式 D：JSON API

```ts
import type { FeedAdapter, Article } from "./types";
import { renderRss } from "./lib/rss";

interface ApiPost {
  slug: string;
  title: string;
  published_at: string;
  author?: string;
  excerpt?: string;
}

const adapter: FeedAdapter = {
  async build(ctx) {
    const resp = await ctx.fetchUrl("https://<site>/api/posts.json", {
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) throw new Error(`upstream HTTP ${resp.status}`);
    const data = (await resp.json()) as { posts: ApiPost[] };
    const articles: Article[] = data.posts.slice(0, 30).map((p) => {
      const a: Article = {
        id: p.slug,
        title: p.title,
        link: `https://<site>/posts/${p.slug}`,
      };
      const d = new Date(p.published_at);
      if (!Number.isNaN(d.getTime())) a.published = d;
      if (p.author) a.author = p.author;
      if (p.excerpt) a.summary = p.excerpt;
      return a;
    });
    return renderRss(
      { title: "<site title>", link: "https://<site>", description: "" },
      articles,
    );
  },
};

export default adapter;
```

### nodejs runtime 用 cheerio

```bash
npm install cheerio
```

```ts
import * as cheerio from "cheerio";

async function build(ctx) {
  const resp = await ctx.fetchUrl("https://<site>/blog");
  const $ = cheerio.load(await resp.text());
  const articles = $("article.post").slice(0, 30).map((_, el) => {
    const href = $(el).find("a").attr("href") ?? "";
    const link = new URL(href, "https://<site>").toString();
    const datetime = $(el).find("time").attr("datetime") ?? "";
    const article: any = {
      id: link,
      title: $(el).find("h2").text().trim(),
      link,
    };
    const d = new Date(datetime);
    if (!Number.isNaN(d.getTime())) article.published = d;
    return article;
  }).get();
  // wrap with renderRss(meta, articles)
}
```

记得把 `cheerio` 加到 `package.json` 的 `dependencies`，别放 `devDependencies`。

---

## Step 6：硬约束

- `Article.id` 必须稳定：用 link 或 sha1(link)，不要用 timestamp / 随机数
- `published` 解析失败时不要赋值：`new Date("")` 是 Invalid Date，会被 `renderRss` 跳过；你的代码在赋值前必须 `!Number.isNaN(d.getTime())` 检查
- 条数 ≤ 30
- 25s 内必须返回（worker wall-time / 反代 timeout）
- 不改公共代码：`lib/fetch.ts`、`lib/rss.ts`、`lib/passthrough.ts`、`types.ts`、`server.ts`、`index.ts`
- secret 不硬编码：worker 用 `wrangler secret put`，nodejs 用环境变量加 `docker compose` 的 `environment:`

---

## Step 7：都不行的时候

如果 Step 1 的诊断显示 A/B/C/D 全部不通——任意 IP、任意路径都被反爬，或站点没结构化数据——直接告诉人类工程方案已穷尽。推荐选项：联系作者要白名单、放弃、商业住宅代理。

不要把没把握的代码塞给人类还说"应该能跑"。

---

## Step 8：输出格式

```
探查诊断
- 已知 RSS 路径：<HTTP 状态汇总>
- 出口对比：本机=<status> / CF Worker 测试=<status>
- 选定模式：<A/B/C/D>
- 选定 runtime：<worker / nodejs>，理由：<一句话>

代码：<runtime>/src/adapter.ts
<文件内容，包括 imports>

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
# (paste adapter.ts; 如需 cheerio 等，加进 package.json dependencies)
docker compose up -d --build

消费方接入
- "https://<old-feed-url>"
+ "https://<new-endpoint>"
```
