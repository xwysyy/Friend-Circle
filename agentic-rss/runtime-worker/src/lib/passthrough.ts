import { safeFetch } from "./fetch";

/**
 * 把源站 RSS/XML 原样转发，仅替换/补充 CORS 与 cache 头。
 *
 * 适用场景：源站本身有合法 RSS，只是 GitHub Runner IP 被反爬。
 * Worker 用 Cloudflare 边缘 IP 拉一次 → 透传给消费方。
 */
export async function proxyFeed(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const upstream = await safeFetch(url, init);
  if (!upstream.ok) {
    return new Response(`upstream ${upstream.status}`, {
      status: 502,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  const body = await upstream.text();
  const ct =
    upstream.headers.get("content-type") ??
    "application/rss+xml; charset=utf-8";
  return new Response(body, {
    headers: {
      "content-type": ct,
      "cache-control": "public, max-age=600",
      "access-control-allow-origin": "*",
      "x-agentic-rss-source": url,
    },
  });
}
