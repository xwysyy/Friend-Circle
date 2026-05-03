import type { SafeFetchOptions } from "./lib/fetch";

export interface Article {
  id: string;
  title: string;
  link: string;
  published?: Date;
  author?: string;
  category?: string;
  summary?: string;
}

export interface FeedMeta {
  title: string;
  link: string;
  description: string;
  language?: string;
}

export interface AdapterContext {
  request: Request;
  fetchUrl: (url: string, opts?: SafeFetchOptions) => Promise<Response>;
}

export interface FeedAdapter {
  build(ctx: AdapterContext): Promise<string>;
}
