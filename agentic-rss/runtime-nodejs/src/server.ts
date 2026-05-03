import { createServer } from "node:http";
import adapter from "./adapter.js";
import { renderRss } from "./lib/rss.js";

const PORT = Number(process.env.PORT ?? 8080);

const server = createServer(async (req, res) => {
  const method = req.method ?? "GET";
  if (method !== "GET" && method !== "HEAD") {
    res.writeHead(405, {
      "content-type": "text/plain; charset=utf-8",
      allow: "GET, HEAD",
      "cache-control": "no-store",
    });
    res.end("method not allowed\n");
    return;
  }

  const path = (req.url ?? "/").split("?")[0]?.replace(/\/+$/, "") || "/";

  if (path === "/health") {
    res.writeHead(200, {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    });
    res.end("ok\n");
    return;
  }

  if (path !== "/" && path !== "/feed" && path !== "/feed.xml") {
    res.writeHead(404, {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    });
    res.end(`not found: ${path}\n`);
    return;
  }

  const t0 = Date.now();
  try {
    const articles = await adapter.fetch();
    const xml = renderRss(adapter.meta, articles);
    console.log(
      `feed.served items=${articles.length} elapsed=${Date.now() - t0}ms`,
    );
    res.writeHead(200, {
      "content-type": "application/rss+xml; charset=utf-8",
      "cache-control": "public, max-age=900",
      "access-control-allow-origin": "*",
      "x-content-type-options": "nosniff",
    });
    if (method === "HEAD") {
      res.end();
    } else {
      res.end(xml);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(
      `feed.error elapsed=${Date.now() - t0}ms err=${msg}`,
    );
    res.writeHead(502, {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    });
    res.end("upstream fetch failed\n");
  }
});

server.listen(PORT, () => {
  console.log(`agentic-rss runtime-nodejs listening on :${PORT}`);
});
