import type { Adapter } from "./types";
import { renderRss } from "./lib/rss";
import { safeFetch } from "./lib/fetch";
import adapter from "./adapter";

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return new Response("ok\n", {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    try {
      const articles = await adapter.fetch({
        request,
        fetchUrl: safeFetch,
      });
      const xml = renderRss(adapter.meta, articles);
      return new Response(xml, {
        headers: {
          "content-type": "application/rss+xml; charset=utf-8",
          "cache-control": "public, max-age=600",
          "access-control-allow-origin": "*",
        },
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return new Response(`adapter error: ${msg}\n`, {
        status: 502,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }
  },
};
