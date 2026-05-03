const DEFAULT_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const RETRY_STATUS = new Set([408, 425, 500, 502, 504]);

export interface SafeFetchOptions extends Omit<RequestInit, "headers" | "signal"> {
  headers?: Record<string, string>;
  totalTimeoutMs?: number;
  retries?: number;
}

export async function safeFetch(
  url: string,
  opts: SafeFetchOptions = {},
): Promise<Response> {
  const { totalTimeoutMs = 15000, retries = 1, headers, ...rest } = opts;

  const finalHeaders: Record<string, string> = {
    "User-Agent": DEFAULT_UA,
    Accept:
      "application/atom+xml,application/rss+xml,application/xml;q=0.9," +
      "application/json;q=0.9,text/html;q=0.5,*/*;q=0.3",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    ...headers,
  };

  const deadline = Date.now() + totalTimeoutMs;
  let lastErr: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const remaining = deadline - Date.now();
    if (remaining <= 200) break;

    if (attempt > 0) {
      const backoff = Math.min(600 * 2 ** (attempt - 1), remaining - 200);
      if (backoff > 0) await sleep(backoff);
    }

    const remainingForFetch = deadline - Date.now();
    if (remainingForFetch <= 200) break;

    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), remainingForFetch);

    let resp: Response;
    try {
      resp = await fetch(url, {
        ...rest,
        headers: finalHeaders,
        signal: ctrl.signal,
      });
    } catch (e) {
      clearTimeout(timer);
      lastErr = e;
      continue;
    }
    clearTimeout(timer);

    if (RETRY_STATUS.has(resp.status) && attempt < retries) {
      lastErr = new Error(`HTTP ${resp.status}`);
      resp.body?.cancel().catch(() => undefined);
      continue;
    }
    return resp;
  }
  throw lastErr ?? new Error(`fetch deadline exhausted: ${url}`);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
