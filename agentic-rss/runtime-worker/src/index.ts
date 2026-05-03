import { safeFetch } from "./lib/fetch";
import adapter from "./adapter";

export default {
  async fetch(request: Request): Promise<Response> {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("method not allowed\n", {
        status: 405,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          allow: "GET, HEAD",
          "cache-control": "no-store",
        },
      });
    }

    const path = new URL(request.url).pathname;
    if (path === "/health") {
      return new Response("ok\n", {
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store",
        },
      });
    }

    try {
      const body = await adapter.build({ request, fetchUrl: safeFetch });
      const headers = new Headers({
        "content-type": "application/rss+xml; charset=utf-8",
        "cache-control": "public, max-age=900",
        "access-control-allow-origin": "*",
        "x-content-type-options": "nosniff",
      });
      if (request.method === "HEAD") return new Response(null, { headers });
      return new Response(body, { headers });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return new Response(`error: ${msg}\n`, {
        status: 502,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store",
        },
      });
    }
  },
};
