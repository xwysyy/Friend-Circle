import type { Adapter } from "./types.js";
// import { safeFetch } from "./lib/fetch.js";

/**
 * Replace this entire file when forking the template. The shape stays the same,
 * but `meta` and `fetch()` are filled in by the AI per `prompts/adapter-author.md`.
 *
 * Four canonical patterns:
 *
 * (A) RSS Proxy — site has RSS, network egress is friendly:
 *
 *   async fetch() {
 *     const resp = await safeFetch("https://site/rss.xml");
 *     // Reuse upstream XML if you also want to skip re-rendering — but the
 *     // standard path here is: parse XML → Article[], let renderRss rebuild
 *     // a clean RSS 2.0. Fewer surprises with malformed upstream feeds.
 *     return parseUpstreamItems(await resp.text());
 *   }
 *
 * (B) HTML Scrape — site has no RSS, but a structured listing page:
 *
 *   async fetch() {
 *     const resp = await safeFetch("https://site/blog");
 *     const html = await resp.text();
 *     return extractWithSelectors(html, {
 *       item: "article.post",
 *       title: "h2 a",
 *       link: "h2 a@href",
 *       date: "time@datetime",
 *     });
 *   }
 *
 * (C) JSON API — site exposes a posts JSON endpoint:
 *
 *   async fetch() {
 *     const resp = await safeFetch("https://site/api/posts.json");
 *     const data: { posts: ApiPost[] } = await resp.json();
 *     return data.posts.slice(0, 30).map(toArticle);
 *   }
 *
 * (D) Mixed — fetch listing for titles+links, then fetch each post for date:
 *     Avoid unless absolutely necessary; N+1 fetches eat throughput.
 *
 * Hard requirements:
 *   - Article.id MUST be stable (use link or sha1(link), never timestamps).
 *   - Total fetch time should stay under ~25s; the runtime reverse-proxy
 *     in front (CF / nginx) will time you out.
 *   - Do not hardcode secrets — use environment variables.
 */
const adapter: Adapter = {
  meta: {
    title: "Example",
    link: "https://example.com",
    description: "Replace with your site description",
    language: "en",
  },

  async fetch() {
    return [];
  },
};

export default adapter;
