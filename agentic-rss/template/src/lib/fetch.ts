const DEFAULT_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const RETRY_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

export interface SafeFetchOptions extends RequestInit {
  timeoutMs?: number;
  retries?: number;
}

export async function safeFetch(
  url: string,
  opts: SafeFetchOptions = {},
): Promise<Response> {
  const { timeoutMs = 25000, retries = 2, headers, ...rest } = opts;

  const finalHeaders: Record<string, string> = {
    "User-Agent": DEFAULT_UA,
    Accept:
      "application/atom+xml,application/rss+xml,application/xml;q=0.9," +
      "text/html,*/*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    ...(headers as Record<string, string> | undefined),
  };

  let lastErr: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) {
      await new Promise((r) =>
        setTimeout(r, 600 * Math.pow(2, attempt - 1)),
      );
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const resp = await fetch(url, {
        ...rest,
        headers: finalHeaders,
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      if (RETRY_STATUS.has(resp.status) && attempt < retries) {
        lastErr = new Error(`HTTP ${resp.status}`);
        continue;
      }
      return resp;
    } catch (e) {
      clearTimeout(timer);
      lastErr = e;
    }
  }
  throw lastErr ?? new Error(`fetch failed: ${url}`);
}
