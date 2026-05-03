export interface Article {
  id: string;
  title: string;
  link: string;
  published?: Date;
  author?: string;
  summary?: string;
}

export interface FeedMeta {
  title: string;
  link: string;
  description?: string;
  language?: string;
}

export interface AdapterContext {
  request: Request;
  fetchUrl: (url: string, init?: RequestInit) => Promise<Response>;
}

export interface Adapter {
  meta: FeedMeta;
  fetch(ctx: AdapterContext): Promise<Article[]>;
}
