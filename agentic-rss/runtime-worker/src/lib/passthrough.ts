import { safeFetch } from "./fetch";

const VALID_FEED_CT_RE = /(rss|atom|xml)/i;
const FEED_SNIFF_RE = /^[\s﻿]*(<\?xml|<rss|<feed|<atom)/i;
const SNIFF_BYTES = 256;

export async function passthrough(url: string): Promise<string> {
  const resp = await safeFetch(url, { totalTimeoutMs: 12000, retries: 1 });
  if (!resp.ok) throw new Error(`upstream HTTP ${resp.status}`);
  const ct = resp.headers.get("content-type") ?? "";
  const body = await resp.text();
  if (!VALID_FEED_CT_RE.test(ct) && !FEED_SNIFF_RE.test(body.slice(0, SNIFF_BYTES))) {
    throw new Error("upstream returned non-feed content");
  }
  return body;
}
