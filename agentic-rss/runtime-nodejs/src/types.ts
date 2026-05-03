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

export interface Adapter {
  meta: FeedMeta;
  fetch(): Promise<Article[]>;
}
