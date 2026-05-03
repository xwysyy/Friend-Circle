import type { Adapter } from "./types";

/**
 * Replace this file when forking the template.
 *
 * Two common patterns:
 *
 * (A) Proxy mode — site has RSS, you only need to refetch with worker IP:
 *
 *     async fetch(ctx) {
 *       const resp = await ctx.fetchUrl("https://site/rss.xml");
 *       const xml = await resp.text();
 *       // Parse <item> blocks → Article[]
 *       return parsed;
 *     }
 *
 *     Or if you want to passthrough the upstream XML untouched, see
 *     `lib/passthrough.ts` and bypass the renderRss path entirely
 *     by short-circuiting in `index.ts`.
 *
 * (B) Scrape mode — site has only HTML:
 *
 *     async fetch(ctx) {
 *       const resp = await ctx.fetchUrl("https://site/posts");
 *       const html = await resp.text();
 *       // Extract via HTMLRewriter / regex → Article[]
 *       return extracted;
 *     }
 *
 * (C) API mode — site exposes JSON:
 *
 *     async fetch(ctx) {
 *       const resp = await ctx.fetchUrl("https://site/api/posts");
 *       const data = await resp.json<{ posts: ApiPost[] }>();
 *       return data.posts.map(toArticle);
 *     }
 *
 * Hard requirements:
 *   - Article.id MUST be stable (use link or sha1(link), never timestamps).
 *   - fetch(ctx) MUST return within 25s (Cloudflare worker CPU/wall budget).
 *   - Do not hardcode secrets — use `wrangler secret put NAME`.
 */
const adapter: Adapter = {
  meta: {
    title: "Example",
    link: "https://example.com",
    description: "Replace this with your site description",
    language: "en",
  },

  async fetch(_ctx) {
    return [];
  },
};

export default adapter;
